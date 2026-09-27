"""
Tests for server.core.retrieval.fusion.

Author: swami
Created: 2026-09-27
Scope: shared (1+cos)/2 score scale; RRF k=60 fusion parity; Mongo hybrid routes through rrf_fuse
"""

from __future__ import annotations

from unittest.mock import patch

from server.core.retrieval.fusion import RRF_K, cosine_to_unit_score, rrf_fuse
from server.core.retrieval.retriever_mongo import hybrid_search
from server.models.results import Chunk, SearchResult


def _hit(chunk_id: str, score: float) -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            id=chunk_id,
            text=chunk_id,
            index=0,
            embedding_model="model-a",
            chunk_method="recursive",
        ),
        dense_score=score,
        rerank_score=None,
        retrieval_method="dense",
        rank=1,
    )


class TestCosineUnitScoreShould:
    def test_given_known_cosine_when_scaled_then_score_is_one_plus_cosine_over_two(self) -> None:
        """
        Scenario: Dense score is on the shared (1+cos)/2 scale.
        Slice: 50 — Elasticsearch adapter core

        Given a raw cosine similarity,
        When it is converted to the shared unit score,
        Then the result equals (1 + cosine) / 2.
        """
        ### Given
        cosine = 0.5
        expected_score = 0.75

        ### When
        actual_score = cosine_to_unit_score(cosine)

        ### Then
        assert actual_score == expected_score, "score must be (1 + cosine) / 2"


class TestRrfFuseShould:
    def test_given_fixed_dual_list_when_fused_then_ranking_matches_k60(self) -> None:
        """
        Scenario: Hybrid RRF parity with Mongo on a fixed fixture.
        Slice: 50 — Elasticsearch adapter core

        Given two ranked lists and k=60,
        When rrf_fuse merges them,
        Then the shared chunk outranks a list-only chunk and the score is 1/(1+k)+1/(1+k).
        """
        ### Given
        dense = [_hit("shared", 0.9), _hit("dense-only", 0.1)]
        sparse = [_hit("shared", 0.2), _hit("sparse-only", 0.8)]
        expected_top = "shared"
        expected_score = 1.0 / (1 + RRF_K) + 1.0 / (1 + RRF_K)

        ### When
        actual = rrf_fuse(dense, sparse, top_k=3)

        ### Then
        assert actual[0].chunk.id == expected_top, "the chunk in both lists must rank first"
        assert actual[0].dense_score == expected_score, "RRF score must use k=60"
        assert actual[0].retrieval_method == "hybrid"
        assert [hit.chunk.id for hit in actual] == ["shared", "dense-only", "sparse-only"]

    def test_given_same_fixture_when_mongo_hybrid_runs_then_ranking_matches_helper(self) -> None:
        """
        Scenario: Extracted RRF helper is the single fusion path.
        Slice: 50 — Elasticsearch adapter core

        Given Mongo hybrid search with dense and sparse patched to a fixed fixture,
        When hybrid search runs,
        Then its ranking matches rrf_fuse on that fixture.
        """
        ### Given
        dense = [_hit("shared", 0.9), _hit("dense-only", 0.1)]
        sparse = [_hit("shared", 0.2), _hit("sparse-only", 0.8)]
        expected = [hit.chunk.id for hit in rrf_fuse(dense, sparse, top_k=3)]

        ### When
        with (
            patch("server.core.retrieval.retriever_mongo.dense_search", return_value=dense),
            patch("server.core.retrieval.retriever_mongo.sparse_search", return_value=sparse),
        ):
            actual = hybrid_search("query", [0.1], "exp", "model-a", "run", top_k=3)

        ### Then
        assert [hit.chunk.id for hit in actual] == expected, "Mongo hybrid must use rrf_fuse"
        assert actual[0].dense_score == rrf_fuse(dense, sparse, top_k=3)[0].dense_score
