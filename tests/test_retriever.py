"""Unit tests for retrieval pipeline filters and search dispatch (run-scoped isolation)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from server.core.retriever import (
    _SPARSE_INDEX_RETRY_ATTEMPTS,
    dense_search,
    hybrid_search,
    search,
    sparse_search,
)
from server.models.enums import RetrievalMethod


def _sparse_hit_doc() -> dict:
    return {
        "chunk_id": "chunk-1",
        "text": "Pell Grant deadline",
        "index": 0,
        "embedding_model": "all-MiniLM-L6-v2",
        "chunk_method": "semantic",
        "score": 0.95,
    }


@pytest.fixture
def mock_aggregate() -> MagicMock:
    with patch("server.core.retriever.get_collection") as get_collection:
        collection = MagicMock()
        collection.aggregate.return_value = []
        get_collection.return_value = collection
        yield collection.aggregate


class TestRetrieverRunScopedFilters:
    """Each sweep run must query only its own stored chunks."""

    def test_dense_search_filters_by_run_id(self, mock_aggregate: MagicMock) -> None:
        dense_search(
            query_embedding=[0.1, 0.2],
            experiment_id="exp-1",
            embedding_model="all-MiniLM-L6-v2",
            run_id="run-a",
            top_k=5,
        )

        pipeline = mock_aggregate.call_args[0][0]
        vector_filter = pipeline[0]["$vectorSearch"]["filter"]
        assert vector_filter["run_id"] == {"$eq": "run-a"}

    def test_sparse_search_filters_by_run_id(self, mock_aggregate: MagicMock) -> None:
        sparse_search(
            query_text="What is the Pell Grant?",
            experiment_id="exp-1",
            embedding_model="all-MiniLM-L6-v2",
            run_id="run-b",
            top_k=5,
        )

        pipeline = mock_aggregate.call_args[0][0]
        filters = pipeline[0]["$search"]["compound"]["filter"]
        run_filter = next(f for f in filters if f["equals"]["path"] == "run_id")
        assert run_filter["equals"]["value"] == "run-b"


class TestSparseSearchRetry:
    """Sparse search retries when Atlas Search index lags behind chunk inserts."""

    def test_sparse_search_retries_until_hits(self, mock_aggregate: MagicMock) -> None:
        mock_aggregate.side_effect = [[], [_sparse_hit_doc()]]

        with patch("server.core.retriever.time.sleep") as mock_sleep:
            results = sparse_search(
                query_text="Pell Grant",
                experiment_id="exp-1",
                embedding_model="all-MiniLM-L6-v2",
                run_id="run-retry",
                top_k=5,
            )

        assert len(results) == 1
        assert results[0].chunk.id == "chunk-1"
        assert mock_aggregate.call_count == 2
        mock_sleep.assert_called_once()

    def test_sparse_search_exhausts_retries_when_index_stays_empty(
        self, mock_aggregate: MagicMock
    ) -> None:
        mock_aggregate.return_value = []

        with patch("server.core.retriever.time.sleep") as mock_sleep:
            results = sparse_search(
                query_text="Pell Grant",
                experiment_id="exp-1",
                embedding_model="all-MiniLM-L6-v2",
                run_id="run-empty",
                top_k=5,
            )

        assert results == []
        assert mock_aggregate.call_count == _SPARSE_INDEX_RETRY_ATTEMPTS
        assert mock_sleep.call_count == _SPARSE_INDEX_RETRY_ATTEMPTS - 1


class TestHybridSearchRunScoped:
    """Hybrid merges dense + sparse; both legs must stay run-scoped."""

    @patch("server.core.retriever.sparse_search")
    @patch("server.core.retriever.dense_search")
    def test_hybrid_search_passes_run_id_to_dense_and_sparse(
        self,
        mock_dense: MagicMock,
        mock_sparse: MagicMock,
    ) -> None:
        mock_dense.return_value = []
        mock_sparse.return_value = []

        hybrid_search(
            query_text="Pell Grant",
            query_embedding=[0.1, 0.2],
            experiment_id="exp-1",
            embedding_model="all-MiniLM-L6-v2",
            run_id="run-hybrid",
            top_k=5,
        )

        mock_dense.assert_called_once_with([0.1, 0.2], "exp-1", "all-MiniLM-L6-v2", "run-hybrid", 5)
        mock_sparse.assert_called_once_with(
            "Pell Grant", "exp-1", "all-MiniLM-L6-v2", "run-hybrid", 5
        )

    @patch("server.core.retriever.sparse_search")
    @patch("server.core.retriever.dense_search")
    def test_hybrid_search_merges_dense_and_sparse_with_rrf(
        self,
        mock_dense: MagicMock,
        mock_sparse: MagicMock,
    ) -> None:
        from server.models.results import Chunk, SearchResult

        shared = SearchResult(
            chunk=Chunk(
                id="shared-chunk",
                text="overlap",
                index=0,
                embedding_model="all-MiniLM-L6-v2",
                chunk_method="semantic",
            ),
            dense_score=0.9,
            rerank_score=None,
            retrieval_method="dense",
            rank=1,
        )
        dense_only = SearchResult(
            chunk=Chunk(
                id="dense-only",
                text="dense",
                index=1,
                embedding_model="all-MiniLM-L6-v2",
                chunk_method="semantic",
            ),
            dense_score=0.8,
            rerank_score=None,
            retrieval_method="dense",
            rank=2,
        )
        sparse_only = SearchResult(
            chunk=Chunk(
                id="sparse-only",
                text="sparse",
                index=2,
                embedding_model="all-MiniLM-L6-v2",
                chunk_method="semantic",
            ),
            dense_score=0.7,
            rerank_score=None,
            retrieval_method="sparse",
            rank=1,
        )
        mock_dense.return_value = [shared, dense_only]
        mock_sparse.return_value = [shared, sparse_only]

        merged = hybrid_search(
            query_text="Pell Grant",
            query_embedding=[0.1],
            experiment_id="exp-1",
            embedding_model="all-MiniLM-L6-v2",
            run_id="run-hybrid",
            top_k=3,
        )

        assert len(merged) == 3
        assert merged[0].chunk.id == "shared-chunk"
        assert merged[0].retrieval_method == "hybrid"
        assert {r.chunk.id for r in merged} == {"shared-chunk", "dense-only", "sparse-only"}


class TestSearchDispatcher:
    """search() routes all retrieval methods with run_id."""

    @patch("server.core.retriever.dense_search")
    def test_search_dense_passes_run_id(self, mock_dense: MagicMock) -> None:
        mock_dense.return_value = []

        search(
            RetrievalMethod.DENSE,
            query_text="q",
            experiment_id="exp-1",
            embedding_model="all-MiniLM-L6-v2",
            run_id="run-dense",
            top_k=10,
            query_embedding=[0.5],
        )

        mock_dense.assert_called_once_with([0.5], "exp-1", "all-MiniLM-L6-v2", "run-dense", 10)

    @patch("server.core.retriever.sparse_search")
    def test_search_sparse_passes_run_id(self, mock_sparse: MagicMock) -> None:
        mock_sparse.return_value = []

        search(
            RetrievalMethod.SPARSE,
            query_text="q",
            experiment_id="exp-1",
            embedding_model="all-MiniLM-L6-v2",
            run_id="run-sparse",
            top_k=10,
        )

        mock_sparse.assert_called_once_with("q", "exp-1", "all-MiniLM-L6-v2", "run-sparse", 10)

    @patch("server.core.retriever.hybrid_search")
    def test_search_hybrid_passes_run_id(self, mock_hybrid: MagicMock) -> None:
        mock_hybrid.return_value = []

        search(
            RetrievalMethod.HYBRID,
            query_text="q",
            experiment_id="exp-1",
            embedding_model="all-MiniLM-L6-v2",
            run_id="run-hybrid",
            top_k=10,
            query_embedding=[0.5],
        )

        mock_hybrid.assert_called_once_with(
            "q", [0.5], "exp-1", "all-MiniLM-L6-v2", "run-hybrid", 10
        )

    def test_search_dense_requires_query_embedding(self) -> None:
        with pytest.raises(ValueError, match="query_embedding is required"):
            search(
                RetrievalMethod.DENSE,
                query_text="q",
                experiment_id="exp-1",
                embedding_model="all-MiniLM-L6-v2",
                run_id="run-1",
            )
