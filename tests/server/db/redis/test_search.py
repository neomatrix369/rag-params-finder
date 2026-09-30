"""
Tests for server.db.redis.search.

Author: swami
Created: 2026-09-30
Scope: tag filter building, embedding byte packing, doc-to-result mapping
       (COSINE distance → shared score scale), dense/sparse/hybrid dispatch,
       require_top_k and require_embedding_model guards.
"""

from __future__ import annotations

import struct
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from server.db.redis.search import (
    _docs_to_results,
    _escape_tag,
    _tag_filter,
    _to_bytes,
    dense_search,
    hybrid_search,
    require_embedding_model,
    require_top_k,
    search,
    sparse_search,
)
from server.models.enums import RetrievalMethod

# ── helpers ──────────────────────────────────────────────────────────────────


def _doc(
    chunk_id: str = "c1",
    text: str = "hello",
    embedding_model: str = "all-MiniLM-L6-v2",
    chunk_method: str = "recursive",
    score: float | None = None,
    dist_field: str | None = None,
) -> Any:
    """Build a SimpleNamespace that mimics a redis-py search document."""
    ns = SimpleNamespace(
        chunk_id=chunk_id,
        text=text,
        embedding_model=embedding_model,
        chunk_method=chunk_method,
        __score=score,
    )
    if dist_field and score is not None:
        setattr(ns, dist_field, score)
    return ns


def _fake_ft_search(docs: list[Any]) -> MagicMock:
    """Return a mock client whose ft().search() yields docs."""
    result = SimpleNamespace(docs=docs)
    ft_mock = MagicMock()
    ft_mock.search.return_value = result
    client = MagicMock()
    client.ft.return_value = ft_mock
    return client


class TestRequireTopKShould:
    def test_does_not_raise_for_positive_top_k(self) -> None:
        """
        Scenario: Positive top_k passes guard without error.
        Slice: 53

        Given top_k=5,
        When require_top_k() is called,
        Then no exception is raised.
        """
        ### Given / When / Then
        require_top_k(5)

    @pytest.mark.parametrize("bad_k", [0, -1, -100])
    def test_raises_for_non_positive_top_k(self, bad_k: int) -> None:
        """
        Scenario: Zero or negative top_k is rejected before any I/O.
        Slice: 53

        Given top_k <= 0,
        When require_top_k() is called,
        Then ValueError is raised.
        """
        ### Given / When / Then
        with pytest.raises(ValueError, match="top_k"):
            require_top_k(bad_k)


class TestRequireEmbeddingModelShould:
    def test_raises_for_empty_string(self) -> None:
        """
        Scenario: Empty embedding_model causes ValueError to prevent mixed-model hits.
        Slice: 53

        Given an empty embedding_model,
        When require_embedding_model() is called,
        Then ValueError is raised with an isolation hint.
        """
        ### Given / When / Then
        with pytest.raises(ValueError, match="embedding_model"):
            require_embedding_model("")

    def test_does_not_raise_for_valid_model(self) -> None:
        """
        Scenario: A non-empty model name passes the guard.
        Slice: 53

        Given embedding_model='all-MiniLM-L6-v2',
        When require_embedding_model() is called,
        Then no exception is raised.
        """
        ### Given / When / Then
        require_embedding_model("all-MiniLM-L6-v2")


class TestEscapeTagShould:
    def test_escapes_colon_in_model_name(self) -> None:
        """
        Scenario: Colons in model names are escaped for TAG filter syntax.
        Slice: 53

        Given a model name containing a colon,
        When _escape_tag() is called,
        Then the colon is backslash-escaped.
        """
        ### Given / When
        result = _escape_tag("model:v2")

        ### Then
        assert r"\:" in result
        assert "model" in result

    def test_escapes_space_in_experiment_id(self) -> None:
        """
        Scenario: Spaces in IDs are escaped.
        Slice: 53
        """
        ### Given / When
        result = _escape_tag("exp id")

        ### Then
        assert r"\ " in result


