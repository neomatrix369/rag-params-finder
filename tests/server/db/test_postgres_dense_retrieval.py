"""
Tests for server.core.retriever_postgres against a live pgvector database.

Author: Mani Sarkar
Created: 2026-07-25
Scope: dense_search — mandatory embedding_model filter, run scoping, dimension
       column selection, ranking and Atlas-comparable scoring; search dispatcher
       — dense/sparse/hybrid routing and missing-embedding rejection.

The mandatory embedding_model filter is the slice's central invariant, so it is
asserted against real SQL rather than a mock: a mocked query would only confirm
our own assumptions about what we wrote.

Needs a live database — ``./start-services.sh --postgres-local``. Skips when absent
unless RAG_REQUIRE_POSTGRES=1 (CI).
"""

from __future__ import annotations

import logging
import math
import os
from collections.abc import Iterator
from unittest.mock import patch

import pytest

pytest.importorskip("psycopg")

import psycopg  # noqa: E402
from pgvector import Vector  # noqa: E402

from server.core import retriever_postgres  # noqa: E402
from server.db import postgres  # noqa: E402
from server.db.postgres.postgres_store import PostgresStorageBackend  # noqa: E402
from server.models.enums import RetrievalMethod  # noqa: E402
from tests.helpers.storage_live import (  # noqa: E402
    TEST_DATABASE_URL,
    postgres_reachable,
    postgres_skip_reason,
)

_EXP_ID = "exp-pg-dense"
_RUN_A = "run-model-a"
_RUN_B = "run-model-b"
_MODEL_A = "all-MiniLM-L6-v2"
# Same 384 width as model A, so both models' vectors land in one column and only
# the embedding_model filter can separate them.
_MODEL_A_TWIN = "bge-small-en-v1.5"
_MODEL_B = "voyage-3.5-lite"

# skipif must not call postgres_skip_reason() — that can pytest.fail at import
# when RAG_REQUIRE_POSTGRES=1. Fixtures enforce the hard-fail in CI.
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        (not postgres_reachable()) and os.environ.get("RAG_REQUIRE_POSTGRES") != "1",
        reason=f"No Postgres at {TEST_DATABASE_URL} — run ./start-services.sh --postgres-local",
    ),
]


def _unit_vector(dimensions: int, hot_index: int) -> list[float]:
    """A one-hot unit vector, so cosine similarity is predictable by construction."""
    vector = [0.0] * dimensions
    vector[hot_index] = 1.0
    return vector


@pytest.fixture
def store(live_postgres_pool: None) -> Iterator[PostgresStorageBackend]:
    """A backend on the test database, with this module's experiment removed."""
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


def _chunk(chunk_id: str, run_id: str, model: str, embedding: list[float], index: int = 0) -> dict:
    return {
        "chunk_id": chunk_id,
        "experiment_id": _EXP_ID,
        "run_id": run_id,
        "text": f"{model} chunk {index}",
        "index": index,
        "embedding_model": model,
        "chunk_method": "recursive",
        "embedding": embedding,
    }


@pytest.fixture
def two_model_corpus(store: PostgresStorageBackend) -> PostgresStorageBackend:
    """Chunks from three models sharing one chunks table.

    The decisive row is ``twin-exact``: a *different* model at the *same* 384
    width, in the *same* run, holding a vector identical to the test query. Only
    the embedding_model filter can exclude it — the dimension column and run_id
    cannot — so it is what makes the isolation test below able to fail. Model B
    at 1024-dim covers the separate concern of column routing.
    """
    store.insert_experiment({"experiment_id": _EXP_ID, "experiment_name": "dense"})
    store.insert_run_status({"run_id": _RUN_A, "experiment_id": _EXP_ID, "phase": "complete"})
    store.insert_run_status({"run_id": _RUN_B, "experiment_id": _EXP_ID, "phase": "complete"})

    store.insert_chunks(
        [
            _chunk("a-exact", _RUN_A, _MODEL_A, _unit_vector(384, 0), index=0),
            _chunk("a-orthogonal", _RUN_A, _MODEL_A, _unit_vector(384, 5), index=1),
            _chunk("twin-exact", _RUN_A, _MODEL_A_TWIN, _unit_vector(384, 0), index=0),
            _chunk("b-only", _RUN_B, _MODEL_B, _unit_vector(1024, 0), index=0),
        ]
    )
    return store


