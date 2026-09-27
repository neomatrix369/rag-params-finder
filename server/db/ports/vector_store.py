"""VectorStore Protocol — backend-agnostic interface for chunk storage + search.

Splits the vector-data concern out of ``StorageBackend`` (DECISIONS #240): a
``VectorStore`` owns chunk write, chunk delete, chunk stats, retrieval (via
``retriever()``), search-index planning, health, ``storage_mode()``, labels,
and declared ``capabilities()``. ``StorageBackend`` keeps run state
(experiments, runs, results, reconciliation) — its chunk methods stay in place
for Slice 49A and are marked deprecated there; callers move onto this port in
Slice 49B.

Call sites (orchestrator, guards, API helpers) depend on this port, never on
pymongo, psycopg, or a future Elasticsearch client directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from server.core.guards.search_index_plan import SearchIndexAssessment
from server.db.ports.retriever_backend import RetrieverBackend
from server.models.config import ExperimentConfig
from server.models.enums import RetrievalMethod


@dataclass(frozen=True)
class VectorCapabilities:
    """What a vector store can do — the preflight/guard decision surface.

    Replaces engine-name branching (``== "mongodb"`` / ``== "postgres"``) with
    a declared capability set so a new store (e.g. Elasticsearch, Slice 50)
    is a registry entry plus one of these values, not a growing ``if`` chain.
    """

    retrieval_methods: frozenset[RetrievalMethod]
    similarity_metrics: frozenset[str]
    index_types: frozenset[str]
    supported_embedding_dims: frozenset[int]
    supports_metadata_filters: bool
    can_host_run_state: bool
    labels: frozenset[str] = field(default_factory=frozenset)


@runtime_checkable
class VectorStore(Protocol):
    """Port for chunk write/delete/stats, retrieval, index planning, and health.

    ``retriever()`` returns the store's ``RetrieverBackend`` so search stays a
    single contract (``RetrieverBackend.search``) — this port never defines a
    second search API.
    """

    # ── Chunks ────────────────────────────────────────────────────────────────

    def insert_chunks(self, docs: list[dict]) -> None: ...

    def delete_chunks_for_experiment(self, experiment_id: str) -> int: ...

    def get_experiment_db_stats(self, experiment_id: str) -> dict:
        """Compute per-experiment vector-storage and content statistics.

        Same return shape as ``StorageBackend.get_experiment_db_stats`` — see
        that docstring for the full key list.
        """
        ...

    def get_vector_db_stats_grouped(self) -> dict:
        """Compute cluster-grouped vector-storage statistics across experiments.

        Same return shape as ``StorageBackend.get_vector_db_stats_grouped``.
        """
        ...

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retriever(self) -> RetrieverBackend:
        """Return this store's RetrieverBackend for dense/sparse/hybrid search."""
        ...

    # ── Index planning ───────────────────────────────────────────────────────

    def plan_indexes(self, config: ExperimentConfig) -> SearchIndexAssessment:
        """Assess whether the store's indexes/catalog objects satisfy ``config``."""
        ...

    def ensure_indexes(self) -> None:
        """Create any missing collections/indexes/catalog objects this store needs."""
        ...

    # ── Health + identity ─────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """Ping the store; return True when reachable."""
        ...

    def storage_mode(self) -> str:
        """Return the four-value storage mode (e.g. ``mongodb-local``, ``postgres-cloud``)."""
        ...

    def capabilities(self) -> VectorCapabilities:
        """Return this store's declared capability set."""
        ...
