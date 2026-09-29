"""
Tests for server.db.sqlite.sqlite_store — SQLiteStorageBackend adapter (Slice 55, ADR-008).

Author: Mani Sarkar
Created: 2026-09-29
Scope: SQLiteStorageBackend Protocol conformance; schema bootstrap; WAL mode;
       migration sequence (copy → hash-verify → backup → opt-in drop);
       concurrent read/write safety; null snapshot rendering.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from server.db.ports.storage import StorageBackend

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test_run_state.db")


@pytest.fixture()
def store(db_path: str, monkeypatch: pytest.MonkeyPatch):
    """Fresh SQLiteStorageBackend wired to a temp file."""
    import server.db.sqlite.sqlite_store as store_module

    monkeypatch.setattr("server.settings.settings.sqlite_db_path", db_path)
    # Reset thread-local and singleton so each test gets a clean connection + schema
    store_module._local.__dict__.clear()
    store_module._storage = None

    from server.db.sqlite.sqlite_store import SQLiteStorageBackend

    return SQLiteStorageBackend()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_experiment(exp_id: str = "exp-001") -> dict:
    from server.models.enums import ExperimentStatus

    return {
        "_id": exp_id,
        "experiment_id": exp_id,
        "experiment_name": f"test-experiment-{exp_id}",
        "status": ExperimentStatus.RUNNING,
        "created_at": datetime.now(UTC),
        "started_at": None,
        "completed_at": None,
        "config": {"embedding": {"provider": "local", "models": ["all-MiniLM-L6-v2"]}},
        "run_count": 1,
        "sweep_summary": {
            "database_provider": "mongodb",
            "storage_mode": "mongodb-local",
            "embedding_provider": "local",
            "models": ["all-MiniLM-L6-v2"],
        },
    }


def _make_run(run_id: str, exp_id: str = "exp-001") -> dict:
    from server.models.enums import Phase

    return {
        "run_id": run_id,
        "experiment_id": exp_id,
        "phase": Phase.QUEUED,
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_provider": "local",
        "chunking_method": "fixed",
        "chunk_size": 256,
        "overlap": 32,
        "padding": 0,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "elapsed_ms": 0,
        "error_message": None,
        "embedding_dimensions": 384,
    }


def _make_result(run_id: str, exp_id: str = "exp-001") -> dict:
    return {
        "experiment_id": exp_id,
        "run_id": run_id,
        "query_id": "q-001",
        "query_text": "What is the deadline?",
        "results": [{"chunk_id": "c-1", "score": 0.95, "text": "chunk text"}],
    }


# ── Protocol conformance ──────────────────────────────────────────────────────


class TestSQLiteStorageBackendShould:
    """Scenario: SQLiteStorageBackend implements the StorageBackend Protocol."""

    def test_given_sqlite_backend_when_checked_then_satisfies_storage_backend_protocol(
        self, store
    ) -> None:
        """
        Scenario: SQLiteStorageBackend satisfies the StorageBackend runtime protocol.
        Slice: 55 — GWT-storage-protocol-conformance
        """
        ### Given
        ### When
        ### Then
        assert isinstance(store, StorageBackend), (
            "SQLiteStorageBackend must satisfy the StorageBackend Protocol"
        )


# ── Schema and connection ─────────────────────────────────────────────────────


class TestSQLiteSchemaShould:
    """Scenario: Schema bootstraps correctly with WAL mode."""

    def test_given_fresh_db_when_bootstrap_then_tables_exist(self, store, db_path: str) -> None:
        """
        Scenario: fresh DB bootstraps experiments, run_status, results tables.
        Slice: 55 — GWT-schema-bootstrap
        """
        import sqlite3

        ### Given
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        ### When
        tables = [
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]
        conn.close()
        ### Then
        assert "experiments" in tables
        assert "run_status" in tables
        assert "results" in tables
        assert "chunks" not in tables, "SQLite must not have a chunks table"

    def test_given_connection_when_checked_then_wal_mode_active(self, store, db_path: str) -> None:
        """
        Scenario: WAL journal mode is active for concurrency safety.
        Slice: 55 — GWT-wal-mode
        """
        import sqlite3

        ### Given
        conn = sqlite3.connect(db_path)
        ### When
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        ### Then
        assert mode == "wal", f"Expected WAL mode but got {mode!r}"


# ── CRUD ─────────────────────────────────────────────────────────────────────


class TestSQLiteExperimentCRUDShould:
    """Scenario: Experiment CRUD operations work correctly."""

    def test_given_experiment_when_inserted_then_found_by_id(self, store) -> None:
        """
        Scenario: insert and retrieve an experiment document.
        Slice: 55 — GWT-experiment-crud
        """
        ### Given
        doc = _make_experiment()
        ### When
        store.insert_experiment(doc)
        result = store.find_experiment_by_id("exp-001")
        ### Then
        assert result is not None
        assert result["experiment_id"] == "exp-001"
        assert result["experiment_name"] == "test-experiment-exp-001"

    def test_given_experiment_when_listing_then_ordered_newest_first(self, store) -> None:
        """
        Scenario: experiments list is ordered by created_at descending.
        Slice: 55 — GWT-list-ordering
        """
        ### Given
        from datetime import timedelta

        now = datetime.now(UTC)
        exp1 = _make_experiment("exp-a")
        exp1["created_at"] = now - timedelta(hours=2)
        exp2 = _make_experiment("exp-b")
        exp2["created_at"] = now - timedelta(hours=1)
        store.insert_experiment(exp1)
        store.insert_experiment(exp2)
        ### When
        all_exps = store.find_all_experiments()
        ### Then
        ids = [e["experiment_id"] for e in all_exps]
        assert ids.index("exp-b") < ids.index("exp-a"), "Newer experiment must appear first"

    def test_given_experiment_when_status_updated_then_status_reflects_change(self, store) -> None:
        """
        Scenario: updating experiment status persists correctly.
        Slice: 55 — GWT-status-update
        """
        from server.models.enums import ExperimentStatus

        ### Given
        store.insert_experiment(_make_experiment())
        ### When
        store.mark_experiment_cancelled("exp-001")
        result = store.find_experiment_by_id("exp-001")
        ### Then
        assert result is not None
        assert result["status"] == ExperimentStatus.CANCELLED.value

    def test_given_experiment_when_cancelled_then_is_cancelled_returns_true(self, store) -> None:
        """
        Scenario: is_experiment_cancelled returns true after cancellation.
        Slice: 55 — GWT-cancelled-check
        """
        ### Given
        store.insert_experiment(_make_experiment())
        store.mark_experiment_cancelled("exp-001")
        ### When / Then
        assert store.is_experiment_cancelled("exp-001") is True

    def test_given_running_experiment_when_checked_then_is_cancelled_returns_false(
        self, store
    ) -> None:
        """
        Scenario: is_experiment_cancelled returns false for running experiments.
        Slice: 55 — GWT-not-cancelled
        """
        ### Given
        store.insert_experiment(_make_experiment())
        ### When / Then
        assert store.is_experiment_cancelled("exp-001") is False


# ── Run CRUD ─────────────────────────────────────────────────────────────────


class TestSQLiteRunStatusCRUDShould:
    """Scenario: Run status CRUD operations work correctly."""

    def test_given_run_when_inserted_then_found_by_id(self, store) -> None:
        """
        Scenario: insert and retrieve a run_status document.
        Slice: 55 — GWT-run-crud
        """
        ### Given
        store.insert_experiment(_make_experiment())
        run_doc = _make_run("run-001")
        ### When
        store.insert_run_status(run_doc)
        result = store.find_run_status("run-001")
        ### Then
        assert result is not None
        assert result["run_id"] == "run-001"
        assert result["experiment_id"] == "exp-001"

    def test_given_run_when_phase_updated_then_phase_reflects_change(self, store) -> None:
        """
        Scenario: update_run_phase persists phase and elapsed_ms.
        Slice: 55 — GWT-run-phase-update
        """
        from server.models.enums import Phase

        ### Given
        store.insert_experiment(_make_experiment())
        store.insert_run_status(_make_run("run-001"))
        ### When
        store.update_run_phase(
            "run-001",
            phase=Phase.PARSING,
            updated_at=datetime.now(UTC),
            elapsed_ms=1200,
            error_message=None,
        )
        result = store.find_run_status("run-001")
        ### Then
        assert result is not None
        assert result["phase"] == Phase.PARSING.value
        assert result["elapsed_ms"] == 1200

    def test_given_runs_when_marked_interrupted_then_phase_is_interrupted(self, store) -> None:
        """
        Scenario: mark_runs_interrupted sets phase to 'interrupted' for listed run_ids.
        Slice: 55 — GWT-mark-interrupted
        """
        ### Given
        store.insert_experiment(_make_experiment())
        store.insert_run_status(_make_run("run-a"))
        store.insert_run_status(_make_run("run-b"))
        ### When
        store.mark_runs_interrupted(
            ["run-a", "run-b"],
            updated_at=datetime.now(UTC),
            error_message="server restarted",
        )
        ### Then
        ra = store.find_run_status("run-a")
        rb = store.find_run_status("run-b")
        assert ra is not None and ra["phase"] == "interrupted"
        assert rb is not None and rb["phase"] == "interrupted"

    def test_given_run_with_embedding_dimensions_when_retrieved_then_dimensions_present(
        self, store
    ) -> None:
        """
        Scenario: embedding_dimensions stored on run_status and retrieved correctly.
        Slice: 55 — GWT-embedding-dimensions
        """
        ### Given
        store.insert_experiment(_make_experiment())
        run = _make_run("run-001")
        run["embedding_dimensions"] = 384
        ### When
        store.insert_run_status(run)
        result = store.find_run_status("run-001")
        ### Then
        assert result is not None
        assert result["embedding_dimensions"] == 384

    def test_given_run_without_embedding_dimensions_when_retrieved_then_none(self, store) -> None:
        """
        Scenario: embedding_dimensions is None when not set on run_status.
        Slice: 55 — GWT-embedding-dimensions-null
        """
        ### Given
        store.insert_experiment(_make_experiment())
        run = _make_run("run-001")
        run.pop("embedding_dimensions", None)
        ### When
        store.insert_run_status(run)
        result = store.find_run_status("run-001")
        ### Then
        assert result is not None
        assert result["embedding_dimensions"] is None


# ── Results CRUD ──────────────────────────────────────────────────────────────


class TestSQLiteResultsCRUDShould:
    """Scenario: Results CRUD operations work correctly."""

    def test_given_result_when_inserted_then_found_for_experiment(self, store) -> None:
        """
        Scenario: insert and retrieve results for an experiment.
        Slice: 55 — GWT-results-crud
        """
        ### Given
        store.insert_experiment(_make_experiment())
        store.insert_run_status(_make_run("run-001"))
        ### When
        store.insert_result(_make_result("run-001"))
        results = store.find_results_for_experiment("exp-001")
        ### Then
        assert len(results) == 1
        assert results[0]["query_id"] == "q-001"


# ── Cascade delete ────────────────────────────────────────────────────────────


class TestSQLiteCascadeDeleteShould:
    """Scenario: delete_experiment_data removes experiments and related rows."""

    def test_given_experiment_with_runs_and_results_when_deleted_then_all_gone(self, store) -> None:
        """
        Scenario: delete_experiment_data removes experiment, runs, and results.
        Slice: 55 — GWT-cascade-delete
        """
        ### Given
        store.insert_experiment(_make_experiment())
        store.insert_run_status(_make_run("run-001"))
        store.insert_result(_make_result("run-001"))
        ### When
        counts = store.delete_experiment_data("exp-001")
        ### Then
        assert store.find_experiment_by_id("exp-001") is None
        assert store.find_run_statuses("exp-001") == []
        assert store.find_results_for_experiment("exp-001") == []
        assert counts["chunks"] == 0, "SQLite never stores chunks"


# ── Boot reconciliation ───────────────────────────────────────────────────────


class TestSQLiteBootReconciliationShould:
    """Scenario: Boot reconciliation finds and updates stale running experiments."""

    def test_given_running_experiments_when_found_then_returned(self, store) -> None:
        """
        Scenario: find_running_experiments returns experiments with RUNNING status.
        Slice: 55 — GWT-boot-reconciliation
        """
        ### Given
        store.insert_experiment(_make_experiment())
        ### When
        running = store.find_running_experiments()
        ### Then
        assert len(running) == 1
        assert running[0]["experiment_id"] == "exp-001"
        assert "_id" in running[0], "boot reconciliation needs _id"

    def test_given_completed_experiments_when_reconciliation_then_not_in_running(
        self, store
    ) -> None:
        """
        Scenario: completed experiments are not returned by find_running_experiments.
        Slice: 55 — GWT-completed-not-reconciled
        """
        from server.models.enums import ExperimentStatus

        ### Given
        exp = _make_experiment()
        exp["status"] = ExperimentStatus.COMPLETE
        store.insert_experiment(exp)
        ### When
        running = store.find_running_experiments()
        ### Then
        assert running == []


# ── vector_store_snapshot ─────────────────────────────────────────────────────


class TestSQLiteVectorStoreSnapshotShould:
    """Scenario: vector_store_snapshot stored and retrieved on experiments."""

    def test_given_experiment_with_snapshot_when_retrieved_then_snapshot_present(
        self, store
    ) -> None:
        """
        Scenario: vector_store_snapshot stored in experiments table and returned in doc.
        Slice: 55 — GWT-vector-store-snapshot
        """
        ### Given
        exp = _make_experiment()
        exp["vector_store_snapshot"] = {
            "provider": "mongodb",
            "storage_mode": "mongodb-local",
            "cluster_host": "localhost",
            "collection_name": "chunks",
            "index_names": ["vector_index_384"],
            "container": "mongodb-atlas-local",
            "image": "mongodb/mongodb-atlas-local:8.0",
        }
        ### When
        store.insert_experiment(exp)
        result = store.find_experiment_by_id("exp-001")
        ### Then
        assert result is not None
        snap = result.get("vector_store_snapshot")
        assert snap is not None, "vector_store_snapshot must be returned"
        assert snap["provider"] == "mongodb"
        assert snap["collection_name"] == "chunks"

    def test_given_pre_existing_experiment_without_snapshot_when_retrieved_then_null(
        self, store
    ) -> None:
        """
        Scenario: pre-existing experiment without snapshot renders vector_store_snapshot=null.
        Slice: 55 — GWT-pre-existing-null-snapshot
        """
        ### Given
        exp = _make_experiment()
        # Explicitly do not set vector_store_snapshot
        exp.pop("vector_store_snapshot", None)
        ### When
        store.insert_experiment(exp)
        result = store.find_experiment_by_id("exp-001")
        ### Then
        assert result is not None
        assert result.get("vector_store_snapshot") is None, (
            "pre-existing experiment must render vector_store_snapshot=null"
        )


# ── Concurrency ───────────────────────────────────────────────────────────────


class TestSQLiteConcurrencyShould:
    """Scenario: Concurrent sweep write and dashboard read do not cause SQLITE_BUSY."""

    def test_given_concurrent_write_and_read_when_executed_then_no_busy_error(self, store) -> None:
        """
        Scenario: WAL mode allows concurrent reads and writes without SQLITE_BUSY.
        Slice: 55 — GWT-concurrent-no-busy-error
        """
        from server.models.enums import Phase

        ### Given
        store.insert_experiment(_make_experiment())
        errors: list[Exception] = []

        def writer() -> None:
            try:
                for i in range(10):
                    run = _make_run(f"run-concurrent-{i}")
                    store.insert_run_status(run)
                    store.update_run_phase(
                        f"run-concurrent-{i}",
                        phase=Phase.EMBEDDING,
                        updated_at=datetime.now(UTC),
                        elapsed_ms=i * 100,
                        error_message=None,
                    )
            except Exception as exc:
                errors.append(exc)

        def reader() -> None:
            try:
                for _ in range(10):
                    store.find_all_experiments()
                    store.find_run_statuses("exp-001")
            except Exception as exc:
                errors.append(exc)

        ### When
        t_write = threading.Thread(target=writer)
        t_read = threading.Thread(target=reader)
        t_write.start()
        t_read.start()
        t_write.join()
        t_read.join()

        ### Then
        assert errors == [], f"Concurrent access raised errors: {errors}"


# ── Stats ─────────────────────────────────────────────────────────────────────


class TestSQLiteStatsShould:
    """Scenario: Stats methods return correct shapes for the run-state-only store."""

    def test_given_experiment_with_results_when_stats_computed_then_total_chunks_zero(
        self, store
    ) -> None:
        """
        Scenario: get_experiment_db_stats returns 0 total_chunks (no chunks in SQLite).
        Slice: 55 — GWT-sqlite-stats-no-chunks
        """
        ### Given
        store.insert_experiment(_make_experiment())
        store.insert_run_status(_make_run("run-001"))
        store.insert_result(_make_result("run-001"))
        ### When
        stats = store.get_experiment_db_stats("exp-001")
        ### Then
        assert stats["total_chunks"] == 0, "SQLite run-state store has no chunks"
        assert stats["total_results"] == 1
        assert "database_provider" in stats
        assert "collection_name" in stats

    def test_given_no_experiments_when_grouped_stats_then_empty_groups(
        self, store, monkeypatch
    ) -> None:
        """
        Scenario: get_vector_db_stats_grouped returns empty groups when no experiments.
        Slice: 55 — GWT-sqlite-grouped-stats-empty
        """
        ### Given
        monkeypatch.setattr(
            "server.core.guards.health_check.resolve_storage_mode",
            lambda: "sqlite-local",
        )
        ### When
        result = store.get_vector_db_stats_grouped()
        ### Then
        assert "groups" in result
        assert result["groups"] == []