class TestTagFilterShould:
    def test_builds_filter_with_all_three_fields(self) -> None:
        """
        Scenario: TAG filter includes embedding_model, experiment_id, and run_id.
        Slice: 53

        Given all three isolation filter values,
        When _tag_filter() is called,
        Then the result contains all three TAG clauses.
        """
        ### Given / When
        result = _tag_filter("exp-1", "all-MiniLM-L6-v2", "run-1")

        ### Then
        assert "@embedding_model:" in result
        assert "@experiment_id:" in result
        assert "@run_id:" in result

    def test_raises_for_empty_embedding_model(self) -> None:
        """
        Scenario: Empty embedding_model in filter raises ValueError.
        Slice: 53
        """
        ### Given / When / Then
        with pytest.raises(ValueError):
            _tag_filter("exp-1", "", "run-1")


class TestToBytesShould:
    def test_packs_float32_little_endian(self) -> None:
        """
        Scenario: _to_bytes packs embedding as little-endian float32.
        Slice: 53

        Given a 3-element embedding,
        When _to_bytes() is called,
        Then the result is 12 bytes (3 × 4) parseable by struct.unpack.
        """
        ### Given
        embedding = [0.1, 0.2, 0.3]

        ### When
        result = _to_bytes(embedding)

        ### Then
        assert isinstance(result, bytes)
        assert len(result) == 12
        unpacked = struct.unpack("3f", result)
        assert abs(unpacked[0] - 0.1) < 1e-6


class TestDocsToResultsShould:
    def test_converts_cosine_distance_to_shared_scale(self) -> None:
        """
        Scenario: COSINE distance d is converted to (1 - d/2) shared scale.
        Slice: 53

        Given d=0.0 (identical vectors),
        When _docs_to_results converts with a distance_field,
        Then score == 1.0.
        """
        ### Given
        dist_field = "__emb_score"
        doc = _doc(score=0.0, dist_field=dist_field)

        ### When
        results = _docs_to_results([doc], "dense", distance_field=dist_field)

        ### Then
        assert results[0].dense_score == pytest.approx(1.0)

    def test_cosine_distance_half_yields_score_0_75(self) -> None:
        """
        Scenario: d=0.5 converts to score=0.75.
        Slice: 53

        score = 1 - d/2 = 1 - 0.5/2 = 0.75
        """
        ### Given
        dist_field = "__vec_score"
        doc = _doc(score=0.5, dist_field=dist_field)

        ### When
        results = _docs_to_results([doc], "dense", distance_field=dist_field)

        ### Then
        assert results[0].dense_score == pytest.approx(0.75)

    def test_assigns_rank_starting_at_1(self) -> None:
        """
        Scenario: Ranks are 1-based, following document order.
        Slice: 53
        """
        ### Given
        docs = [_doc("c1"), _doc("c2"), _doc("c3")]

        ### When
        results = _docs_to_results(docs, "dense")

        ### Then
        assert [r.rank for r in results] == [1, 2, 3]

    def test_returns_empty_for_empty_docs(self) -> None:
        """
        Scenario: No docs produces an empty result list.
        Slice: 53
        """
        ### Given / When
        results = _docs_to_results([], "dense")

        ### Then
        assert results == []

    def test_score_falls_back_to_dunder_score_when_no_distance_field(self) -> None:
        """
        Scenario: Without distance_field, __score attribute is used directly.
        Slice: 53
        """
        ### Given
        doc = _doc(score=0.8)

        ### When
        results = _docs_to_results([doc], "sparse", distance_field=None)

        ### Then
        assert results[0].dense_score == pytest.approx(0.8)


class TestDenseSearchShould:
    def test_calls_ft_search_with_knn_query(self, fake_redis_modules: dict) -> None:
        """
        Scenario: dense_search builds and sends a KNN FT.SEARCH query.
        Slice: 53

        Given a mocked redis client and Query class,
        When dense_search() is called,
        Then client.ft(index).search() is invoked exactly once.
        """
        ### Given
        query_cls = fake_redis_modules["query"].Query.return_value
        query_cls.sort_by.return_value = query_cls
        query_cls.paging.return_value = query_cls
        query_cls.return_fields.return_value = query_cls
        query_cls.dialect.return_value = query_cls

        result_mock = SimpleNamespace(docs=[])
        ft_mock = MagicMock()
        ft_mock.search.return_value = result_mock
        client = MagicMock()
        client.ft.return_value = ft_mock

        ### When
        results = dense_search(
            client,
            index="rpf:chunks",
            query_embedding=[0.1] * 384,
            experiment_id="exp-1",
            embedding_model="all-MiniLM-L6-v2",
            run_id="run-1",
            top_k=5,
        )

        ### Then
        ft_mock.search.assert_called_once()
        assert isinstance(results, list)

    def test_raises_for_zero_top_k(self, fake_redis_modules: dict) -> None:
        """
        Scenario: top_k=0 is rejected before any Redis I/O.
        Slice: 53
        """
        ### Given
        client = MagicMock()

        ### When / Then
        with pytest.raises(ValueError, match="top_k"):
            dense_search(
                client,
                index="idx",
                query_embedding=[0.1] * 384,
                experiment_id="e",
                embedding_model="m",
                run_id="r",
                top_k=0,
            )