class TestPostgresDenseSearchShould:
    """Scenario: dense search never lets one model's vectors reach another's query."""

    def test_given_same_width_rival_model_when_searched_then_only_the_asked_model_returns(
        self, two_model_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given same width rival model when searched then only the asked model returns.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: The embedding_model filter isolates models that share a column.
        Slice: slice-34-postgres-dense-retrieval

        Given a rival 384-dim model in the same run holding a vector identical to
             the query,
        When dense_search runs for model A,
        Then every hit belongs to model A and the rival's perfect match is absent —
        it would otherwise rank first and silently corrupt the run's scores.
        """
        ### Given
        query = _unit_vector(384, 0)

        ### When
        actual = retriever_postgres.dense_search(query, _EXP_ID, _MODEL_A, _RUN_A, top_k=10)

        ### Then
        assert actual, "Expected at least one hit for model A"
        models = {result.chunk.embedding_model for result in actual}
        assert models == {_MODEL_A}, f"Cross-model contamination — got models {models}"
        assert "twin-exact" not in {result.chunk.id for result in actual}

    def test_given_missing_embedding_model_when_searched_then_raises_before_any_sql(
        self, two_model_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given missing embedding model when searched then raises before any sql.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: An omitted embedding_model is rejected, never treated as "all models".
        Slice: slice-34-postgres-dense-retrieval

        Given an empty embedding_model,
        When dense_search is called,
        Then ValueError explains that cross-model comparison is not allowed.
        """
        ### Given / When / Then
        with pytest.raises(ValueError, match="embedding_model is required"):
            retriever_postgres.dense_search(_unit_vector(384, 0), _EXP_ID, "", _RUN_A, top_k=5)

    def test_given_chunks_in_another_run_when_searched_then_only_this_run_returns(
        self, two_model_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given chunks in another run when searched then only this run returns.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Runs are isolated, so one sweep row cannot borrow another's chunks.
        Slice: slice-34-postgres-dense-retrieval

        Given model A chunks under run A and model B chunks under run B,
        When dense_search runs for model A but names run B,
        Then no hits are returned.
        """
        ### Given / When
        actual = retriever_postgres.dense_search(
            _unit_vector(384, 0), _EXP_ID, _MODEL_A, _RUN_B, top_k=10
        )

        ### Then
        assert actual == [], "run_id filter did not isolate runs"

    def test_given_384_dim_query_against_1024_dim_model_when_searched_then_no_hits(
        self, two_model_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given 384 dim query against 1024 dim model when searched then no hits.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Query width picks its own vector column, so mismatched widths miss.
        Slice: slice-34-postgres-dense-retrieval

        Given a 384-dim query but model B, whose vectors live in the 1024-dim column,
        When dense_search runs,
        Then nothing is returned rather than a comparison against the wrong column.
        """
        ### Given / When
        actual = retriever_postgres.dense_search(
            _unit_vector(384, 0), _EXP_ID, _MODEL_B, _RUN_B, top_k=10
        )

        ### Then
        assert actual == [], "384-dim query reached rows stored in the 1024-dim column"

    def test_given_1024_dim_query_when_searched_then_the_1024_column_is_used(
        self, two_model_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given 1024 dim query when searched then the 1024 column is used.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: The 1024-dim path resolves its own column and returns its own rows.
        Slice: slice-34-postgres-dense-retrieval

        Given a 1024-dim query embedding for model B,
        When dense_search runs,
        Then model B's chunk is returned from the 1024-dim column.
        """
        ### Given
        query = _unit_vector(1024, 0)

        ### When
        actual = retriever_postgres.dense_search(query, _EXP_ID, _MODEL_B, _RUN_B, top_k=5)

        ### Then
        assert [result.chunk.id for result in actual] == ["b-only"]

    def test_given_unsupported_width_when_searched_then_raises_naming_slice_35(
        self, two_model_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given unsupported width when searched then raises naming slice 35.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: A sparse-width query fails loudly rather than querying nothing.
        Slice: slice-34-postgres-dense-retrieval

        Given a 30522-dim SPLADE-style query embedding,
        When dense_search is called,
        Then ValueError names the supported widths.
        """
        ### Given / When / Then
        with pytest.raises(ValueError, match="30522-dim"):
            retriever_postgres.dense_search(
                _unit_vector(30522, 0), _EXP_ID, _MODEL_A, _RUN_A, top_k=5
            )

    def test_given_similar_and_orthogonal_chunks_when_searched_then_ranked_by_similarity(
        self, two_model_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given similar and orthogonal chunks when searched then ranked by similarity.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Results come back ordered best-first with sequential ranks.
        Slice: slice-34-postgres-dense-retrieval

        Given one chunk identical to the query and one orthogonal to it,
        When dense_search runs,
        Then the identical chunk ranks first and ranks number from one.
        """
        ### Given
        query = _unit_vector(384, 0)

        ### When
        actual = retriever_postgres.dense_search(query, _EXP_ID, _MODEL_A, _RUN_A, top_k=10)

        ### Then
        assert [result.chunk.id for result in actual] == ["a-exact", "a-orthogonal"]
        assert [result.rank for result in actual] == [1, 2], "Ranks must be 1-based and sequential"
        assert actual[0].dense_score > actual[1].dense_score

    def test_given_exact_and_orthogonal_matches_when_scored_then_matches_atlas_scale(
        self, two_model_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given exact and orthogonal matches when scored then matches atlas scale.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Scores use Atlas's (1 + cosine) / 2 scale, not raw pgvector distance.
        Slice: slice-34-postgres-dense-retrieval

        Given an identical chunk (cosine 1.0) and an orthogonal one (cosine 0.0),
        When dense_search scores them,
        Then the scores are 1.0 and 0.5 — the same numbers Atlas would report,
        which is what makes the Slice 38 backend comparison meaningful.
        """
        ### Given
        query = _unit_vector(384, 0)

        ### When
        actual = retriever_postgres.dense_search(query, _EXP_ID, _MODEL_A, _RUN_A, top_k=10)

        ### Then
        by_id = {result.chunk.id: result.dense_score for result in actual}
        assert math.isclose(by_id["a-exact"], 1.0, abs_tol=1e-06), (
            f"Identical vector should score 1.0, got {by_id['a-exact']}"
        )
        assert math.isclose(by_id["a-orthogonal"], 0.5, abs_tol=1e-06), (
            f"Orthogonal vector should score 0.5 on the Atlas scale, got {by_id['a-orthogonal']}"
        )

    def test_given_top_k_smaller_than_corpus_when_searched_then_limit_is_applied(
        self, two_model_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given top k smaller than corpus when searched then limit is applied.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: top_k caps the result count.
        Slice: slice-34-postgres-dense-retrieval

        Given two matching chunks for model A,
        When dense_search runs with top_k=1,
        Then only the best hit is returned.
        """
        ### Given / When
        actual = retriever_postgres.dense_search(
            _unit_vector(384, 0), _EXP_ID, _MODEL_A, _RUN_A, top_k=1
        )

        ### Then
        assert [result.chunk.id for result in actual] == ["a-exact"]

    def test_given_unknown_experiment_when_searched_then_returns_no_hits(
        self, two_model_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given unknown experiment when searched then returns no hits.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: An unknown experiment yields nothing rather than erroring.
        Slice: slice-34-postgres-dense-retrieval

        Given an experiment id with no chunks,
        When dense_search runs,
        Then an empty list is returned.
        """
        ### Given / When
        actual = retriever_postgres.dense_search(
            _unit_vector(384, 0), "no-such-experiment", _MODEL_A, _RUN_A, top_k=5
        )

        ### Then
        assert actual == []


class TestPostgresDenseRecallShould:
    """Scenario: filtered dense search returns full, exactly-ordered recall.

    pgvector's HNSW index cannot filter inside the index. If the planner serves
    one of our queries from HNSW, ``experiment_id``/``embedding_model`` become a
    *post*-filter over the ``ef_search`` candidate set, so a query can quietly
    return fewer than ``top_k`` rows — or mis-order them. This tool exists to
    compare retrieval configurations, so silent recall loss would corrupt the very
    numbers it reports. These tests fail if that ever starts happening.
    """

    _CORPUS_SIZE = 60

    @pytest.fixture
    def wide_corpus(self, store: PostgresStorageBackend) -> PostgresStorageBackend:
        """Model A chunks spread over distinct directions, plus rival-model noise.

        The rival rows share the 384 column, so an index-only path that skipped
        the model filter would pull them in and displace genuine hits.
        """
        store.insert_experiment({"experiment_id": _EXP_ID, "experiment_name": "recall"})
        store.insert_run_status({"run_id": _RUN_A, "experiment_id": _EXP_ID, "phase": "complete"})

        docs = [
            _chunk(f"a-{i:03d}", _RUN_A, _MODEL_A, _unit_vector(384, i), index=i)
            for i in range(self._CORPUS_SIZE)
        ]
        docs += [
            _chunk(f"twin-{i:03d}", _RUN_A, _MODEL_A_TWIN, _unit_vector(384, i), index=i)
            for i in range(self._CORPUS_SIZE)
        ]
        store.insert_chunks(docs)
        return store

    def test_given_more_matches_than_top_k_when_searched_then_exactly_top_k_return(
        self, wide_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given more matches than top k when searched then exactly top k return.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: A capped search fills every requested slot.
        Slice: slice-34-postgres-dense-retrieval

        Given 60 matching chunks for model A,
        When dense_search asks for 20,
        Then exactly 20 distinct hits come back — a post-filtered index scan
        would return fewer.
        """
        ### Given / When
        actual = retriever_postgres.dense_search(
            _unit_vector(384, 0), _EXP_ID, _MODEL_A, _RUN_A, top_k=20
        )

        ### Then
        assert len(actual) == 20, f"Recall loss — asked for 20, got {len(actual)}"
        assert len({result.chunk.id for result in actual}) == 20

    def test_given_top_k_covering_corpus_when_searched_then_every_match_returns(
        self, wide_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given top k covering corpus when searched then every match returns.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Full recall — no matching chunk is ever dropped.
        Slice: slice-34-postgres-dense-retrieval

        Given 60 matching chunks and 60 rival-model chunks in the same column,
        When dense_search asks for all 60,
        Then all 60 of model A's chunks are returned and none of the rival's.
        """
        ### Given
        expected = {f"a-{i:03d}" for i in range(self._CORPUS_SIZE)}

        ### When
        actual = retriever_postgres.dense_search(
            _unit_vector(384, 0), _EXP_ID, _MODEL_A, _RUN_A, top_k=self._CORPUS_SIZE
        )

        ### Then
        assert {result.chunk.id for result in actual} == expected

    def test_given_pooled_connection_when_inspected_then_iterative_scan_is_strict(
        self, wide_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given pooled connection when inspected then iterative scan is strict.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Every pooled connection has HNSW iterative scan switched on.
        Slice: slice-34-postgres-dense-retrieval

        Given a connection handed out by the pool,
        When hnsw.iterative_scan is read,
        Then it is strict_order — the setting that stops a filtered HNSW scan from
        returning fewer rows than asked for.
        """
        ### Given / When
        actual = postgres.fetch_value("SHOW hnsw.iterative_scan")

        ### Then
        assert actual == "strict_order"

    def test_given_hnsw_forced_when_searched_then_recall_is_still_complete(
        self, wide_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given hnsw forced when searched then recall is still complete.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Recall survives even when the planner is pushed onto HNSW.
        Slice: slice-34-postgres-dense-retrieval

        Given the btree filter indexes made unavailable inside a rolled-back
             transaction, forcing the HNSW post-filter path,
        When the dense query asks for 20 of model A's 60 chunks,
        Then 20 still come back. Without iterative scan this returns a short set,
        which is the silent failure the pool setting exists to prevent.
        """
        ### Given
        forced_plan_sql = retriever_postgres._dense_query("embedding_384")

        ### When
        with postgres.connection() as conn:
            conn.execute("SET LOCAL enable_seqscan = off")
            for index in ("chunks_model_idx", "chunks_experiment_idx", "chunks_run_idx"):
                conn.execute(f"DROP INDEX {index}")
            with conn.cursor() as cur:
                cur.execute(
                    forced_plan_sql,
                    {
                        "query": Vector(_unit_vector(384, 0)),
                        "experiment_id": _EXP_ID,
                        "embedding_model": _MODEL_A,
                        "run_id": _RUN_A,
                        "top_k": 20,
                    },
                )
                actual = cur.fetchall()
            conn.rollback()

        ### Then
        assert len(actual) == 20, (
            f"HNSW path returned {len(actual)} of 20 — iterative scan is not protecting recall"
        )

    def test_given_wide_corpus_when_searched_then_scores_decrease_monotonically(
        self, wide_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given wide corpus when searched then scores decrease monotonically.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Ordering is exact, best-first, with no approximation artefacts.
        Slice: slice-34-postgres-dense-retrieval

        Given a corpus of distinct directions,
        When dense_search returns hits,
        Then scores never increase as rank grows, and the chunk aligned with the
        query is first.
        """
        ### Given / When
        actual = retriever_postgres.dense_search(
            _unit_vector(384, 7), _EXP_ID, _MODEL_A, _RUN_A, top_k=30
        )

        ### Then
        scores = [result.dense_score for result in actual]
        assert actual[0].chunk.id == "a-007"
        assert scores == sorted(scores, reverse=True), f"Ranking not monotonic: {scores}"


class TestPostgresSearchDispatcherShould:
    """Scenario: the dispatcher routes dense and refuses what it cannot do."""

    def test_given_dense_method_when_dispatched_then_dense_results_return(
        self, two_model_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given dense method when dispatched then dense results return.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: RetrievalMethod.DENSE reaches the pgvector dense path.
        Slice: slice-34-postgres-dense-retrieval

        Given a dense retrieval method and a query embedding,
        When search dispatches,
        Then ranked dense results are returned tagged as dense.
        """
        ### Given / When
        actual = retriever_postgres.search(
            RetrievalMethod.DENSE,
            "anything",
            _EXP_ID,
            _MODEL_A,
            _RUN_A,
            10,
            _unit_vector(384, 0),
        )

        ### Then
        assert actual[0].chunk.id == "a-exact"
        assert actual[0].retrieval_method == "dense"

    def test_given_dense_method_without_embedding_when_dispatched_then_raises(
        self, two_model_corpus: PostgresStorageBackend
    ) -> None:
        """
        Scenario: given dense method without embedding when dispatched then raises.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Dense search cannot proceed without a query vector.
        Slice: slice-34-postgres-dense-retrieval

        Given RetrievalMethod.DENSE and no query embedding,
        When search dispatches,
        Then ValueError says the embedding is required.
        """
        ### Given / When / Then
        with pytest.raises(ValueError, match="query_embedding is required"):
            retriever_postgres.search(
                RetrievalMethod.DENSE, "q", _EXP_ID, _MODEL_A, _RUN_A, 5, None
            )

    @pytest.mark.parametrize(
        "method",
        [RetrievalMethod.SPARSE, RetrievalMethod.HYBRID],
        ids=["sparse", "hybrid"],
    )
    def test_given_sparse_or_hybrid_when_dispatched_then_does_not_raise_not_implemented(
        self, two_model_corpus: PostgresStorageBackend, method: RetrievalMethod
    ) -> None:
        """
        Scenario: given sparse or hybrid when dispatched then does not raise not implemented.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Sparse and hybrid are implemented on Postgres (Slice 35).
        Slice: slice-34-postgres-dense-retrieval (dispatcher smoke)

        Given RetrievalMethod.SPARSE or HYBRID,
        When search dispatches,
        Then NotImplementedError is not raised (detailed behaviour is covered
        in test_postgres_sparse_hybrid.py).
        """
        ### Given / When
        try:
            retriever_postgres.search(
                method, "q", _EXP_ID, _MODEL_A, _RUN_A, 5, _unit_vector(384, 0)
            )
        except NotImplementedError as exc:
            ### Then
            pytest.fail(f"Slice 35 should have implemented {method}: {exc}")

    def test_given_unrecognised_method_when_dispatched_then_raises_value_error(
        self,
    ) -> None:
        """
        Scenario: given unrecognised method when dispatched then raises value error.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: An unrecognised retrieval method is rejected, not ignored.
        Slice: slice-34-postgres-dense-retrieval

        Given a method outside RetrievalMethod,
        When search dispatches,
        Then ValueError names it — a silent no-op here would look like a query
        that simply found nothing.
        """
        ### Given / When / Then
        with pytest.raises(ValueError, match="Unknown retrieval method"):
            retriever_postgres.search(
                "telepathy",  # type: ignore[arg-type]
                "q",
                _EXP_ID,
                _MODEL_A,
                _RUN_A,
                5,
                _unit_vector(384, 0),
            )


class TestPostgresDenseFailureShould:
    """Scenario: a failed vector query says enough to diagnose it."""

    def test_given_query_failure_when_searched_then_context_is_logged_and_raised(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Scenario: given query failure when searched then context is logged and raised.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: A database error surfaces with the identifiers needed to debug it.
        Slice: slice-34-postgres-dense-retrieval

        Given the underlying query raises,
        When dense_search runs,
        Then the error propagates and the log names the experiment, model, and
        vector column — without them, a failure mid-sweep is untraceable to the
        run that caused it.
        """
        ### Given
        boom = psycopg.errors.UndefinedTable('relation "chunks" does not exist')

        ### When
        with (
            patch("server.core.retrieval.retriever_postgres.fetch_all", side_effect=boom),
            caplog.at_level(logging.ERROR),
            pytest.raises(psycopg.errors.UndefinedTable),
        ):
            retriever_postgres.dense_search(
                _unit_vector(384, 0), "exp-boom", _MODEL_A, _RUN_A, top_k=5
            )

        ### Then
        assert "exp-boom" in caplog.text
        assert _MODEL_A in caplog.text
        assert "embedding_384" in caplog.text
