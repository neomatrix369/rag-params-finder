"""
Tests for server.db.sqlite.sqlite_diagnostics — boot / healthz run-state probe.

Author: Mani Sarkar
Created: 2026-11-05
Scope: Slice 65B — prime_boot_diagnostics (full quick_check + counts, cached once
       at boot), collect_run_state_diagnostics (cheap per-call /healthz snapshot
       that reads the cache and never re-scans), and checkpoint_truncate
       (fresh-connection WAL truncate on shutdown, including the busy=1 path).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from server.db.sqlite import sqlite_diagnostics
from server.db.sqlite.sqlite_diagnostics import (
    _parse_checkpoint_row,
    checkpoint_truncate,
    collect_run_state_diagnostics,
    prime_boot_diagnostics,
)


@pytest.fixture(autouse=True)
def _reset_boot_cache() -> None:
    """Clear the module-level boot cache so tests never leak cached scans."""
    ### Given a clean cache before and after every test
    sqlite_diagnostics._boot_quick_check = None
    sqlite_diagnostics._boot_quick_check_at = None
    sqlite_diagnostics._boot_counts = None
    yield
    sqlite_diagnostics._boot_quick_check = None
    sqlite_diagnostics._boot_quick_check_at = None
    sqlite_diagnostics._boot_counts = None


def _make_run_state_db(path: Path, *, experiments: int = 0) -> None:
    """Create a minimal WAL-mode run-state DB with the three tables."""
    ### Given a real SQLite file with the run-state schema
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
    assert diag["quick_check_at"] is None
    assert diag["counts"] == {"experiments": 0, "run_status": 0, "results": 0}
    assert not db_path.exists()


def test_given_populated_db_when_primed_then_reports_path_mode_and_counts(
    tmp_path: Path,
) -> None:
    """
    Scenario: Boot priming surfaces the single file's identity and slow scans.
    Slice: 65B

    Given a WAL-mode run-state DB with two experiments,
    When prime_boot_diagnostics runs,
    Then it reports the resolved path, inode, WAL journal mode, quick_check ok,
         quick_check_at, a byte size and the row counts.
    """
    ### Given
    db_path = tmp_path / "run_state.db"
    _make_run_state_db(db_path, experiments=2)

    ### When
    diag = prime_boot_diagnostics(str(db_path))

    ### Then
    assert diag["exists"] is True
    assert diag["path"] == str(db_path.resolve())
    assert diag["inode"] is not None
    assert diag["journal_mode"] == "wal"
    assert diag["quick_check"] == "ok"
    assert isinstance(diag["quick_check_at"], float)
    assert isinstance(diag["db_size_bytes"], int) and diag["db_size_bytes"] > 0
    assert diag["counts"]["experiments"] == 2


def test_given_primed_cache_when_collected_then_reports_cached_quick_check_and_counts(
    tmp_path: Path,
) -> None:
    """
    Scenario: The per-call /healthz collector reports the boot-cached scans.
    Slice: 65B

    Given prime_boot_diagnostics has run against a populated DB,
    When collect_run_state_diagnostics runs afterwards,
    Then it reports the cached quick_check, quick_check_at and counts alongside
         the live cheap fields (path, inode, journal mode, sizes).
    """
    ### Given
    db_path = tmp_path / "run_state.db"
    _make_run_state_db(db_path, experiments=3)
    primed = prime_boot_diagnostics(str(db_path))

    ### When
    diag = collect_run_state_diagnostics(str(db_path))

    ### Then
    assert diag["quick_check"] == "ok"
    assert diag["quick_check_at"] == primed["quick_check_at"]
    assert diag["counts"]["experiments"] == 3
    assert diag["journal_mode"] == "wal"
    assert diag["path"] == str(db_path.resolve())


def test_given_file_without_tables_when_primed_then_counts_sentinel_minus_one(
    tmp_path: Path,
) -> None:
    """
    Scenario: A pre-bootstrap file (no schema) reports a missing-table sentinel.
    Slice: 65B

    Given an empty SQLite file with no run-state tables,
    When prime_boot_diagnostics runs,
    Then each count is the -1 missing-table sentinel rather than raising.
    """
    ### Given
    db_path = tmp_path / "run_state.db"
    sqlite3.connect(str(db_path)).close()

    ### When
    diag = prime_boot_diagnostics(str(db_path))

    ### Then
    assert diag["exists"] is True
    assert diag["counts"] == {"experiments": -1, "run_status": -1, "results": -1}


def test_given_populated_db_when_collected_then_quick_check_not_executed(
    tmp_path: Path,
) -> None:
    """
    Scenario: The per-call collector never runs the slow quick_check scan (B1).
    Slice: 65B

    Given a populated run-state DB (boot priming has not run in this test),
    When collect_run_state_diagnostics runs with _run_quick_check patched,
    Then quick_check is never executed — the collector stays cheap per call.
    """
    ### Given
    db_path = tmp_path / "run_state.db"
    _make_run_state_db(db_path, experiments=1)

    ### When
    with patch.object(sqlite_diagnostics, "_run_quick_check") as mock_quick_check:
        collect_run_state_diagnostics(str(db_path))

    ### Then
    assert mock_quick_check.call_count == 0


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


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ((0, 5, 5), (0, 5, 5)),
        ((1, 3, 0), (1, 3, 0)),
        (None, (-1, -1, -1)),
        ((0,), (-1, -1, -1)),
        (("x", "y", "z"), (-1, -1, -1)),
    ],
)
def test_given_checkpoint_rows_when_parsed_then_tuple_or_sentinel(
    row: object, expected: tuple[int, int, int]
) -> None:
    """
    Scenario: The (busy, log, checkpointed) row parses, bad shapes degrade.
    Slice: 65B

    Given a PRAGMA wal_checkpoint result row (well-formed or not),
    When _parse_checkpoint_row runs,
    Then a 3-int tuple is returned, or a (-1,-1,-1) sentinel for a bad shape.
    """
    ### Given / When
    actual = _parse_checkpoint_row(row)

    ### Then
    assert actual == expected


def test_given_busy_checkpoint_when_truncate_then_does_not_claim_success(
    tmp_path: Path,
) -> None:
    """
    Scenario: A busy=1 checkpoint logs a WARNING and does not report success.
    Slice: 65B

    Given a checkpoint whose pragma returns (busy=1, ...) because it was blocked,
    When checkpoint_truncate runs,
    Then it returns "busy" (not "ok") and logs a WARNING so shutdown can see the
         WAL was not fully folded.
    """
    ### Given
    db_path = tmp_path / "run_state.db"
    _make_run_state_db(db_path)

    class _BusyCursor:
        def fetchone(self) -> tuple[int, int, int]:
            return (1, 7, 0)

    class _BusyConn:
        def execute(self, _sql: str) -> _BusyCursor:
            return _BusyCursor()

        def commit(self) -> None:
            return None

        def close(self) -> None:
            return None

    ### When
    with patch.object(sqlite_diagnostics.sqlite3, "connect", return_value=_BusyConn()):
        with patch.object(sqlite_diagnostics.logger, "warning") as mock_warning:
            result = checkpoint_truncate(str(db_path))

    ### Then
    assert result == "busy"
    assert mock_warning.call_count == 1
