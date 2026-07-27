"""
Tests for four-value storage_mode classification.

Author: Mani Sarkar
Created: 2026-07-26
Scope: mongodb-local|mongodb-cloud|postgres-local|postgres-cloud — URI + backend
       classification for /healthz and db-stats (Slice 36 / Slice 27 absorption).
"""

from __future__ import annotations

import pytest

from server.db.mongo.mongodb_uri import (
    STORAGE_MODE_MONGODB_CLOUD,
    STORAGE_MODE_MONGODB_LOCAL,
    mongodb_storage_mode,
)
from server.db.postgres.postgres_uri import (
    STORAGE_MODE_POSTGRES_CLOUD,
    STORAGE_MODE_POSTGRES_LOCAL,
    postgres_storage_mode,
)

_POSTGRES_MODE_CASES = [
    (
        "postgresql://rag:rag@localhost:5433/rag_params_finder",
        STORAGE_MODE_POSTGRES_LOCAL,
    ),
    (
        "postgresql://postgres.abcdefghijklmnop:secret@aws-0-eu-west-1.pooler.supabase.com:6543/postgres",
        STORAGE_MODE_POSTGRES_CLOUD,
    ),
    (
        "postgresql://user:pass@db.abcdefghijklmnop.supabase.co:5432/postgres",
        STORAGE_MODE_POSTGRES_CLOUD,
    ),
]

_MONGODB_MODE_CASES = [
    (
        "mongodb://localhost:27017/rag_params_finder?directConnection=true",
        STORAGE_MODE_MONGODB_LOCAL,
    ),
    (
        "mongodb+srv://user:pass@cluster0.abcde.mongodb.net/rag_params_finder",
        STORAGE_MODE_MONGODB_CLOUD,
    ),
]


@pytest.mark.parametrize(("uri", "expected_mode"), _POSTGRES_MODE_CASES)
def test_given_postgres_uri_when_classified_then_flag_aligned_mode(
    uri: str, expected_mode: str
) -> None:
    """
    Scenario: Postgres URIs map to postgres-local or postgres-cloud.
    Slice: slice-36-postgres-preflight-stats

    Given a local Docker or hosted Supabase DATABASE_URL,
    When postgres_storage_mode classifies it,
    Then the result matches the planned start-services flag compound.
    """
    ### Given / When
    actual_mode = postgres_storage_mode(uri)

    ### Then
    assert actual_mode == expected_mode, (
        f"Expected {expected_mode!r} for {uri!r}, got {actual_mode!r}"
    )
    assert actual_mode not in {"supabase", "local-postgres", "mongo", "mongodb"}


@pytest.mark.parametrize(("uri", "expected_mode"), _MONGODB_MODE_CASES)
def test_given_mongodb_uri_when_classified_then_flag_aligned_mode(
    uri: str, expected_mode: str
) -> None:
    """
    Scenario: Mongo URIs map to mongodb-local or mongodb-cloud.
    Slice: slice-36-postgres-preflight-stats

    Given an Atlas Local or Atlas cloud MONGODB_URI,
    When mongodb_storage_mode classifies it,
    Then the result matches the planned start-services flag compound.
    """
    ### Given / When
    actual_mode = mongodb_storage_mode(uri)

    ### Then
    assert actual_mode == expected_mode, (
        f"Expected {expected_mode!r} for {uri!r}, got {actual_mode!r}"
    )
    assert actual_mode not in {"supabase", "local-postgres", "mongo", "mongodb"}
