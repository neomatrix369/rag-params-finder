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
        logger.info("All vector search indexes already exist")
        return True

    models = [_build_vector_index_model(cfg["name"], cfg["dimensions"]) for cfg in needed]
    names = [cfg["name"] for cfg in needed]

    try:
        chunks.create_search_indexes(models=models)
        logger.info(f"Created vector search indexes: {names}")
    except Exception as e:
        err_str = str(e)
        if "CommandNotFound" in err_str or "no such command" in err_str.lower():
            logger.warning(
                "Programmatic vector index creation not supported on this cluster tier (M0/M2/M5). "
                "Create indexes manually in the Atlas UI:"
            )
            _log_manual_instructions()
            return False
        raise

    return _wait_for_indexes_ready(chunks, names)


def _wait_for_indexes_ready(collection, names: list[str], timeout_s: int = 120) -> bool:
    """Poll until all named search indexes reach 'READY' status."""
    logger.info(f"Waiting for vector indexes to become active (timeout {timeout_s}s)...")
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
            logger.info(f"Vector indexes active: {names}")
            return True

        pending = [n for n, s in statuses.items() if s not in ("READY", True)]
        if pending:
            logger.info(f"Indexes still building: {pending}")

        time.sleep(_INDEX_POLL_INTERVAL_S)

    logger.warning(
        f"Timed out waiting for vector indexes after {timeout_s}s — they may still be building"
    )
    return False


def _log_manual_instructions() -> None:
    for cfg in VECTOR_INDEX_CONFIGS:
        logger.info(f"  Index '{cfg['name']}': numDimensions={cfg['dimensions']} ({cfg['desc']})")
    logger.info("  path=embedding, similarity=cosine, filters=[experiment_id, embedding_model]")
    logger.info("  See: https://www.mongodb.com/docs/atlas/atlas-vector-search/create-index/")


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
        logger.info(f"Created {len(needed)} index(es) on {name}")

    if created == 0:
        logger.info("All standard indexes already exist")
    else:
        logger.info(f"Created {created} standard index(es) total")


def ensure_indexes() -> None:
    """Ensure all indexes exist — standard + vector search. Skips what's already present."""
    _ensure_standard_indexes()
    create_vector_indexes()
