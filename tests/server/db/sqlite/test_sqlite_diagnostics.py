"""
Tests for server.db.sqlite.sqlite_diagnostics — boot / healthz run-state probe.

Author: Mani Sarkar
Created: 2026-11-05
Scope: Slice 65B — collect_run_state_diagnostics (read-only inspection that
       never creates the file) and checkpoint_truncate (fresh-connection WAL
       truncate on shutdown).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from server.db.sqlite.sqlite_diagnostics import (
    checkpoint_truncate,
    collect_run_state_diagnostics,
)


def _make_run_state_db(path: Path, *, experiments: int = 0) -> None:
    """Create a minimal WAL-mode run-state DB with the three tables."""
    # -- Given a real SQLite file with the run-state schema --
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE experiments (experiment_id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE run_status (run_id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE results (result_id INTEGER PRIMARY KEY)")
        for i in range(experiments):
            conn.execute("INSERT INTO experiments (experiment_id) VALUES (?)", (f"exp-{i}",))
        conn.commit()
    finally:
        conn.close()


def test_given_missing_file_when_collected_then_exists_false_and_no_file_created(
    tmp_path: Path,
) -> None:
    """
    Scenario: Diagnostics on an absent DB must not create a second file.
    Slice: 65B

    Given a path where no run-state DB exists,
    When collect_run_state_diagnostics runs,
    Then it reports exists=False and still no file is created on disk.
    """
    ### Given
    db_path = tmp_path / "run_state.db"

    ### When
    diag = collect_run_state_diagnostics(str(db_path))

    ### Then
    assert diag["exists"] is False
    assert diag["quick_check"] is None
    assert diag["counts"] == {"experiments": 0, "run_status": 0, "results": 0}
    assert not db_path.exists()


def test_given_populated_db_when_collected_then_reports_path_mode_and_counts(
    tmp_path: Path,
) -> None:
    """
    Scenario: Diagnostics surface the single file's identity for the boot log.
    Slice: 65B

    Given a WAL-mode run-state DB with two experiments,
    When collect_run_state_diagnostics runs,
    Then it reports the resolved path, inode, WAL journal mode, quick_check ok,
         a byte size and the row counts.
    """
    ### Given
    db_path = tmp_path / "run_state.db"
    _make_run_state_db(db_path, experiments=2)

    ### When
    diag = collect_run_state_diagnostics(str(db_path))

    ### Then
    assert diag["exists"] is True
    assert diag["path"] == str(db_path.resolve())
    assert diag["inode"] is not None
    assert diag["journal_mode"] == "wal"
    assert diag["quick_check"] == "ok"
    assert isinstance(diag["db_size_bytes"], int) and diag["db_size_bytes"] > 0
    assert diag["counts"]["experiments"] == 2


def test_given_file_without_tables_when_collected_then_counts_sentinel_minus_one(
    tmp_path: Path,
) -> None:
    """
    Scenario: A pre-bootstrap file (no schema) reports a missing-table sentinel.
    Slice: 65B

    Given an empty SQLite file with no run-state tables,
    When collect_run_state_diagnostics runs,
    Then each count is the -1 missing-table sentinel rather than raising.
    """
    ### Given
    db_path = tmp_path / "run_state.db"
    sqlite3.connect(str(db_path)).close()

    ### When
    diag = collect_run_state_diagnostics(str(db_path))

    ### Then
    assert diag["exists"] is True
    assert diag["counts"] == {"experiments": -1, "run_status": -1, "results": -1}


def test_given_missing_file_when_checkpoint_then_noop_returns_none(tmp_path: Path) -> None:
    """
    Scenario: Shutdown checkpoint on an absent DB is a safe no-op.
    Slice: 65B

    Given a path where no run-state DB exists,
    When checkpoint_truncate runs,
    Then it returns None and creates no file.
    """
    ### Given
    db_path = tmp_path / "run_state.db"

    ### When
    result = checkpoint_truncate(str(db_path))

    ### Then
    assert result is None
    assert not db_path.exists()


def test_given_wal_db_when_checkpoint_then_wal_truncated(tmp_path: Path) -> None:
    """
    Scenario: The shutdown hook folds the WAL back into the main DB.
    Slice: 65B

    Given a WAL-mode DB with an uncheckpointed write holding a non-empty -wal,
    When checkpoint_truncate runs,
    Then it returns "ok" and the -wal file is truncated to zero bytes.
    """
    ### Given
    db_path = tmp_path / "run_state.db"
    _make_run_state_db(db_path)
    # A second connection writes without checkpointing so -wal has frames.
    writer = sqlite3.connect(str(db_path))
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("INSERT INTO experiments (experiment_id) VALUES ('pending')")
    writer.commit()
    writer.close()
    wal = db_path.with_name(db_path.name + "-wal")

    ### When
    result = checkpoint_truncate(str(db_path))

    ### Then
    assert result == "ok"
    assert (not wal.exists()) or wal.stat().st_size == 0
