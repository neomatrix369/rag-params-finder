"""
Tests for server.main._run_shutdown — WAL checkpoint survives teardown errors.

Author: Mani Sarkar
Created: 2026-11-05
Scope: Slice 65B (S1) — the lifespan shutdown must still run
       wal_checkpoint(TRUNCATE) for a SQLite run-state backend even when
       stop_watcher/shutdown_executors raise, and must skip it for non-SQLite.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from server.main import _run_shutdown


def test_given_sqlite_backend_when_shutdown_then_checkpoint_runs(tmp_path: Path) -> None:
    """
    Scenario: A clean SQLite shutdown folds the WAL once.
    Slice: 65B

    Given STORAGE_BACKEND=sqlite and healthy teardown,
    When _run_shutdown runs,
    Then checkpoint_truncate is called once with the configured DB path.
    """
    ### Given
    db_path = tmp_path / "run_state.db"
    with (
        patch("server.main.settings") as mock_settings,
        patch("server.core.pipeline.doubleword_watcher.stop_watcher"),
        patch("server.main.shutdown_executors"),
        patch("server.db.sqlite.sqlite_diagnostics.checkpoint_truncate") as mock_ckpt,
    ):
        mock_settings.storage_backend = "sqlite"
        mock_settings.sqlite_db_path = str(db_path)

        ### When
        _run_shutdown()

    ### Then
    mock_ckpt.assert_called_once_with(str(db_path))


def test_given_executor_teardown_raises_when_shutdown_then_checkpoint_still_runs(
    tmp_path: Path,
) -> None:
    """
    Scenario: A teardown failure must not skip the WAL checkpoint.
    Slice: 65B

    Given shutdown_executors raises during a SQLite shutdown,
    When _run_shutdown runs,
    Then checkpoint_truncate still runs (try/finally) before the error propagates.
    """
    ### Given
    db_path = tmp_path / "run_state.db"
    with (
        patch("server.main.settings") as mock_settings,
        patch("server.core.pipeline.doubleword_watcher.stop_watcher"),
        patch("server.main.shutdown_executors", side_effect=RuntimeError("boom")),
        patch("server.db.sqlite.sqlite_diagnostics.checkpoint_truncate") as mock_ckpt,
    ):
        mock_settings.storage_backend = "sqlite"
        mock_settings.sqlite_db_path = str(db_path)

        ### When / Then
        with pytest.raises(RuntimeError, match="boom"):
            _run_shutdown()

    assert mock_ckpt.call_count == 1


def test_given_non_sqlite_backend_when_shutdown_then_no_checkpoint(tmp_path: Path) -> None:
    """
    Scenario: The checkpoint only governs the SQLite run-state file.
    Slice: 65B

    Given STORAGE_BACKEND=mongodb,
    When _run_shutdown runs,
    Then checkpoint_truncate is never called.
    """
    ### Given
    with (
        patch("server.main.settings") as mock_settings,
        patch("server.core.pipeline.doubleword_watcher.stop_watcher"),
        patch("server.main.shutdown_executors"),
        patch("server.db.sqlite.sqlite_diagnostics.checkpoint_truncate") as mock_ckpt,
    ):
        mock_settings.storage_backend = "mongodb"
        mock_settings.sqlite_db_path = str(tmp_path / "run_state.db")

        ### When
        _run_shutdown()

    ### Then
    mock_ckpt.assert_not_called()
