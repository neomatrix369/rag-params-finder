"""MongoVectorStore — thin composite VectorStore adapter for Atlas / Atlas Local.

Pure composition (DECISIONS #240): every method delegates to an existing
Mongo primitive — ``MongoStorageBackend`` (chunk write/delete/stats),
``MongoRetrieverBackend`` (search), ``server.db.mongo.indexes`` (index
plan/ensure), ``server.db.mongo.mongodb_uri`` (storage_mode), and
``server.core.guards.health_check`` (ping). No new business logic —
see SLICE-49-VECTOR-STORE-PORT-SPLIT-REGISTRY.md "Reuse ledger".
"""

from __future__ import annotations

from server.core.guards.health_check import mongodb_health_status
from server.core.guards.search_index_guard import collect_search_index_snapshot
from server.core.guards.search_index_plan import (
    SearchIndexAssessment,
    SearchIndexMismatchError,
    assess_search_index_readiness,
    required_search_indexes,
    validate_vector_index_feasibility,
)
from server.db.mongo.indexes import ensure_indexes as _mongo_ensure_indexes
from server.db.mongo.mongo_store import (
    MongoRetrieverBackend,
    MongoStorageBackend,
    get_mongo_retriever,
    get_mongo_storage,
)
from server.db.mongo.mongodb_uri import mongodb_storage_mode
from server.db.ports.retriever_backend import RetrieverBackend
from server.db.ports.vector_store import VectorCapabilities
from server.models.config import ExperimentConfig
from server.models.enums import RetrievalMethod
from server.settings import settings

_CAPABILITIES = VectorCapabilities(
    retrieval_methods=frozenset(
        {RetrievalMethod.DENSE, RetrievalMethod.SPARSE, RetrievalMethod.HYBRID}
    ),
    similarity_metrics=frozenset({"cosine"}),
    index_types=frozenset({"vectorSearch", "search"}),
    supported_embedding_dims=frozenset({384, 1024, 30522}),
    supports_metadata_filters=True,
    can_host_run_state=True,
    labels=frozenset({"mongodb", "atlas"}),
)


class MongoVectorStore:
    """VectorStore composed from the existing Mongo chunk/retriever/index primitives.

    Constructed from the same ``MongoStorageBackend`` / ``MongoRetrieverBackend``
    singletons ``store_factory.py`` already returns, so this composite carries
    no state of its own beyond references to what exists.
    """

    def __init__(
        self,
        storage: MongoStorageBackend | None = None,
        retriever: MongoRetrieverBackend | None = None,
    ) -> None:
        self._storage = storage if storage is not None else get_mongo_storage()
        self._retriever = retriever if retriever is not None else get_mongo_retriever()

    # ── Chunks — delegate to MongoStorageBackend ───────────────────────────────

    def insert_chunks(self, docs: list[dict]) -> None:
        self._storage.insert_chunks(docs)

    def delete_chunks_for_experiment(self, experiment_id: str) -> int:
        return self._storage.delete_chunks_for_experiment(experiment_id)

    def get_experiment_db_stats(self, experiment_id: str) -> dict:
        return self._storage.get_experiment_db_stats(experiment_id)

    def get_vector_db_stats_grouped(self) -> dict:
        return self._storage.get_vector_db_stats_grouped()

    # ── Retrieval — delegate to MongoRetrieverBackend ──────────────────────────

    def retriever(self) -> RetrieverBackend:
        return self._retriever

    # ── Index planning — delegate to search_index_plan/guard + indexes.py ─────

    def plan_indexes(self, config: ExperimentConfig) -> SearchIndexAssessment:
        required = required_search_indexes(config)
        feasibility_error = validate_vector_index_feasibility(required)
        if feasibility_error:
            raise SearchIndexMismatchError(feasibility_error)
        snapshot = collect_search_index_snapshot()
        return assess_search_index_readiness(required=required, snapshot=snapshot)

    def ensure_indexes(self) -> None:
        _mongo_ensure_indexes()

    # ── Health + identity ───────────────────────────────────────────────────────

    def health_check(self) -> bool:
        return mongodb_health_status() != "error"

    def storage_mode(self) -> str:
        return mongodb_storage_mode(settings.mongodb_uri or "")

    @classmethod
    def capabilities(cls) -> VectorCapabilities:
        return _CAPABILITIES
