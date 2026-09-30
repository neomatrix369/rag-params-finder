"""RedisVectorStore — vector-only adapter (cannot host run state, D1)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from server.core.guards.search_index_plan import SearchIndexAssessment, SearchIndexMismatchError
from server.core.model_registry import get_dimensions
from server.db.ports.retriever_backend import RetrieverBackend
from server.db.ports.stats_common import (
    assemble_experiment_db_stats,
    new_vector_db_group,
    vector_db_group_key,
)
from server.db.ports.vector_store import VectorCapabilities
from server.db.redis.client import (
    RedisClientMissingError,
    build_client,
    import_redis,
    raise_if_unreachable,
)
from server.db.redis.preflight import (
    RedisPreflightError,
    run_all_preflight,
)
from server.db.redis.redis_catalog import RedisCatalog
from server.db.redis.schema import (
    ACCEPTED_EVICTION_POLICIES,
    SUPPORTED_DIMS,
    chunk_key,
    field_for_dims,
    index_name_for,
)
from server.db.redis.search import search as redis_search
from server.db.redis.uri import cluster_host, redis_storage_mode
from server.models.config import ExperimentConfig
from server.models.enums import RetrievalMethod
from server.models.results import SearchResult
from server.settings import settings

_PROVIDER = "redis"


class RedisRetrieverBackend:
    """RetrieverBackend over the shared Redis chunks index."""

    def __init__(self, store: RedisVectorStore) -> None:
        self._store = store

    def search(
        self,
        method: RetrievalMethod,
        query_text: str,
        experiment_id: str,
        embedding_model: str,
        run_id: str,
        top_k: int,
        query_embedding: list[float] | None,
    ) -> list[SearchResult]:
        found = self._store.call(
            lambda: redis_search(
                self._store.client(),
                index=self._store.index_name,
                method=method,
                query_text=query_text,
                experiment_id=experiment_id,
                embedding_model=embedding_model,
                run_id=run_id,
                top_k=top_k,
                query_embedding=query_embedding,
            )
        )
        return cast(list[SearchResult], found)


class RedisVectorStore:
    """VectorStore for one ``{prefix}:chunks`` index. Run state stays elsewhere."""

    def __init__(self, client: Any | None = None) -> None:
        if client is None:
            import_redis()
        self._client = client
        self._index = index_name_for(getattr(settings, "redis_index_prefix", "rpf"))

    @property
    def index_name(self) -> str:
        return self._index

    @property
    def url(self) -> str:
        return getattr(settings, "redis_url", "").strip()

    def client(self) -> Any:
        """Return the injected client, or open one. Missing extra fails in ``__init__``."""
        if self._client is None:
            self._client = build_client(self.url)
        return self._client

    def call(self, action: Callable[[], Any]) -> Any:
        """Run ``action`` and turn connection failures into a clear error."""
        try:
            return action()
        except RedisPreflightError:
            raise
        except Exception as exc:
            raise_if_unreachable(exc, self.url)
            raise

    def insert_chunks(self, docs: list[dict]) -> None:
        if not docs:
            return
        pipeline = self.client().pipeline(transaction=False)
        for doc in docs:
            _add_to_pipeline(pipeline, doc)
        self.call(lambda: pipeline.execute())

    def delete_chunks_for_experiment(self, experiment_id: str) -> int:
        """Delete all keys tagged with ``experiment_id``. Returns deleted count."""
        pattern = f"rpf:chunk:{experiment_id}:*"
        deleted = 0
        client = self.client()
        cursor = 0
        while True:
            cursor, keys = self.call(lambda: client.scan(cursor, match=pattern, count=200))
            if keys:
                self.call(lambda: client.delete(*keys))
                deleted += len(keys)
            if cursor == 0:
                break
        return deleted

    def get_experiment_db_stats(self, experiment_id: str) -> dict:
        total = self._count_for_experiment(experiment_id)
        models = self._distinct_tag_values("embedding_model", experiment_id)
        methods = self._tag_counts("chunking_method", experiment_id)
        runs = self._tag_counts("run_id", experiment_id)
        breakdown = [
            {"run_id": run_id, "chunks": count, "results": 0}
            for run_id, count in sorted(runs.items())
        ]
        return assemble_experiment_db_stats(
            None,
            database_provider=_PROVIDER,
            collection_name=self._index,
            cluster_host=cluster_host(self.url),
            index_names=[self._index],
            total_chunks=total,
            embedding_models=sorted(models),
            chunking_breakdown=methods,
            total_results=0,
            unique_queries=0,
            runs_with_data=len(runs),
            run_breakdown=breakdown,
        )

    def get_vector_db_stats_grouped(self) -> dict:
        index_info = self._ft_info_or_empty()
        total_chunks = int(index_info.get("num_docs") or 0)
        if not total_chunks:
            return {"groups": []}
        stats = self._label_stats(total_chunks)
        group_key = vector_db_group_key(self.storage_mode(), stats["cluster_host"])
        group = new_vector_db_group(group_key, stats)
        group["totals"]["total_chunks"] = total_chunks
        return {"groups": [group]}

    def retriever(self) -> RetrieverBackend:
        return RedisRetrieverBackend(self)

    def plan_indexes(self, config: ExperimentConfig) -> SearchIndexAssessment:
        _reject_unsupported_models(config)
        if not self._index_exists():
            return _missing_assessment(self._index)
        return _ready_assessment(self._index)

    def ensure_indexes(self) -> None:
        if self._index_exists():
            return
        _create_index(self.client(), self._index)

    def health_check(self) -> bool:
        if not self.url:
            return False
        try:
            return bool(self.client().ping())
        except RedisClientMissingError:
            return False
        except Exception as exc:
            raise_if_unreachable(exc, self.url)
            return False

    def storage_mode(self) -> str:
        return redis_storage_mode(self.url)

    @classmethod
    def capabilities(cls) -> VectorCapabilities:
        return RedisCatalog.capabilities()

    @classmethod
    def ui_labels(cls) -> dict[str, str]:
        return RedisCatalog.ui_labels()

    @classmethod
    def index_summary(cls) -> dict[str, object]:
        return RedisCatalog.index_summary()

    def run_preflight(
        self,
        *,
        planned_vectors: int,
        dims: int,
    ) -> None:
        """Run all preflight checks (Query Engine, eviction, capacity, AOF)."""
        run_all_preflight(
            self.client(),
            planned_vectors=planned_vectors,
            dims=dims,
            accepted_policies=ACCEPTED_EVICTION_POLICIES,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _index_exists(self) -> bool:
        try:
            self.client().ft(self._index).info()
            return True
        except Exception as exc:
            if _is_not_found(exc):
                return False
            raise

    def _ft_info_or_empty(self) -> dict:
        try:
            info = self.client().ft(self._index).info()
            if isinstance(info, dict):
                return info
            # redis-py returns a flat list in older versions
            return {}
        except Exception:
            return {}

    def _count_for_experiment(self, experiment_id: str) -> int:
        pattern = f"rpf:chunk:{experiment_id}:*"
        count = 0
        cursor = 0
        client = self.client()
        while True:
            cursor, keys = client.scan(cursor, match=pattern, count=200)
            count += len(keys)
            if cursor == 0:
                break
        return count

    def _distinct_tag_values(self, field: str, experiment_id: str) -> list[str]:
        pattern = f"rpf:chunk:{experiment_id}:*"
        values: set[str] = set()
        cursor = 0
        client = self.client()
        while True:
            cursor, keys = client.scan(cursor, match=pattern, count=200)
            for key in keys:
                val = client.hget(key, field)
                if val:
                    values.add(val.decode() if isinstance(val, bytes) else str(val))
            if cursor == 0:
                break
        return list(values)

    def _tag_counts(self, field: str, experiment_id: str) -> dict[str, int]:
        pattern = f"rpf:chunk:{experiment_id}:*"
        counts: dict[str, int] = {}
        cursor = 0
        client = self.client()
        while True:
            cursor, keys = client.scan(cursor, match=pattern, count=200)
            for key in keys:
                val = client.hget(key, field)
                if val:
                    k = val.decode() if isinstance(val, bytes) else str(val)
                    counts[k] = counts.get(k, 0) + 1
            if cursor == 0:
                break
        return counts

    def _label_stats(self, total_chunks: int) -> dict:
        return assemble_experiment_db_stats(
            None,
            database_provider=_PROVIDER,
            collection_name=self._index,
            cluster_host=cluster_host(self.url),
            index_names=[self._index],
            total_chunks=total_chunks,
            embedding_models=[],
            chunking_breakdown={},
            total_results=0,
            unique_queries=0,
            runs_with_data=0,
            run_breakdown=[],
        )


def _add_to_pipeline(pipeline: Any, doc: dict) -> None:
    """Add a pipelined HSET for one chunk document. No TTL is ever set."""
    embedding = list(doc.get("embedding") or [])
    if not embedding:
        return
    field = field_for_dims(len(embedding))
    import struct

    embedding_bytes = struct.pack(f"{len(embedding)}f", *embedding)
    key = chunk_key(
        experiment_id=str(doc.get("experiment_id") or ""),
        run_id=str(doc.get("run_id") or ""),
        chunk_id=str(doc.get("chunk_id") or ""),
    )
    mapping = {
        "chunk_id": str(doc.get("chunk_id") or ""),
        "experiment_id": str(doc.get("experiment_id") or ""),
        "run_id": str(doc.get("run_id") or ""),
        "text": str(doc.get("text") or ""),
        "embedding_model": str(doc.get("embedding_model") or ""),
        "chunking_method": str(doc.get("chunk_method") or doc.get("chunking_method") or ""),
        "chunk_size": int(doc.get("chunk_size") or 0),
        "overlap": int(doc.get("overlap") or 0),
        field: embedding_bytes,
    }
    pipeline.hset(key, mapping=mapping)
    # Never set a TTL on vector keys (GWT: "Vector keys never expire").


def _create_index(client: Any, index_name: str) -> None:
    """Create the Redis chunks index via FT.CREATE."""
    from redis.commands.search.indexDefinition import (  # type: ignore[import-not-found]
        IndexDefinition,
        IndexType,
    )
    from server.db.redis.schema import build_schema_fields

    schema = build_schema_fields()
    client.ft(index_name).create_index(
        schema,
        definition=IndexDefinition(prefix=["rpf:chunk:"], index_type=IndexType.HASH),
    )


def _is_not_found(exc: BaseException) -> bool:
    """True when the exception indicates the FT index does not exist."""
    msg = str(exc).lower()
    return (
        "unknown index name" in msg
        or "no such index" in msg
        or "responseError" in type(exc).__name__.lower()
        and "unknown" in msg
    )


def _reject_unsupported_models(config: ExperimentConfig) -> None:
    problems = [
        f"{model} ({get_dimensions(model)}-dim)"
        for model in config.embedding.models
        if get_dimensions(model) not in SUPPORTED_DIMS
    ]
    if not problems:
        return
    supported = ", ".join(str(dim) for dim in sorted(SUPPORTED_DIMS))
    raise SearchIndexMismatchError(
        "Dimension mismatch: "
        f"{', '.join(problems)} not in capabilities.supported_dims ({supported})."
    )


def _missing_assessment(index: str) -> SearchIndexAssessment:
    required = frozenset({index})
    return SearchIndexAssessment(
        required=required,
        present_ready=frozenset(),
        present_building=frozenset(),
        missing=required,
        cluster_total=0,
        cluster_limit=0,
        available_slots=0,
        unknown_count=0,
        is_satisfied=False,
        failure_reason=f"Redis index {index!r} is missing.",
    )


def _ready_assessment(index: str) -> SearchIndexAssessment:
    required = frozenset({index})
    return SearchIndexAssessment(
        required=required,
        present_ready=required,
        present_building=frozenset(),
        missing=frozenset(),
        cluster_total=1,
        cluster_limit=0,
        available_slots=0,
        unknown_count=0,
        is_satisfied=True,
        failure_reason=None,
    )
