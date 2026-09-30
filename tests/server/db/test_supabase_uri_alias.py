"""
Author: Cursor agent
Created: 2026-07-26
Scope: POSTGRES_CLOUD_URL / POSTGRES_LOCAL_URL cloud-or-local resolution (Slice 37 follow-up).
"""

from __future__ import annotations

import pytest

from server.settings import Settings


def test_given_postgres_cloud_url_only_when_settings_load_then_database_url_filled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Scenario: POSTGRES_CLOUD_URL alone populates database_url.
    Slice: slice-37-postgres-local-cloud-parity

    Given POSTGRES_LOCAL_URL is unset and POSTGRES_CLOUD_URL is set
    When Settings is constructed
    Then database_url equals the cloud Postgres URI.
    """
    ### Given
    monkeypatch.delenv("POSTGRES_CLOUD_URL", raising=False)
    monkeypatch.delenv("POSTGRES_LOCAL_URL", raising=False)
    monkeypatch.setenv(
        "POSTGRES_CLOUD_URL",
        "postgresql://postgres:secret@db.example.supabase.co:5432/postgres",
    )

    ### When
    loaded = Settings(_env_file=None)

    ### Then
    assert loaded.database_url == (
        "postgresql://postgres:secret@db.example.supabase.co:5432/postgres"
    )


def test_given_both_cloud_and_local_when_settings_load_then_cloud_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Scenario: POSTGRES_CLOUD_URL takes precedence over POSTGRES_LOCAL_URL.
    Slice: slice-37-postgres-local-cloud-parity

    Given both POSTGRES_CLOUD_URL and POSTGRES_LOCAL_URL are set
    When Settings is constructed
    Then database_url keeps the POSTGRES_CLOUD_URL value.
    """
    ### Given
    monkeypatch.setenv(
        "POSTGRES_CLOUD_URL",
        "postgresql://postgres:secret@db.example.supabase.co:5432/postgres",
    )
    monkeypatch.setenv(
        "POSTGRES_LOCAL_URL", "postgresql://rag:rag@localhost:5433/rag_params_finder"
    )

    ### When
    loaded = Settings(_env_file=None)

    ### Then
    assert loaded.database_url == (
        "postgresql://postgres:secret@db.example.supabase.co:5432/postgres"
    )


def test_given_postgres_without_uri_when_ensure_ready_then_mentions_cloud_and_local_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Scenario: Missing URI error names both POSTGRES_CLOUD_URL and POSTGRES_LOCAL_URL.
    Slice: slice-37-postgres-local-cloud-parity

    Given STORAGE_BACKEND=postgres with no connection URI
    When ensure_storage_ready runs
    Then the error mentions POSTGRES_CLOUD_URL or POSTGRES_LOCAL_URL.
    """
    ### Given
    monkeypatch.setenv("STORAGE_BACKEND", "postgres")
    monkeypatch.delenv("POSTGRES_CLOUD_URL", raising=False)
    monkeypatch.delenv("POSTGRES_LOCAL_URL", raising=False)
    loaded = Settings(_env_file=None)

    ### When / Then
    with pytest.raises(ValueError, match="POSTGRES_CLOUD_URL|POSTGRES_LOCAL_URL"):
        loaded.ensure_storage_ready()


def test_given_postgres_placeholder_uri_when_ensure_ready_then_rejects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Scenario: Example .env POSTGRES_CLOUD_URL placeholder fails before opaque connect.
    Slice: slice-38-cutover-adr-004

    Given STORAGE_BACKEND=postgres and a <project-ref> placeholder URI
    When ensure_storage_ready runs
    Then ValueError names the placeholder and remediation.
    """
    ### Given
    placeholder = (
        "postgresql://postgres.<project-ref>:<password>"
        "@aws-0-<region>.pooler.supabase.com:5432/postgres"
    )
    monkeypatch.setenv("STORAGE_BACKEND", "postgres")
    monkeypatch.setenv("POSTGRES_CLOUD_URL", placeholder)
    monkeypatch.delenv("POSTGRES_LOCAL_URL", raising=False)
    loaded = Settings(_env_file=None)

    ### When / Then
    with pytest.raises(ValueError, match="placeholder|project-ref"):
        loaded.ensure_storage_ready()
