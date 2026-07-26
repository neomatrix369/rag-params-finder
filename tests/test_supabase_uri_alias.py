"""
Author: Cursor agent
Created: 2026-07-26
Scope: SUPABASE_URI → DATABASE_URL settings alias (Slice 37 follow-up).
"""

from __future__ import annotations

import pytest

from server.settings import Settings


def test_given_supabase_uri_only_when_settings_load_then_database_url_filled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Scenario: SUPABASE_URI alone populates database_url.
    Slice: slice-37-postgres-local-cloud-parity

    Given DATABASE_URL is unset and SUPABASE_URI is set
    When Settings is constructed
    Then database_url equals the Supabase URI.
    """
    ### Given
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "SUPABASE_URI",
        "postgresql://postgres:secret@db.example.supabase.co:5432/postgres",
    )

    ### When
    loaded = Settings(_env_file=None)

    ### Then
    assert loaded.database_url == (
        "postgresql://postgres:secret@db.example.supabase.co:5432/postgres"
    )


def test_given_both_uris_when_settings_load_then_database_url_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Scenario: DATABASE_URL takes precedence over SUPABASE_URI.
    Slice: slice-37-postgres-local-cloud-parity

    Given both DATABASE_URL and SUPABASE_URI are set
    When Settings is constructed
    Then database_url keeps the canonical DATABASE_URL value.
    """
    ### Given
    monkeypatch.setenv("DATABASE_URL", "postgresql://rag:rag@localhost:5433/rag_params_finder")
    monkeypatch.setenv(
        "SUPABASE_URI",
        "postgresql://postgres:secret@db.example.supabase.co:5432/postgres",
    )

    ### When
    loaded = Settings(_env_file=None)

    ### Then
    assert loaded.database_url == "postgresql://rag:rag@localhost:5433/rag_params_finder"


def test_given_postgres_without_uri_when_ensure_ready_then_mentions_supabase_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Scenario: Missing URI error names both DATABASE_URL and SUPABASE_URI.
    Slice: slice-37-postgres-local-cloud-parity

    Given STORAGE_BACKEND=postgres with no connection URI
    When ensure_storage_ready runs
    Then the error mentions SUPABASE_URI.
    """
    ### Given
    monkeypatch.setenv("STORAGE_BACKEND", "postgres")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_URI", raising=False)
    loaded = Settings(_env_file=None)

    ### When / Then
    with pytest.raises(ValueError, match="SUPABASE_URI"):
        loaded.ensure_storage_ready()


def test_given_postgres_placeholder_uri_when_ensure_ready_then_rejects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Scenario: Example .env SUPABASE_URI placeholder fails before opaque connect.
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
    monkeypatch.setenv("SUPABASE_URI", placeholder)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    loaded = Settings(_env_file=None)

    ### When / Then
    with pytest.raises(ValueError, match="placeholder|project-ref"):
        loaded.ensure_storage_ready()
