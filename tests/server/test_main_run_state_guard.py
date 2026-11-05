"""
Tests for server.main.enforce_run_state_db_present — fail-closed boot guard.

Author: Mani Sarkar
Created: 2026-11-05
Scope: Slice 65B — RUN_STATE_DB_MUST_EXIST makes the server refuse to boot (and
       so never create a second DB) when the SQLite run-state file is missing.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from server.main import enforce_run_state_db_present


def test_given_flag_set_and_file_missing_when_enforced_then_system_exit(
    tmp_path: Path,
) -> None:
    """
    Scenario: Armed guard refuses to create a second DB.
    Slice: 65B

    Given STORAGE_BACKEND=sqlite, RUN_STATE_DB_MUST_EXIST on, and no DB file,
    When enforce_run_state_db_present runs,
    Then it raises SystemExit and the file is still not created.
    """
    ### Given
    missing = tmp_path / "run_state.db"
    with patch("server.main.settings") as mock_settings:
        mock_settings.storage_backend = "sqlite"
        mock_settings.run_state_db_must_exist = True
        mock_settings.sqlite_db_path = str(missing)

        ### When / Then
        with pytest.raises(SystemExit):
            enforce_run_state_db_present()

    assert not missing.exists()


def test_given_flag_set_and_file_present_when_enforced_then_ok(tmp_path: Path) -> None:
    """
    Scenario: Armed guard passes when the canonical file already exists.
    Slice: 65B

    Given the run-state DB file exists and RUN_STATE_DB_MUST_EXIST is on,
    When enforce_run_state_db_present runs,
    Then it returns without raising.
    """
    ### Given
    existing = tmp_path / "run_state.db"
    existing.touch()
    with patch("server.main.settings") as mock_settings:
        mock_settings.storage_backend = "sqlite"
        mock_settings.run_state_db_must_exist = True
        mock_settings.sqlite_db_path = str(existing)

        ### When / Then (no raise)
        enforce_run_state_db_present()


def test_given_flag_off_and_file_missing_when_enforced_then_ok(tmp_path: Path) -> None:
    """
    Scenario: Default (opt-out) boot still creates the DB on first run.
    Slice: 65B

    Given RUN_STATE_DB_MUST_EXIST is off and no DB file,
    When enforce_run_state_db_present runs,
    Then it returns without raising (first boot may create the file).
    """
    ### Given
    with patch("server.main.settings") as mock_settings:
        mock_settings.storage_backend = "sqlite"
        mock_settings.run_state_db_must_exist = False
        mock_settings.sqlite_db_path = str(tmp_path / "run_state.db")

        ### When / Then (no raise)
        enforce_run_state_db_present()


def test_given_non_sqlite_backend_when_enforced_then_ok(tmp_path: Path) -> None:
    """
    Scenario: The guard only governs the SQLite run-state file.
    Slice: 65B

    Given STORAGE_BACKEND=mongodb (guard armed, no sqlite file),
    When enforce_run_state_db_present runs,
    Then it returns without raising.
    """
    ### Given
    with patch("server.main.settings") as mock_settings:
        mock_settings.storage_backend = "mongodb"
        mock_settings.run_state_db_must_exist = True
        mock_settings.sqlite_db_path = str(tmp_path / "run_state.db")

        ### When / Then (no raise)
        enforce_run_state_db_present()