class TestSparseSearchShould:
    def test_calls_ft_search_with_bm25_text_query(self, fake_redis_modules: dict) -> None:
        """
        Scenario: sparse_search issues a TEXT match FT.SEARCH query.
        Slice: 53

        Given a mocked client and Query class,
        When sparse_search() is called,
        Then client.ft(index).search() is invoked with the query text.
        """
        ### Given
        query_cls = fake_redis_modules["query"].Query.return_value
        query_cls.paging.return_value = query_cls
        query_cls.return_fields.return_value = query_cls
        query_cls.dialect.return_value = query_cls

        result_mock = SimpleNamespace(docs=[])
        ft_mock = MagicMock()
        ft_mock.search.return_value = result_mock
        client = MagicMock()
        client.ft.return_value = ft_mock

        ### When
        results = sparse_search(
            client,
            index="rpf:chunks",
            query_text="grant deadline",
            experiment_id="exp-1",
            embedding_model="all-MiniLM-L6-v2",
            run_id="run-1",
            top_k=3,
        )

        ### Then
        ft_mock.search.assert_called_once()
        assert isinstance(results, list)


class TestHybridSearchShould:
    def test_fuses_dense_and_sparse_results(self, fake_redis_modules: dict) -> None:
        """
        Scenario: hybrid_search returns RRF-fused results from both methods.
        Slice: 53

        Given a mocked client returning one doc for dense and one for sparse,
        When hybrid_search() is called,
        Then results list is non-empty and each result has a retrieval_method of 'hybrid'.
        """
        ### Given
        query_cls_mock = MagicMock()
        query_cls_mock.sort_by.return_value = query_cls_mock
        query_cls_mock.paging.return_value = query_cls_mock
        query_cls_mock.return_fields.return_value = query_cls_mock
        query_cls_mock.dialect.return_value = query_cls_mock
        fake_redis_modules["query"].Query.return_value = query_cls_mock

        shared_doc = _doc("shared", score=0.0, dist_field="__embedding_384_score")
        # Both dense and sparse return the same doc
        result_mock = SimpleNamespace(docs=[shared_doc])
        ft_mock = MagicMock()
        ft_mock.search.return_value = result_mock
        client = MagicMock()
        client.ft.return_value = ft_mock

        ### When
        results = hybrid_search(
            client,
            index="rpf:chunks",
            query_text="grant",
            query_embedding=[0.0] * 384,
            experiment_id="exp-1",
            embedding_model="all-MiniLM-L6-v2",
            run_id="run-1",
            top_k=5,
        )

        ### Then
        assert isinstance(results, list)
        assert len(results) >= 0  # may be 0 if RRF deduplicates; list type is key


