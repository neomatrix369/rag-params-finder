"""
Tests for SQLite run-state diagnostics surfaced in /healthz (storage_health).

Author: Mani Sarkar
Created: 2026-11-05
Scope: Slice 65B — storage_health() exposes stores.run_state.diagnostics with the
       resolved path and the boot-cached quick_check while keeping every pre-65B
       key intact, and never re-runs the slow quick_check scan per /healthz (B1).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from server.core.health_check import storage_health
from server.db.sqlite import sqlite_diagnostics
from server.db.sqlite.sqlite_diagnostics import prime_boot_diagnostics


@pytest.fixture(autouse=True)
def _reset_boot_cache() -> None:
    """Clear the module-level boot cache so tests never leak cached scans."""
    sqlite_diagnostics._boot_quick_check = None
    sqlite_diagnostics._boot_quick_check_at = None
    sqlite_diagnostics._boot_counts = None
    yield
    sqlite_diagnostics._boot_quick_check = None
    sqlite_diagnostics._boot_quick_check_at = None
    sqlite_diagnostics._boot_counts = None


def _make_run_state_db(path: Path) -> None:
    """A minimal run-state DB so quick_check returns ok."""
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("CREATE TABLE experiments (experiment_id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE run_status (run_id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE results (result_id INTEGER PRIMARY KEY)")
        conn.commit()
    finally:
        conn.close()


def test_given_sqlite_run_state_when_storage_health_then_run_state_diagnostics_present(
    tmp_path: Path,
) -> None:
    """
    Scenario: /healthz confirms the one run-state DB path and quick_check.
    Slice: 65B

    Given STORAGE_BACKEND=sqlite with a real run-state DB on disk and boot
          priming already run,
    When storage_health runs,
    Then stores.run_state carries a diagnostics block with the resolved path and
         the boot-cached quick_check=ok, and the pre-65B keys (ok, provider,
         mode) still hold.
    """
    ### Given
    db_path = tmp_path / "run_state.db"
    _make_run_state_db(db_path)
    prime_boot_diagnostics(str(db_path))

    with patch("server.core.guards.health_check.settings") as mock_settings:
        # Both stores sqlite — keeps the probe on the local-file path with no
        # Mongo/Postgres driver reached (this test exercises diagnostics only).
        mock_settings.storage_backend = "sqlite"
        mock_settings.vector_store_backend = "sqlite"
        mock_settings.sqlite_db_path = str(db_path)

        ### When
        actual = storage_health()

    ### Then
    run_state = actual["stores"]["run_state"]
    assert run_state["provider"] == "sqlite"
    assert run_state["ok"] is True
    assert run_state["mode"] == "sqlite-local"
    diagnostics = run_state["diagnostics"]
    assert diagnostics["path"] == str(db_path.resolve())
    assert diagnostics["quick_check"] == "ok"
    assert diagnostics["exists"] is True


def test_given_boot_primed_when_storage_health_then_quick_check_not_rerun(
    tmp_path: Path,
) -> None:
    """
    Scenario: /healthz does not execute quick_check per call (B1).
    Slice: 65B

    Given boot priming has already run the quick_check once and cached it,
    When storage_health runs with _run_quick_check patched,
    Then quick_check is never executed again — the probe reports the cached
         value instead of re-scanning the ~600MB DB on the event loop.
    """
    ### Given
    db_path = tmp_path / "run_state.db"
    _make_run_state_db(db_path)
    prime_boot_diagnostics(str(db_path))

    with patch("server.core.guards.health_check.settings") as mock_settings:
        mock_settings.storage_backend = "sqlite"
        mock_settings.vector_store_backend = "sqlite"
        mock_settings.sqlite_db_path = str(db_path)

        ### When
        with patch.object(sqlite_diagnostics, "_run_quick_check") as mock_quick_check:
            actual = storage_health()

    ### Then
    assert mock_quick_check.call_count == 0
    assert actual["stores"]["run_state"]["diagnostics"]["quick_check"] == "ok"
