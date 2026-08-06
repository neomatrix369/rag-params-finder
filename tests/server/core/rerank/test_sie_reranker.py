"""
Tests for server.core.rerank.reranker.

Author: swami
Created: 2026-07-29
Scope: SIE reranking relevance scoring, unreachable SIE error path
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from server.core.rerank.reranker import rerank_results
from server.models.results import Chunk, SearchResult


def _search_result(text: str, dense_score: float, rank: int) -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            id=f"chunk-{rank}",
            text=text,
            index=rank - 1,
            embedding_model="bge-m3",
            chunk_method="recursive",
        ),
        dense_score=dense_score,
        retrieval_method="dense",
        rank=rank,
    )


def test_given_sie_scores_when_rerank_results_then_results_are_sorted_by_relevance() -> None:
    """
    Scenario: SIE reranker sorts results by returned relevance scores.
    Slice: 22 — SIE Scooter

    Given two search results and an SIE reranker score response,
    When rerank_results is called with provider="sie",
    Then the results are returned in descending relevance order with rerank scores attached.
    """
    ### Given
    search_results = [
        _search_result("lower relevance", dense_score=0.7, rank=1),
        _search_result("higher relevance", dense_score=0.6, rank=2),
    ]

    ### When
    with patch("server.core.embedding.sie_embedder.SIEClient") as mock_client_cls:
        mock_client_cls.return_value.score.return_value = [
            {"score": 0.12},
            {"score": 0.91},
        ]
        actual_results = rerank_results(
            query="AI agents",
            search_results=search_results,
            model="bge-reranker",
            top_k=2,
            provider="sie",
        )

    ### Then
    assert [result.chunk.text for result in actual_results] == [
        "higher relevance",
        "lower relevance",
    ], "Expected SIE scores to reorder results by descending relevance."
    assert actual_results[0].rerank_score == 0.91, "Expected the top result to carry the SIE score."
    assert actual_results[0].rank == 1, "Expected reranked results to reset rank positions."


def test_given_unreachable_sie_when_rerank_results_then_runtime_error_mentions_sie() -> None:
    """
    Scenario: Unreachable SIE reranker raises a runtime error.
    Slice: 22 — SIE Scooter

    Given the SIE score endpoint cannot be reached,
    When rerank_results is called with provider="sie",
    Then a RuntimeError is raised and the message contains "SIE unreachable".
    """
    ### Given
    search_results = [_search_result("only result", dense_score=0.7, rank=1)]

    ### When
    with patch("server.core.embedding.sie_embedder.SIEClient") as mock_client_cls:
        mock_client_cls.return_value.score.side_effect = Exception("connection refused")
        with pytest.raises(RuntimeError, match="SIE unreachable"):
            rerank_results(
                query="AI agents",
                search_results=search_results,
                model="bge-reranker",
                top_k=1,
                provider="sie",
            )

    ### Then
    assert True, "Expected unreachable SIE score path to raise a RuntimeError."