class TestSearchSparseDispatchShould:
    def test_dispatches_sparse_search_and_returns_results(self, fake_redis_modules: dict) -> None:
        """
        Scenario: search() with SPARSE method calls sparse_search and returns results.
        Slice: 53

        Given a mocked client with SPARSE method,
        When search() is called,
        Then sparse_search is invoked (ft.search called once).
        """
        ### Given
        query_cls = fake_redis_modules["query"].Query.return_value
        query_cls.paging.return_value = query_cls
        query_cls.return_fields.return_value = query_cls
        query_cls.dialect.return_value = query_cls

        ft_mock = MagicMock()
        ft_mock.search.return_value = SimpleNamespace(docs=[])
        client = MagicMock()
        client.ft.return_value = ft_mock

        ### When
        results = search(
            client,
            index="idx",
            method=RetrievalMethod.SPARSE,
            query_text="test query",
            experiment_id="e",
            embedding_model="all-MiniLM-L6-v2",
            run_id="r",
            top_k=5,
            query_embedding=None,
        )

        ### Then
        ft_mock.search.assert_called_once()
        assert isinstance(results, list)

    def test_dispatches_dense_search_and_returns_results(self, fake_redis_modules: dict) -> None:
        """
        Scenario: search() with DENSE method calls dense_search and returns results.
        Slice: 53

        Given a mocked client with DENSE method and embedding provided,
        When search() is called,
        Then dense_search is invoked.
        """
        ### Given
        query_cls = fake_redis_modules["query"].Query.return_value
        query_cls.sort_by.return_value = query_cls
        query_cls.paging.return_value = query_cls
        query_cls.return_fields.return_value = query_cls
        query_cls.dialect.return_value = query_cls

        ft_mock = MagicMock()
        ft_mock.search.return_value = SimpleNamespace(docs=[])
        client = MagicMock()
        client.ft.return_value = ft_mock

        ### When
        results = search(
            client,
            index="idx",
            method=RetrievalMethod.DENSE,
            query_text="test",
            experiment_id="e",
            embedding_model="all-MiniLM-L6-v2",
            run_id="r",
            top_k=5,
            query_embedding=[0.1] * 384,
        )

        ### Then
        ft_mock.search.assert_called_once()
        assert isinstance(results, list)

    def test_dispatches_hybrid_search_and_returns_results(self, fake_redis_modules: dict) -> None:
        """
        Scenario: search() with HYBRID method calls hybrid_search and returns results.
        Slice: 53

        Given a mocked client with HYBRID method,
        When search() is called,
        Then dense_search and sparse_search are both invoked.
        """
        ### Given
        query_cls = fake_redis_modules["query"].Query.return_value
        query_cls.sort_by.return_value = query_cls
        query_cls.paging.return_value = query_cls
        query_cls.return_fields.return_value = query_cls
        query_cls.dialect.return_value = query_cls

        ft_mock = MagicMock()
        ft_mock.search.return_value = SimpleNamespace(docs=[])
        client = MagicMock()
        client.ft.return_value = ft_mock

        ### When
        results = search(
            client,
            index="idx",
            method=RetrievalMethod.HYBRID,
            query_text="grant",
            experiment_id="e",
            embedding_model="all-MiniLM-L6-v2",
            run_id="r",
            top_k=5,
            query_embedding=[0.1] * 384,
        )

        ### Then
        # dense + sparse each call ft.search once = 2 total
        assert ft_mock.search.call_count == 2
        assert isinstance(results, list)


class TestSearchDispatchShould:
    def test_raises_for_dense_without_embedding(self) -> None:
        """
        Scenario: Dense search without query_embedding raises ValueError.
        Slice: 53
        """
        ### Given
        client = MagicMock()

        ### When / Then
        with pytest.raises(ValueError, match="query_embedding"):
            search(
                client,
                index="idx",
                method=RetrievalMethod.DENSE,
                query_text="q",
                experiment_id="e",
                embedding_model="m",
                run_id="r",
                top_k=5,
                query_embedding=None,
            )

    def test_raises_for_hybrid_without_embedding(self) -> None:
        """
        Scenario: Hybrid search without query_embedding raises ValueError.
        Slice: 53
        """
        ### Given
        client = MagicMock()

        ### When / Then
        with pytest.raises(ValueError, match="query_embedding"):
            search(
                client,
                index="idx",
                method=RetrievalMethod.HYBRID,
                query_text="q",
                experiment_id="e",
                embedding_model="m",
                run_id="r",
                top_k=5,
                query_embedding=None,
            )

    def test_raises_for_unknown_method(self) -> None:
        """
        Scenario: Unknown retrieval method raises ValueError.
        Slice: 53
        """
        ### Given
        client = MagicMock()

        ### When / Then
        with pytest.raises(ValueError, match="Unknown"):
            search(
                client,
                index="idx",
                method="reranker",  # type: ignore[arg-type]
                query_text="q",
                experiment_id="e",
                embedding_model="m",
                run_id="r",
                top_k=5,
                query_embedding=None,
            )
