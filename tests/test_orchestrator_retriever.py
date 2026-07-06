"""Tests for orchestrator → retriever wiring (run-scoped search during QUERYING)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from server.core.orchestrator import _search_reranker_retriever, _search_traditional_retriever
from server.models.config import RetrieverConfig
from server.models.enums import RetrieverType
from server.models.results import Chunk, SearchResult


def _dense_candidate() -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            id="chunk-1",
            text="sample",
            index=0,
            embedding_model="all-MiniLM-L6-v2",
            chunk_method="semantic",
        ),
        dense_score=0.9,
        rerank_score=None,
        retrieval_method="dense",
        rank=1,
    )


@pytest.mark.parametrize(
    "retriever_type",
    [RetrieverType.DENSE, RetrieverType.SPARSE, RetrieverType.HYBRID],
)
@patch("server.core.orchestrator.retriever_search")
def test_search_traditional_retriever_passes_run_id(
    mock_search: MagicMock,
    retriever_type: RetrieverType,
) -> None:
    mock_search.return_value = []

    _search_traditional_retriever(
        RetrieverConfig(type=retriever_type),
        run_id="run-42",
        query_text="What is the Pell Grant?",
        experiment_id="exp-1",
        embedding_model="all-MiniLM-L6-v2",
        embed_query_fn=lambda _q, _m: [0.1, 0.2],
        top_k=10,
        query_embedding=[0.1, 0.2] if retriever_type != RetrieverType.SPARSE else None,
    )

    mock_search.assert_called_once()
    assert mock_search.call_args.kwargs["run_id"] == "run-42"


@patch("server.core.orchestrator._update_phase")
@patch("server.core.orchestrator.rerank_results")
@patch("server.core.orchestrator.retriever_search")
def test_search_reranker_retriever_passes_run_id_to_dense_prefetch(
    mock_search: MagicMock,
    mock_rerank: MagicMock,
    _mock_update_phase: MagicMock,
) -> None:
    mock_search.return_value = [_dense_candidate()]
    mock_rerank.return_value = []

    _search_reranker_retriever(
        RetrieverConfig(
            type=RetrieverType.RERANKER,
            provider="local",
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        ),
        run_id="run-rerank",
        query_text="What is the Pell Grant?",
        experiment_id="exp-1",
        embedding_model="all-MiniLM-L6-v2",
        embed_query_fn=lambda _q, _m: [0.1],
        top_k_initial=20,
        top_k_final=5,
    )

    mock_search.assert_called_once()
    assert mock_search.call_args.kwargs["run_id"] == "run-rerank"
