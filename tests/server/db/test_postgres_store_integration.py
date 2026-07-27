"""
Integration tests for server.db.postgres.postgres_store against a live pgvector database.

Author: Mani Sarkar
Created: 2026-07-25
Scope: Postgres StorageBackend — CRUD round-trips, JSONB/datetime fidelity,
       dual-dimension chunk routing, and FK cascade delete.

These tests need a real Postgres with the vector extension; the SQL and the
document ↔ row mapping are exactly what a mock would hide. Start one with
``./start-services.sh --postgres-local`` (or rely on the CI service container). The
whole module skips when RAG_TEST_DATABASE_URL points nowhere reachable.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

pytest.importorskip("psycopg")

from server.db import postgres  # noqa: E402
from server.db.postgres.postgres_store import PostgresStorageBackend  # noqa: E402
from server.models.enums import ExperimentStatus  # noqa: E402
from tests.helpers.storage_live import (  # noqa: E402
    TEST_DATABASE_URL,
    postgres_reachable,
    postgres_skip_reason,
)

_EXP_ID = "exp-pg-integration"
_RUN_ID = "run-pg-integration"

# skipif must not call postgres_skip_reason() — that can pytest.fail at import
# when RAG_REQUIRE_POSTGRES=1. Fixtures enforce the hard-fail in CI.
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        (not postgres_reachable()) and os.environ.get("RAG_REQUIRE_POSTGRES") != "1",
        reason=f"No Postgres at {TEST_DATABASE_URL} — run ./start-services.sh --postgres-local",
    ),
]


@pytest.fixture
def store(live_postgres_pool: None) -> Iterator[PostgresStorageBackend]:
    """A backend bound to the test database, with the fixture's rows removed.

    Cleanup runs before and after so a crashed run cannot poison the next one.
    Deleting the experiment is enough — the FK cascade takes the children, which
    is also what the cascade test asserts explicitly.
    """
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


def _experiment_doc(**overrides: object) -> dict:
    doc = {
        "experiment_id": _EXP_ID,
        "experiment_name": "pg integration",
        "status": ExperimentStatus.RUNNING,
        "created_at": datetime(2026, 7, 25, 12, 0, tzinfo=UTC),
        "started_at": None,
        "completed_at": None,
        "data_paths": ["./input_data/pdfs/a.pdf"],
        "total_runs": 4,
        "sweep_summary": {"database_provider": "postgres"},
    }
    doc.update(overrides)
    return doc


def _run_doc(**overrides: object) -> dict:
    doc = {
        "run_id": _RUN_ID,
        "experiment_id": _EXP_ID,
        "phase": "queued",
        "created_at": datetime(2026, 7, 25, 12, 1, tzinfo=UTC),
        "updated_at": datetime(2026, 7, 25, 12, 1, tzinfo=UTC),
        "embedding_model": "all-MiniLM-L6-v2",
        "chunking_method": "recursive",
        "chunk_size": 512,
        "overlap": 50,
    }
    doc.update(overrides)
    return doc


def _chunk_doc(chunk_id: str, dimensions: int, **overrides: object) -> dict:
    doc = {
        "chunk_id": chunk_id,
        "experiment_id": _EXP_ID,
        "run_id": _RUN_ID,
        "text": "Pell Grant eligibility depends on financial need.",
        "index": 0,
        "embedding_model": "all-MiniLM-L6-v2",
        "chunk_method": "recursive",
        "chunk_size": 512,
        "overlap": 50,
        "padding": 0,
        "embedding": [0.1] * dimensions,
    }
    doc.update(overrides)
    return doc


class TestPostgresExperimentCrudShould:
    """Scenario: experiment documents survive a Postgres round-trip intact."""

    def test_given_experiment_with_nested_fields_when_read_back_then_doc_matches(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: Promoted columns and the JSONB remainder recombine into one document.
        Slice: slice-33-postgres-schema-crud

        Given an experiment carrying both promoted fields and nested extras,
        When it is inserted and read back by id,
        Then every field returns with its original value and type.
        """
        ### Given
        doc = _experiment_doc()

        ### When
        store.insert_experiment(doc)
        actual = store.find_experiment_by_id(_EXP_ID)

        ### Then
        assert actual is not None, "Expected the inserted experiment to be found"
        assert actual["experiment_name"] == "pg integration"
        assert actual["status"] == ExperimentStatus.RUNNING.value
        assert actual["data_paths"] == ["./input_data/pdfs/a.pdf"], "JSONB list not preserved"
        assert actual["sweep_summary"] == {"database_provider": "postgres"}
        assert actual["created_at"] == datetime(2026, 7, 25, 12, 0, tzinfo=UTC), (
            "TIMESTAMPTZ must return a timezone-aware datetime, not an ISO string"
        )

    def test_given_experiment_when_found_by_id_then_id_field_is_present(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: Boot reconciliation reads doc["_id"], so the adapter synthesises it.
        Slice: slice-33-postgres-schema-crud

        Given an experiment stored in Postgres, which has no Mongo _id,
        When it is fetched by id or listed as running,
        Then _id is derived from the primary key.
        """
        ### Given
        store.insert_experiment(_experiment_doc())

        ### When
        by_id = store.find_experiment_by_id(_EXP_ID)
        running = store.find_running_experiments()

        ### Then
        assert by_id is not None and by_id["_id"] == _EXP_ID
        assert any(row["_id"] == _EXP_ID for row in running), (
            "Running experiments must carry _id for startup reconciliation"
        )

    def test_given_partial_update_when_applied_then_untouched_jsonb_keys_survive(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: A partial update merges into the JSONB blob instead of replacing it.
        Slice: slice-33-postgres-schema-crud

        Given a stored experiment with several JSONB fields,
        When only one of them plus a promoted column is updated,
        Then the updated keys change and the unmentioned keys remain.
        """
        ### Given
        store.insert_experiment(_experiment_doc())

        ### When
        store.update_experiment(
            _EXP_ID,
            {"status": ExperimentStatus.COMPLETE, "completed_count": 4},
        )
        actual = store.find_experiment_by_id(_EXP_ID)

        ### Then
        assert actual is not None
        assert actual["status"] == ExperimentStatus.COMPLETE.value
        assert actual["completed_count"] == 4, "New JSONB key not merged"
        assert actual["total_runs"] == 4, "Pre-existing JSONB key was clobbered by the merge"
        assert actual["data_paths"] == ["./input_data/pdfs/a.pdf"]

    def test_given_running_experiment_when_cancelled_then_status_and_flag_agree(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: Cancellation is visible to the orchestrator's cancel check.
        Slice: slice-33-postgres-schema-crud

        Given a running experiment,
        When it is marked cancelled,
        Then is_experiment_cancelled reports True and completed_at is stamped.
        """
        ### Given
        store.insert_experiment(_experiment_doc())
        assert store.is_experiment_cancelled(_EXP_ID) is False

        ### When
        store.mark_experiment_cancelled(_EXP_ID)
        actual = store.find_experiment_by_id(_EXP_ID)

        ### Then
        assert store.is_experiment_cancelled(_EXP_ID) is True
        assert actual is not None and actual["completed_at"] is not None


class TestPostgresConnectionShould:
    """Scenario: the local container connects without TLS and bootstraps its schema."""

    def test_given_local_container_when_schema_bootstrapped_twice_then_idempotent(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: Boot-time DDL is safe to re-apply on every server start.
        Slice: slice-33-postgres-schema-crud

        Given a local pgvector container reached without TLS,
        When schema.sql is applied a second time,
        Then it succeeds and the vector extension is present.
        """
        ### Given
        from server.db.postgres.postgres_uri import (
            STORAGE_MODE_LOCAL_POSTGRES,
            postgres_storage_mode,
        )

        assert postgres_storage_mode(TEST_DATABASE_URL) == STORAGE_MODE_LOCAL_POSTGRES
        assert "sslmode" not in postgres.postgres_connect_kwargs(TEST_DATABASE_URL), (
            "A local container must not have TLS forced on it"
        )

        ### When
        postgres.bootstrap_schema(TEST_DATABASE_URL)

        ### Then
        assert (
            postgres.fetch_value("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            is not None
        ), "schema.sql must create the vector extension"

    def test_given_string_experiment_id_when_round_tripped_then_exact_string_returns(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: The external experiment_id contract is unchanged by Postgres.
        Slice: slice-33-postgres-schema-crud

        Given the API and CLI address experiments by an opaque string id,
        When such an id is stored and listed back,
        Then the identical string returns — never coerced to a UUID.
        """
        ### Given
        store.insert_experiment(_experiment_doc())

        ### When
        listed = [row for row in store.find_all_experiments() if row["experiment_id"] == _EXP_ID]

        ### Then
        assert len(listed) == 1, "Experiment not found by its string id"
        assert listed[0]["experiment_id"] == _EXP_ID
        assert isinstance(listed[0]["experiment_id"], str)


class TestPostgresRunStatusShould:
    """Scenario: run phase transitions and phase queries behave like Mongo's."""

    def test_given_queued_run_when_phase_updated_then_phase_and_error_persist(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: update_run_phase writes the promoted column and the JSONB extras.
        Slice: slice-33-postgres-schema-crud

        Given a queued run,
        When its phase is advanced to failed with an error message,
        Then both the phase column and the JSONB error/elapsed fields are readable.
        """
        ### Given
        store.insert_experiment(_experiment_doc())
        store.insert_run_status(_run_doc())

        ### When
        store.update_run_phase(
            _RUN_ID,
            phase="failed",
            updated_at=datetime(2026, 7, 25, 12, 5, tzinfo=UTC),
            elapsed_ms=1234,
            error_message="voyage rate limit",
        )
        actual = store.find_run_status(_RUN_ID)

        ### Then
        assert actual is not None
        assert actual["phase"] == "failed"
        assert actual["elapsed_ms"] == 1234
        assert actual["error_message"] == "voyage rate limit"
        assert actual["embedding_model"] == "all-MiniLM-L6-v2", "Original JSONB fields lost"

    def test_given_runs_in_phases_when_counted_and_listed_then_only_phase_matches_return(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: Phase filters drive the dashboard's failed-run panel.
        Slice: slice-33-postgres-schema-crud

        Given two complete runs and one failed run,
        When counting and listing by phase,
        Then each phase reports only its own runs and the limit is honoured.
        """
        ### Given
        store.insert_experiment(_experiment_doc())
        for run_id, phase in (("r1", "complete"), ("r2", "complete"), ("r3", "failed")):
            store.insert_run_status(_run_doc(run_id=run_id, phase=phase))

        ### When
        complete_count = store.count_runs_by_phase(_EXP_ID, "complete")
        failed = store.find_runs_by_phase(_EXP_ID, "failed", 5)
        limited = store.find_runs_by_phase(_EXP_ID, "complete", 1)
        sigs = store.find_completed_run_sigs(_EXP_ID)

        ### Then
        assert complete_count == 2
        assert [run["run_id"] for run in failed] == ["r3"]
        assert len(limited) == 1, "LIMIT not applied to phase query"
        assert len(sigs) == 2, "Completed signatures must cover both complete runs"

    def test_given_running_runs_when_marked_interrupted_then_all_ids_transition(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: Boot reconciliation interrupts every orphaned run in one statement.
        Slice: slice-33-postgres-schema-crud

        Given two runs left mid-flight by a crash,
        When mark_runs_interrupted is called with both ids,
        Then both carry the interrupted phase and the reason.
        """
        ### Given
        store.insert_experiment(_experiment_doc())
        for run_id in ("r1", "r2"):
            store.insert_run_status(_run_doc(run_id=run_id, phase="embedding"))

        ### When
        store.mark_runs_interrupted(
            ["r1", "r2"],
            updated_at=datetime(2026, 7, 25, 12, 9, tzinfo=UTC),
            error_message="server restarted",
        )
        actual = {run["run_id"]: run for run in store.find_run_statuses(_EXP_ID)}

        ### Then
        assert actual["r1"]["phase"] == "interrupted"
        assert actual["r2"]["phase"] == "interrupted"
        assert actual["r1"]["error_message"] == "server restarted"

    def test_given_no_run_ids_when_marked_interrupted_then_nothing_changes(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: An empty interrupt list must not degenerate into a mass update.
        Slice: slice-33-postgres-schema-crud

        Given a run in the embedding phase,
        When mark_runs_interrupted is called with an empty list,
        Then the run keeps its phase.
        """
        ### Given
        store.insert_experiment(_experiment_doc())
        store.insert_run_status(_run_doc(phase="embedding"))

        ### When
        store.mark_runs_interrupted([], updated_at=datetime.now(UTC), error_message="unused")
        actual = store.find_run_status(_RUN_ID)

        ### Then
        assert actual is not None and actual["phase"] == "embedding"


class TestPostgresChunksShould:
    """Scenario: chunks route to the vector column matching their dimension."""

    def test_given_384_and_1024_chunks_when_inserted_then_each_lands_in_its_column(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: One chunks table holds both supported embedding widths.
        Slice: slice-33-postgres-schema-crud

        Given a batch mixing 384-dim and 1024-dim embeddings,
        When inserted in a single call,
        Then each row populates only the column for its dimension.
        """
        ### Given
        store.insert_experiment(_experiment_doc())
        store.insert_run_status(_run_doc())
        docs = [
            _chunk_doc("c-384", 384),
            _chunk_doc("c-1024", 1024, embedding_model="voyage-3.5-lite"),
        ]

        ### When
        store.insert_chunks(docs)
        rows = postgres.fetch_all(
            "SELECT chunk_id, embedding_384 IS NULL AS no_384, embedding_1024 IS NULL AS no_1024 "
            "FROM chunks WHERE experiment_id = %s ORDER BY chunk_id",
            (_EXP_ID,),
        )

        ### Then
        by_id = {row["chunk_id"]: row for row in rows}
        assert by_id["c-1024"]["no_384"] is True and by_id["c-1024"]["no_1024"] is False
        assert by_id["c-384"]["no_384"] is False and by_id["c-384"]["no_1024"] is True

    def test_given_unsupported_dimension_when_inserted_then_raises_with_guidance(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: SPLADE-width vectors fail loudly rather than being silently dropped.
        Slice: slice-33-postgres-schema-crud

        Given a chunk with a 30522-dim sparse embedding,
        When insert_chunks is called,
        Then ValueError names the supported dimensions.
        """
        ### Given
        store.insert_experiment(_experiment_doc())
        store.insert_run_status(_run_doc())

        ### When / Then
        with pytest.raises(ValueError, match="30522-dim"):
            store.insert_chunks([_chunk_doc("c-sparse", 30522)])

    def test_given_no_chunks_when_inserted_then_no_statement_runs(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: An empty parse result must not error.
        Slice: slice-33-postgres-schema-crud

        Given an experiment with no chunks produced,
        When insert_chunks is called with an empty list,
        Then it returns cleanly and the table stays empty.
        """
        ### Given
        store.insert_experiment(_experiment_doc())

        ### When
        store.insert_chunks([])

        ### Then
        assert store.delete_chunks_for_experiment(_EXP_ID) == 0


class TestPostgresCascadeDeleteShould:
    """Scenario: deleting an experiment removes every dependent row."""

    def test_given_experiment_with_children_when_deleted_then_counts_cover_all_tables(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: Cascade delete reports per-table counts like the Mongo adapter.
        Slice: slice-33-postgres-schema-crud

        Given an experiment with a run, two chunks, and a result,
        When delete_experiment_data is called,
        Then every table reports its deleted count and no rows remain.
        """
        ### Given
        store.insert_experiment(_experiment_doc())
        store.insert_run_status(_run_doc())
        store.insert_chunks([_chunk_doc("c-1", 384), _chunk_doc("c-2", 384)])
        store.insert_result(
            {
                "experiment_id": _EXP_ID,
                "run_id": _RUN_ID,
                "query_id": "q1",
                "query_text": "What is the Pell Grant deadline?",
                "results": [{"chunk_id": "c-1", "score": 0.91}],
            }
        )

        ### When
        actual = store.delete_experiment_data(_EXP_ID)

        ### Then
        assert actual == {"chunks": 2, "results": 1, "run_status": 1, "experiments": 1}
        assert store.find_experiment_by_id(_EXP_ID) is None
        assert store.find_run_statuses(_EXP_ID) == []
        assert store.find_results_for_experiment(_EXP_ID) == []

    def test_given_experiment_deleted_directly_when_children_queried_then_fk_cascaded(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: The schema's ON DELETE CASCADE is real, not just adapter bookkeeping.
        Slice: slice-33-postgres-schema-crud

        Given an experiment with a run and a chunk,
        When the experiments row is deleted with raw SQL,
        Then the database removes the dependent rows without adapter help.
        """
        ### Given
        store.insert_experiment(_experiment_doc())
        store.insert_run_status(_run_doc())
        store.insert_chunks([_chunk_doc("c-1", 384)])

        ### When
        postgres.execute("DELETE FROM experiments WHERE experiment_id = %s", (_EXP_ID,))

        ### Then
        assert (
            postgres.fetch_value(
                "SELECT count(*) FROM run_status WHERE experiment_id = %s", (_EXP_ID,)
            )
            == 0
        )
        assert (
            postgres.fetch_value("SELECT count(*) FROM chunks WHERE experiment_id = %s", (_EXP_ID,))
            == 0
        )


class TestPostgresStatsShould:
    """Scenario: the explore and db-stats screens get their shapes from Postgres."""

    def test_given_experiment_with_data_when_db_stats_computed_then_counts_are_reported(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: Per-experiment db stats aggregate chunks and results.
        Slice: slice-33-postgres-schema-crud

        Given an experiment with two chunks under one run and one result,
        When get_experiment_db_stats is called,
        Then the totals, chunking breakdown, and run breakdown reflect the data.
        """
        ### Given
        store.insert_experiment(_experiment_doc())
        store.insert_run_status(_run_doc())
        store.insert_chunks([_chunk_doc("c-1", 384), _chunk_doc("c-2", 384)])
        store.insert_result(
            {"experiment_id": _EXP_ID, "run_id": _RUN_ID, "query_id": "q1", "query_text": "q"}
        )

        ### When
        actual = store.get_experiment_db_stats(_EXP_ID)

        ### Then
        assert actual["total_chunks"] == 2
        assert actual["total_results"] == 1
        assert actual["unique_queries"] == 1
        assert actual["embedding_models"] == ["all-MiniLM-L6-v2"]
        assert actual["embedding_dimensions"] == [384]
        assert actual["chunking_breakdown"] == {"recursive": 2}
        assert actual["run_breakdown"] == [{"run_id": _RUN_ID, "chunks": 2, "results": 1}]
        assert actual["collection_name"] == "chunks"
        # A two-chunk experiment is ~3 KB, which rounds to 0.0 MB; the invariant
        # that holds at every scale is that the parts sum to the whole.
        assert actual["estimated_storage_mb"] == pytest.approx(
            actual["estimated_embedding_mb"] + actual["estimated_metadata_mb"], abs=0.01
        )

    def test_given_experiment_when_explore_source_loaded_then_three_parts_return(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: The Search Explorer's source tuple survives the Postgres mapping.
        Slice: slice-33-postgres-schema-crud

        Given an experiment with one run and one result,
        When load_explore_source is called,
        Then the experiment, results, and run statuses come back populated.
        """
        ### Given
        store.insert_experiment(_experiment_doc())
        store.insert_run_status(_run_doc())
        store.insert_result(
            {
                "experiment_id": _EXP_ID,
                "run_id": _RUN_ID,
                "query_id": "q1",
                "query_text": "q",
                "results": [{"chunk_id": "c-1"}],
            }
        )

        ### When
        experiment, results, runs = store.load_explore_source(_EXP_ID)

        ### Then
        assert experiment is not None and experiment["experiment_id"] == _EXP_ID
        assert len(results) == 1 and results[0]["results"] == [{"chunk_id": "c-1"}]
        assert len(runs) == 1 and runs[0]["run_id"] == _RUN_ID

    def test_given_unknown_experiment_when_explore_source_loaded_then_empty_tuple(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: An unknown id yields the documented empty shape, not an error.
        Slice: slice-33-postgres-schema-crud

        Given no experiment with the requested id,
        When load_explore_source is called,
        Then (None, [], []) is returned.
        """
        ### Given / When
        actual = store.load_explore_source("does-not-exist")

        ### Then
        assert actual == (None, [], [])

    def test_given_experiments_when_grouped_stats_computed_then_group_totals_accumulate(
        self, store: PostgresStorageBackend
    ) -> None:
        """
        Scenario: Grouped vector-db stats carry the cluster capacity block.
        Slice: slice-33-postgres-schema-crud

        Given an experiment with chunks,
        When get_vector_db_stats_grouped is called,
        Then its group totals include the experiment and the capacity keys exist.
        """
        ### Given
        store.insert_experiment(_experiment_doc())
        store.insert_run_status(_run_doc())
        store.insert_chunks([_chunk_doc("c-1", 384)])

        ### When
        actual = store.get_vector_db_stats_grouped()

        ### Then
        groups = actual["groups"]
        assert groups, "Expected at least one vector-db group"
        totals = groups[0]["totals"]
        assert totals["experiment_count"] >= 1
        assert totals["database_used_mb"] > 0, "Postgres database size not reported"
        assert totals["database_storage_limit_mb"] is None, (
            "Postgres exposes no quota over SQL — the limit must stay None"
        )
