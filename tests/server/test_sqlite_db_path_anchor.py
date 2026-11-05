"""
Tests for the anchored SQLITE_DB_PATH default and the RUN_STATE_DB_MUST_EXIST flag.

Author: Mani Sarkar
Created: 2026-11-05
Scope: Slice 65B duplicate-prevention guard — the SQLite run-state default
       resolves to the repo root (not the cwd), and the opt-in
       run_state_db_must_exist flag defaults off.
"""

from __future__ import annotations

from pathlib import Path

from server.settings import _DEFAULT_SQLITE_DB_PATH, Settings


def test_given_default_setting_when_resolved_then_anchored_to_repo_root() -> None:
    """
    Scenario: The default run-state path does not depend on the working directory.
    Slice: 65B

    Given the Settings class default for sqlite_db_path,
    When it is inspected,
    Then it is the absolute repo-root data/run_state.db, matching the image
         path /app/data/run_state.db (server/ is parents[0], root is parents[1]).
    """
    ### Given
    default = Settings.model_fields["sqlite_db_path"].default
    expected = Path(__file__).resolve().parents[2] / "data" / "run_state.db"

    ### When
    resolved = Path(default)

    ### Then
    assert default == _DEFAULT_SQLITE_DB_PATH
    assert resolved.is_absolute()
    assert resolved == expected
    assert resolved.name == "run_state.db"


def test_given_no_env_when_settings_built_then_run_state_db_must_exist_off() -> None:
    """
    Scenario: The fail-closed guard is opt-in and off by default.
    Slice: 65B

    Given a Settings built without the env override,
    When run_state_db_must_exist is read,
    Then it is False so normal first-boot still creates the DB.
    """
    ### Given / When
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    ### Then
    assert settings.run_state_db_must_exist is False


def test_given_env_flag_when_settings_built_then_run_state_db_must_exist_on(
    monkeypatch,
) -> None:
    """
    Scenario: start-services.sh can arm the guard via the env var.
    Slice: 65B

    Given RUN_STATE_DB_MUST_EXIST=1 in the environment,
    When Settings is built,
    Then run_state_db_must_exist is True.
    """
    ### Given
    monkeypatch.setenv("RUN_STATE_DB_MUST_EXIST", "1")

    ### When
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    ### Then
    assert settings.run_state_db_must_exist is True
