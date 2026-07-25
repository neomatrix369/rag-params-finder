"""RetrieverBackend Protocol — backend-agnostic interface for vector/text retrieval.

Separates dense/sparse/hybrid search from CRUD operations so each adapter
owns its own query surface area.
"""

from typing import Protocol, runtime_checkable

from server.models.enums import RetrievalMethod
from server.models.results import SearchResult


@runtime_checkable
class RetrieverBackend(Protocol):
    """Port for dense, sparse, and hybrid chunk retrieval."""

    def search(
        self,
        method: RetrievalMethod,
        query_text: str,
        experiment_id: str,
        embedding_model: str,
        run_id: str,
        top_k: int,
        query_embedding: list[float] | None,
    ) -> list[SearchResult]: ...
