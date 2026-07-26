"""
Tests for Postgres sparse and hybrid retrieval (Slice 35).

Author: Mani Sarkar
Created: 2026-07-26
Scope: sparse_search — keyword ranking + embedding_model isolation;
       hybrid_search — RRF fusion vs pure dense/sparse; search dispatcher;
       empty embedding_model and missing hybrid embedding guards;
       query-failure logging for sparse and hybrid paths.

Needs a live database — ``./start-services.sh --postgres``. Skips when absent
unless RAG_REQUIRE_POSTGRES=1 (CI).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from unittest.mock import patch

import pytest

pytest.importorskip("psycopg")

import psycopg  # noqa: E402

from server.core import retriever_postgres  # noqa: E402
from server.db import postgres  # noqa: E402
from server.db.postgres_store import PostgresStorageBackend  # noqa: E402
from server.models.enums import RetrievalMethod  # noqa: E402
from tests.helpers.storage_live import (  # noqa: E402
    TEST_DATABASE_URL,
    postgres_reachable,
    postgres_skip_reason,
)

_EXP_ID = "exp-pg-sparse-hybrid"
_RUN_A = "run-sparse-a"
_MODEL_A = "all-MiniLM-L6-v2"
_MODEL_B = "bge-small-en-v1.5"

# skipif must not call postgres_skip_reason() — that can pytest.fail at import
# when RAG_REQUIRE_POSTGRES=1. Fixtures enforce the hard-fail in CI.
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        (not postgres_reachable()) and os.environ.get("RAG_REQUIRE_POSTGRES") != "1",
        reason=f"No Postgres at {TEST_DATABASE_URL} — run ./start-services.sh --postgres",
    ),
]


def _unit_vector(dimensions: int, hot_index: int) -> list[float]:
    vector = [0.0] * dimensions
    vector[hot_index] = 1.0
    return vector


@pytest.fixture
def store(live_postgres_pool: None) -> Iterator[PostgresStorageBackend]:
    from server.settings import settings

    reason = postgres_skip_reason()
    if reason is not None:
        pytest.skip(reason)

    settings.database_url = TEST_DATABASE_URL

    backend = PostgresStorageBackend()
    postgres.execute("DELETE FROM experiments WHERE experiment_id = %s", (_EXP_ID,))
    try:
        yield backend
    finally:
        postgres.execute("DELETE FROM experiments WHERE experiment_id = %s", (_EXP_ID,))


def _chunk(
    chunk_id: str,
    text: str,
    *,
    model: str = _MODEL_A,
    embedding: list[float] | None = None,
    index: int = 0,
) -> dict:
    return {
        "chunk_id": chunk_id,
        "experiment_id": _EXP_ID,
        "run_id": _RUN_A,
        "text": text,
        "index": index,
        "embedding_model": model,
        "chunk_method": "recursive",
        "embedding": embedding if embedding is not None else _unit_vector(384, index % 10),
    }


@pytest.fixture
def keyword_corpus(store: PostgresStorageBackend) -> PostgresStorageBackend:
    """Chunks with distinctive tokens for sparse ranking + a rival-model twin."""
    store.insert_experiment({"experiment_id": _EXP_ID, "experiment_name": "sparse"})
    store.insert_run_status({"run_id": _RUN_A, "experiment_id": _EXP_ID, "phase": "complete"})
    store.insert_chunks(
        [
            _chunk(
                "match-pell",
                "The Pell Grant deadline for federal aid is June 30.",
                embedding=_unit_vector(384, 0),
                index=0,
            ),
            _chunk(
                "unrelated-weather",
                "The weather forecast predicts rain tomorrow afternoon.",
                embedding=_unit_vector(384, 1),
                index=1,
            ),
            _chunk(
                "partial-grant",
                "Students apply for grants through the portal each spring.",
                embedding=_unit_vector(384, 2),
                index=2,
            ),
            _chunk(
                "rival-pell",
                "The Pell Grant deadline for federal aid is June 30.",
                model=_MODEL_B,
                embedding=_unit_vector(384, 0),
                index=0,
            ),
        ]
    )
    return store


@pytest.fixture
def fusion_corpus(store: PostgresStorageBackend) -> PostgresStorageBackend:
    """Corpus where dense and sparse prefer different winners so hybrid differs."""
    store.insert_experiment({"experiment_id": _EXP_ID, "experiment_name": "hybrid"})
    store.insert_run_status({"run_id": _RUN_A, "experiment_id": _EXP_ID, "phase": "complete"})
    # Query text: "Pell Grant deadline"
    # Query embedding: hot at index 0 → dense prefers dense-winner
    # Sparse prefers keyword-winner (has Pell Grant deadline)
    store.insert_chunks(
        [
            _chunk(
                "keyword-winner",
                "The Pell Grant deadline is published each year.",
                embedding=_unit_vector(384, 5),
                index=0,
            ),
            _chunk(
                "dense-winner",
                "Campus dining hours and meal plan options for residents.",
                embedding=_unit_vector(384, 0),
                index=1,
            ),
            _chunk(
                "neither",
                "Library hours and quiet study rooms on the third floor.",
                embedding=_unit_vector(384, 9),
                index=2,
            ),
        ]
    )
    return store


class TestPostgresSparseSearchShould:
    """Scenario: sparse keyword search ranks distinctive tokens above noise."""

    def test_given_distinctive_tokens_when_sparse_searched_then_match_ranks_first(
        self, keyword_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: Sparse search returns keyword matches ahead of unrelated text.
        Slice: slice-35-postgres-sparse-hybrid

        Given chunks containing distinctive tokens and unrelated prose,
        When sparse retrieval runs for a matching query,
        Then those chunks rank above unrelated chunks.
        """
        ### Given
        query = "Pell Grant deadline"

        ### When
        actual = retriever_postgres.sparse_search(query, _EXP_ID, _MODEL_A, _RUN_A, top_k=5)

        ### Then
        assert actual, "Expected at least one sparse hit"
        assert actual[0].chunk.id == "match-pell"
        assert actual[0].retrieval_method == "sparse"
        assert "unrelated-weather" not in {r.chunk.id for r in actual[:1]}

    def test_given_rival_model_same_text_when_sparse_searched_then_only_asked_model(
        self, keyword_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: embedding_model filter isolates keyword hits across models.
        Slice: slice-35-postgres-sparse-hybrid

        Given identical keyword text under a different embedding_model,
        When sparse_search runs for model A,
        Then the rival model's chunk is absent.
        """
        ### When
        actual = retriever_postgres.sparse_search(
            "Pell Grant deadline", _EXP_ID, _MODEL_A, _RUN_A, top_k=10
        )

        ### Then
        ids = {r.chunk.id for r in actual}
        assert "match-pell" in ids
        assert "rival-pell" not in ids

    def test_given_empty_embedding_model_when_sparse_searched_then_raises(
        self, keyword_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: Empty embedding_model is rejected before SQL.
        Slice: slice-35-postgres-sparse-hybrid

        Given an empty embedding_model,
        When sparse_search is called,
        Then ValueError explains the filter is required.
        """
        ### Given / When / Then
        with pytest.raises(ValueError, match="embedding_model is required"):
            retriever_postgres.sparse_search("Pell", _EXP_ID, "", _RUN_A, top_k=5)


class TestPostgresHybridSearchShould:
    """Scenario: hybrid RRF fusion differs from pure dense and pure sparse."""

    def test_given_divergent_rank_lists_when_hybrid_then_order_differs_from_pure(
        self, fusion_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: Hybrid uses RRF fusion of dense and sparse candidate sets.
        Slice: slice-35-postgres-sparse-hybrid

        Given dense and sparse prefer different winners,
        When hybrid_search runs,
        Then fused ranking differs from pure dense and pure sparse in the
        expected direction (both candidates appear; top is not forced to either
        pure-list #1 alone when both contribute).
        """
        ### Given
        query_text = "Pell Grant deadline"
        query_embedding = _unit_vector(384, 0)

        ### When
        dense = retriever_postgres.dense_search(query_embedding, _EXP_ID, _MODEL_A, _RUN_A, top_k=3)
        sparse = retriever_postgres.sparse_search(query_text, _EXP_ID, _MODEL_A, _RUN_A, top_k=3)
        hybrid = retriever_postgres.hybrid_search(
            query_text, query_embedding, _EXP_ID, _MODEL_A, _RUN_A, top_k=3
        )

        ### Then
        assert dense[0].chunk.id == "dense-winner"
        assert sparse[0].chunk.id == "keyword-winner"
        assert hybrid, "Expected hybrid hits"
        assert hybrid[0].retrieval_method == "hybrid"
        hybrid_ids = [r.chunk.id for r in hybrid]
        assert "keyword-winner" in hybrid_ids
        assert "dense-winner" in hybrid_ids
        # RRF with both lists contributing should not equal either pure order
        assert hybrid_ids != [r.chunk.id for r in dense]
        assert hybrid_ids != [r.chunk.id for r in sparse]

    def test_given_hybrid_without_embedding_when_dispatched_then_raises(
        self, fusion_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: Hybrid requires a query embedding.
        Slice: slice-35-postgres-sparse-hybrid

        Given RetrievalMethod.HYBRID and no query embedding,
        When search dispatches,
        Then ValueError says the embedding is required.
        """
        ### Given / When / Then
        with pytest.raises(ValueError, match="query_embedding is required"):
            retriever_postgres.search(
                RetrievalMethod.HYBRID, "Pell", _EXP_ID, _MODEL_A, _RUN_A, 5, None
            )


class TestPostgresSparseHybridDispatcherShould:
    """Scenario: search() routes sparse and hybrid to the new paths."""

    def test_given_sparse_method_when_dispatched_then_returns_sparse_results(
        self, keyword_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: Dispatcher routes SPARSE to sparse_search.
        Slice: slice-35-postgres-sparse-hybrid

        Given RetrievalMethod.SPARSE,
        When search runs,
        Then results use retrieval_method sparse.
        """
        ### When
        actual = retriever_postgres.search(
            RetrievalMethod.SPARSE,
            "Pell Grant deadline",
            _EXP_ID,
            _MODEL_A,
            _RUN_A,
            5,
            None,
        )

        ### Then
        assert actual
        assert actual[0].retrieval_method == "sparse"

    def test_given_hybrid_method_when_dispatched_then_returns_hybrid_results(
        self, fusion_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: Dispatcher routes HYBRID to hybrid_search.
        Slice: slice-35-postgres-sparse-hybrid

        Given RetrievalMethod.HYBRID with a query embedding,
        When search runs,
        Then results use retrieval_method hybrid.
        """
        ### When
        actual = retriever_postgres.search(
            RetrievalMethod.HYBRID,
            "Pell Grant deadline",
            _EXP_ID,
            _MODEL_A,
            _RUN_A,
            5,
            _unit_vector(384, 0),
        )

        ### Then
        assert actual
        assert actual[0].retrieval_method == "hybrid"


class TestPostgresSparseHybridFailureShould:
    """Scenario: sparse/hybrid query failures log enough context to debug."""

    def test_given_sparse_query_failure_when_searched_then_context_is_logged_and_raised(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Scenario: A sparse SQL error surfaces with experiment and model ids.
        Slice: slice-35-postgres-sparse-hybrid

        Given the underlying sparse query raises,
        When sparse_search runs,
        Then the error propagates and the log names the experiment and model.
        """
        ### Given
        boom = psycopg.errors.UndefinedTable('relation "chunks" does not exist')

        ### When
        with (
            patch("server.core.retriever_postgres.fetch_all", side_effect=boom),
            caplog.at_level(logging.ERROR),
            pytest.raises(psycopg.errors.UndefinedTable),
        ):
            retriever_postgres.sparse_search(
                "Pell Grant deadline", "exp-boom", _MODEL_A, _RUN_A, top_k=5
            )

        ### Then
        assert "exp-boom" in caplog.text
        assert _MODEL_A in caplog.text

    def test_given_hybrid_query_failure_when_searched_then_context_is_logged_and_raised(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Scenario: A hybrid SQL error surfaces with experiment, model, and column.
        Slice: slice-35-postgres-sparse-hybrid

        Given the underlying hybrid query raises,
        When hybrid_search runs,
        Then the error propagates and the log names experiment, model, and column.
        """
        ### Given
        boom = psycopg.errors.UndefinedTable('relation "chunks" does not exist')

        ### When
        with (
            patch("server.core.retriever_postgres.fetch_all", side_effect=boom),
            caplog.at_level(logging.ERROR),
            pytest.raises(psycopg.errors.UndefinedTable),
        ):
            retriever_postgres.hybrid_search(
                "Pell Grant deadline",
                _unit_vector(384, 0),
                "exp-boom",
                _MODEL_A,
                _RUN_A,
                top_k=5,
            )

        ### Then
        assert "exp-boom" in caplog.text
        assert _MODEL_A in caplog.text
        assert "embedding_384" in caplog.text
