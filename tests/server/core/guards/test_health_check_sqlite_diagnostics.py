"""
Tests for SQLite run-state diagnostics surfaced in /healthz (storage_health).

Author: Mani Sarkar
Created: 2026-11-05
Scope: Slice 65B — storage_health() exposes stores.run_state.diagnostics with the
       resolved path and quick_check while keeping every pre-65B key intact.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

from server.core.health_check import storage_health


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

    Given STORAGE_BACKEND=sqlite with a real run-state DB on disk,
    When storage_health runs,
    Then stores.run_state carries a diagnostics block with the resolved path and
         quick_check=ok, and the pre-65B keys (ok, provider, mode) still hold.
    """
    ### Given
    db_path = tmp_path / "run_state.db"
    _make_run_state_db(db_path)

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
