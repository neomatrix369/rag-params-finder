import time
from typing import TypedDict

from pymongo import ASCENDING, IndexModel
from pymongo.collection import Collection
from pymongo.operations import SearchIndexModel

from server.db.atlas import (
    CHUNKS_COLLECTION,
    COLLECTIONS_COLLECTION,
    EXPERIMENTS_COLLECTION,
    QUERIES_COLLECTION,
    RESULTS_COLLECTION,
    RUN_STATUS_COLLECTION,
    get_collection,
    get_mongo_client,
)
from server.utils.logger import get_logger

logger = get_logger(__name__)

_INDEX_POLL_INTERVAL_S = 5  # seconds between readiness checks while waiting for vector indexes


class _VectorIndexConfig(TypedDict):
    name: str
    dimensions: int
    desc: str


STANDARD_INDEX_SPEC: dict[str, list[IndexModel]] = {
    EXPERIMENTS_COLLECTION: [
        IndexModel([("created_at", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
    ],
    RUN_STATUS_COLLECTION: [
        IndexModel([("experiment_id", ASCENDING)]),
        IndexModel([("phase", ASCENDING)]),
    ],
    CHUNKS_COLLECTION: [
        IndexModel([("experiment_id", ASCENDING)]),
    ],
    COLLECTIONS_COLLECTION: [
        IndexModel([("hash", ASCENDING)]),
    ],
    QUERIES_COLLECTION: [
        IndexModel([("experiment_id", ASCENDING)]),
    ],
    RESULTS_COLLECTION: [
        IndexModel([("experiment_id", ASCENDING)]),
        IndexModel([("query_id", ASCENDING)]),
    ],
}

VECTOR_INDEX_CONFIGS: list[_VectorIndexConfig] = [
    {"name": "vector_index_1024", "dimensions": 1024, "desc": "Voyage models"},
    {"name": "vector_index_384", "dimensions": 384, "desc": "local models (e.g. all-MiniLM-L6-v2)"},
]

TEXT_SEARCH_INDEX_NAME = "text_search_index"
M0_SEARCH_INDEX_LIMIT = 3


class SearchIndexInfo(TypedDict):
    database: str
    collection: str
    name: str
    index_type: str
    status: str
    known: bool


def known_search_index_names() -> frozenset[str]:
    return frozenset([TEXT_SEARCH_INDEX_NAME, *[cfg["name"] for cfg in VECTOR_INDEX_CONFIGS]])


def list_cluster_search_indexes() -> list[SearchIndexInfo]:
    """Return all Atlas Search indexes across every database on the cluster."""
    client = get_mongo_client()
    known = known_search_index_names()
    results: list[SearchIndexInfo] = []

    for db_name in sorted(client.list_database_names()):
        db = client[db_name]
        for coll_name in sorted(db.list_collection_names()):
            coll = db[coll_name]
            try:
                indexes = list(coll.list_search_indexes())
            except Exception:
                continue
            for idx in indexes:
                results.append(
                    SearchIndexInfo(
                        database=db_name,
                        collection=coll_name,
                        name=idx.get("name", "?"),
                        index_type=str(idx.get("type", "?")),
                        status=str(idx.get("status", idx.get("queryable", "?"))),
                        known=idx.get("name", "?") in known,
                    )
                )
    return results


def drop_search_index_at(database: str, collection: str, name: str) -> None:
    """Drop a named Atlas Search index."""
    get_mongo_client()[database][collection].drop_search_index(name)
    logger.info("search index dropped — %s.%s name=%s", database, collection, name)


def prune_unknown_search_indexes() -> list[str]:
    """Drop search indexes not managed by this project. Returns dropped paths."""
    dropped: list[str] = []
    for info in list_cluster_search_indexes():
        if info["known"]:
            continue
        path = f"{info['database']}.{info['collection']}.{info['name']}"
        drop_search_index_at(info["database"], info["collection"], info["name"])
        dropped.append(path)
    return dropped


def reset_chunks_search_indexes() -> None:
    """Drop all search indexes on chunks and recreate vector + text indexes."""
    chunks = get_collection(CHUNKS_COLLECTION)
    for idx in chunks.list_search_indexes():
        name = idx["name"]
        chunks.drop_search_index(name)
        logger.info("chunks search index dropped — name=%s", name)
    create_vector_indexes()
    create_text_search_index()


def _search_index_create_unavailable(err_str: str) -> bool:
    lowered = err_str.lower()
    return (
        "commandnotfound" in lowered
        or "no such command" in lowered
        or "maximum number of fts indexes" in lowered
    )


def _build_vector_index_model(name: str, dimensions: int) -> SearchIndexModel:
    return SearchIndexModel(
        definition={
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": dimensions,
                    "similarity": "cosine",
                },
                {"type": "filter", "path": "experiment_id"},
                {"type": "filter", "path": "embedding_model"},
            ]
        },
        name=name,
        type="vectorSearch",
    )


def _get_existing_search_indexes(collection) -> set[str]:
    """Return names of existing search indexes on a collection."""
    try:
        return {idx["name"] for idx in collection.list_search_indexes()}
    except Exception:
        return set()


def create_vector_indexes() -> bool:
    """Create Atlas vector search indexes programmatically.

    Returns True if all indexes are confirmed active, False if creation
    was skipped (e.g. free-tier cluster) or indexes are still building.
    """
    chunks = get_collection(CHUNKS_COLLECTION)
    existing = _get_existing_search_indexes(chunks)

    needed = [cfg for cfg in VECTOR_INDEX_CONFIGS if cfg["name"] not in existing]
    if not needed:
        logger.info("vector indexes OK — already exist")
        return True

    models = [_build_vector_index_model(cfg["name"], cfg["dimensions"]) for cfg in needed]
    names = [cfg["name"] for cfg in needed]

    try:
        chunks.create_search_indexes(models=models)
        logger.info("vector indexes created — names=%s", names)
    except Exception as e:
        err_str = str(e)
        if _search_index_create_unavailable(err_str):
            if "maximum number of fts indexes" in err_str.lower():
                logger.warning(
                    "vector index quota exceeded — M0 allows %s search indexes cluster-wide; "
                    "run `rag-params-finder indexes list` and `indexes reset --unknown-only`",
                    M0_SEARCH_INDEX_LIMIT,
                )
            else:
                logger.warning(
                    "vector index programmatic unavailable — M0/M2/M5 tiers; "
                    "create Atlas vector indexes manually in UI:",
                )
            _log_manual_instructions()
            return False
        raise

    return _wait_for_indexes_ready(chunks, names)


def ensure_vector_index(dimensions: int) -> bool:
    """Ensure a vector search index exists for a runtime-detected dimension."""
    name = f"vector_index_{dimensions}"
    chunks = get_collection(CHUNKS_COLLECTION)
    existing = _get_existing_search_indexes(chunks)
    if name in existing:
        return True

    try:
        chunks.create_search_indexes(models=[_build_vector_index_model(name, dimensions)])
        logger.info(f"Created vector search index: {name}")
    except Exception as e:
        err_str = str(e)
        if "CommandNotFound" in err_str or "no such command" in err_str.lower():
            logger.warning(
                "Programmatic vector index creation not supported on this cluster tier (M0/M2/M5). "
                f"Create index '{name}' manually in the Atlas UI with numDimensions={dimensions}."
            )
            return False
        raise

    return _wait_for_indexes_ready(chunks, [name])


def _wait_for_indexes_ready(collection, names: list[str], timeout_s: int = 120) -> bool:
    """Poll until all named search indexes reach 'READY' status."""
    logger.info("vector indexes polling — activation timeout=%ss", timeout_s)
    deadline = time.monotonic() + timeout_s

    while time.monotonic() < deadline:
        try:
            statuses = {
                idx["name"]: idx.get("status", idx.get("queryable", False))
                for idx in collection.list_search_indexes()
                if idx["name"] in names
            }
        except Exception:
            statuses = {}

        all_ready = all(s == "READY" or s is True for s in statuses.values()) and len(
            statuses
        ) == len(names)

        if all_ready:
            logger.info("vector indexes ready — names=%s", names)
            return True

        pending = [n for n, s in statuses.items() if s not in ("READY", True)]
        if pending:
            logger.info("vector indexes building — pending=%s", pending)

        time.sleep(_INDEX_POLL_INTERVAL_S)

    logger.warning("vector indexes timeout — waited %ss indexes may still be building", timeout_s)
    return False


def _log_manual_instructions() -> None:
    for cfg in VECTOR_INDEX_CONFIGS:
        logger.info(
            "manual vector index hint — name=%s numDimensions=%s (%s)",
            cfg["name"],
            cfg["dimensions"],
            cfg["desc"],
        )
    logger.info(
        "manual vector index hints — "
        "path=embedding similarity=cosine filters=[experiment_id, embedding_model]"
    )
    logger.info(
        "manual vector index docs — %s",
        "https://www.mongodb.com/docs/atlas/atlas-vector-search/create-index/",
    )


def create_text_search_index() -> bool:
    """Create Atlas Search (BM25) index for sparse and hybrid retrieval.

    Returns True if index is confirmed active, False if creation was skipped
    (e.g. free-tier cluster) or index is still building.
    """
    chunks = get_collection(CHUNKS_COLLECTION)
    existing = _get_existing_search_indexes(chunks)

    if TEXT_SEARCH_INDEX_NAME in existing:
        logger.info("text search index OK — already exists name=%s", TEXT_SEARCH_INDEX_NAME)
        return True

    model = SearchIndexModel(
        definition={
            "mappings": {
                "dynamic": False,
                "fields": {
                    "text": [{"type": "string"}],
                    "experiment_id": [{"type": "token"}],
                    "embedding_model": [{"type": "token"}],
                },
            }
        },
        name=TEXT_SEARCH_INDEX_NAME,
        type="search",
    )

    try:
        chunks.create_search_indexes(models=[model])
        logger.info("text search index created — name=%s", TEXT_SEARCH_INDEX_NAME)
    except Exception as e:
        err_str = str(e)
        if _search_index_create_unavailable(err_str):
            if "maximum number of fts indexes" in err_str.lower():
                logger.warning(
                    "text search index quota exceeded — M0 allows %s search indexes cluster-wide; "
                    "run `rag-params-finder indexes list` and `indexes reset --unknown-only`",
                    M0_SEARCH_INDEX_LIMIT,
                )
            else:
                logger.warning(
                    "text search index programmatic unavailable — M0/M2/M5 tiers; "
                    "create Atlas Search index manually name=%s. "
                    "See docs/user-guide/getting-started.md",
                    TEXT_SEARCH_INDEX_NAME,
                )
            return False
        raise

    return _wait_for_indexes_ready(chunks, [TEXT_SEARCH_INDEX_NAME])


def _desired_keys(models: list[IndexModel]) -> set[tuple[tuple[str, int], ...]]:
    """Extract the key tuples we want so we can compare with what exists."""
    return {tuple(m.document["key"].items()) for m in models}


def _existing_keys(collection: Collection) -> set[tuple[tuple[str, int], ...]]:
    """Return key tuples of indexes already on the collection (excluding _id)."""
    return {
        tuple(info["key"])
        for info in collection.index_information().values()
        if info["key"] != [("_id", 1)]
    }


def _ensure_standard_indexes() -> None:
    """Create standard indexes only for collections that are missing them."""
    created = 0
    for name, models in STANDARD_INDEX_SPEC.items():
        collection = get_collection(name)
        existing = _existing_keys(collection)
        desired = _desired_keys(models)
        missing = desired - existing
        if not missing:
            continue
        needed = [m for m in models if tuple(m.document["key"].items()) in missing]
        collection.create_indexes(needed)
        created += len(needed)
        logger.info("standard indexes created — collection=%s count=%s", name, len(needed))

    if created == 0:
        logger.info("standard indexes OK — all present")
    else:
        logger.info("standard indexes synced — created_total=%s", created)


def ensure_indexes() -> None:
    """Ensure all indexes exist — standard + vector + text search. Skips what's already present."""
    _ensure_standard_indexes()
    create_vector_indexes()
    create_text_search_index()
