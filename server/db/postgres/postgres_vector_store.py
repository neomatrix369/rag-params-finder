"""PostgresVectorStore — thin composite VectorStore adapter for Supabase / pgvector.

Pure composition (DECISIONS #240): every method delegates to an existing
Postgres primitive — ``PostgresStorageBackend`` (chunk write/delete/stats),
``PostgresRetrieverBackend`` (search), ``server.core.guards.search_index_guard``
(catalog plan) + ``server.db.postgres.postgres.bootstrap_schema`` (ensure), and
``server.db.postgres.postgres_uri`` (storage_mode). No new business logic —
see SLICE-49-VECTOR-STORE-PORT-SPLIT-REGISTRY.md "Reuse ledger".
"""

from __future__ import annotations

from server.core.guards.health_check import postgres_health_status
from server.core.guards.search_index_guard import validate_postgres_experiment_indexes
from server.core.guards.search_index_plan import SearchIndexAssessment
from server.db.ports.retriever_backend import RetrieverBackend
from server.db.ports.vector_store import VectorCapabilities
from server.db.postgres.postgres import bootstrap_schema
from server.db.postgres.postgres_store import (
    PostgresRetrieverBackend,
    PostgresStorageBackend,
    get_postgres_retriever,
    get_postgres_storage,
)
from server.db.postgres.postgres_uri import postgres_storage_mode
from server.models.config import ExperimentConfig
from server.models.enums import RetrievalMethod
from server.settings import settings

_CAPABILITIES = VectorCapabilities(
    retrieval_methods=frozenset(
        {RetrievalMethod.DENSE, RetrievalMethod.SPARSE, RetrievalMethod.HYBRID}
    ),
    similarity_metrics=frozenset({"cosine"}),
    index_types=frozenset({"hnsw", "gin"}),
    supported_embedding_dims=frozenset({384, 1024}),
    supports_metadata_filters=True,
    can_host_run_state=True,
    labels=frozenset({"postgres", "pgvector", "supabase"}),
)


class PostgresVectorStore:
    """VectorStore composed from the existing Postgres chunk/retriever/catalog primitives.

    Constructed from the same ``PostgresStorageBackend`` / ``PostgresRetrieverBackend``
    singletons ``store_factory.py`` already returns, so this composite carries
    no state of its own beyond references to what exists.
    """

    def __init__(
        self,
        storage: PostgresStorageBackend | None = None,
        retriever: PostgresRetrieverBackend | None = None,
    ) -> None:
        self._storage = storage if storage is not None else get_postgres_storage()
        self._retriever = retriever if retriever is not None else get_postgres_retriever()

    # ── Chunks — delegate to PostgresStorageBackend ────────────────────────────

    def insert_chunks(self, docs: list[dict]) -> None:
        self._storage.insert_chunks(docs)

    def delete_chunks_for_experiment(self, experiment_id: str) -> int:
        return self._storage.delete_chunks_for_experiment(experiment_id)

    def get_experiment_db_stats(self, experiment_id: str) -> dict:
        return self._storage.get_experiment_db_stats(experiment_id)

    def get_vector_db_stats_grouped(self) -> dict:
        return self._storage.get_vector_db_stats_grouped()

    # ── Retrieval — delegate to PostgresRetrieverBackend ───────────────────────

    def retriever(self) -> RetrieverBackend:
        return self._retriever

    # ── Index planning — delegate to search_index_guard + schema bootstrap ────

    def plan_indexes(self, config: ExperimentConfig) -> SearchIndexAssessment:
        return validate_postgres_experiment_indexes(config)

    def ensure_indexes(self) -> None:
        bootstrap_schema(settings.database_url or "")

    # ── Health + identity ───────────────────────────────────────────────────────

    def health_check(self) -> bool:
        return postgres_health_status() != "error"

    def storage_mode(self) -> str:
        return postgres_storage_mode(settings.database_url or "")

    def capabilities(self) -> VectorCapabilities:
        return _CAPABILITIES
