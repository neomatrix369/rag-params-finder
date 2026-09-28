"""Postgres catalog facts that do not import psycopg."""

from __future__ import annotations

from server.core.guards.search_index_plan import (
    POSTGRES_REQUIRED_INDEXES,
    POSTGRES_VECTOR_EXTENSION,
)
from server.db.ports.vector_store import VectorCapabilities
from server.models.enums import RetrievalMethod

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


class PostgresCatalog:
    """Classmethods the public store catalog reads without opening Postgres."""

    @classmethod
    def capabilities(cls) -> VectorCapabilities:
        return _CAPABILITIES

    @classmethod
    def ui_labels(cls) -> dict[str, str]:
        return {"index": "Table", "host": "Host", "section": "Host & Table"}

    @classmethod
    def index_summary(cls) -> dict[str, object]:
        return {
            "extension": POSTGRES_VECTOR_EXTENSION,
            "indexes": sorted(POSTGRES_REQUIRED_INDEXES),
        }
