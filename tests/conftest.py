"""Shared pytest fixtures for live storage-backend integration and contract tests.

Author: Mani Sarkar
Created: 2026-07-26
Scope: Parametrized StorageBackend fixtures for Mongo (Atlas Local) and Postgres
       (pgvector) — skips locally, hard-fails in CI. One Postgres pool per
       session so live suites do not deadlock on per-test schema bootstrap.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from tests.helpers.storage_live import (
    CONTRACT_EXP_ID,
    TEST_DATABASE_URL,
    TEST_MONGODB_URI,
    mongo_skip_reason,
    postgres_skip_reason,
    reset_mongo_client,
)


@pytest.fixture(scope="session")
def live_postgres_pool() -> Iterator[None]:
    """Bind DATABASE_URL and open one pool for the whole pytest process.

    Live fixtures used to call ``close_pool()`` on every test. Each reopen
    re-ran ``schema.sql`` DDL (AccessExclusiveLock). Interleaved contract +
    dense/sparse/integration suites then deadlocked or saw half-applied
    deletes (FK / UniqueViolation). Bootstrap once; tests only clean rows.
    """
    from server.db import postgres
    from server.settings import settings

    reason = postgres_skip_reason()
    if reason is not None:
        # Dependents still call postgres_skip_reason() and skip/fail themselves.
        yield
        return

    original_url = settings.database_url
    settings.database_url = TEST_DATABASE_URL
    postgres.close_pool()
    postgres.get_pool()
    try:
        yield
    finally:
        postgres.close_pool()
        settings.database_url = original_url


@pytest.fixture
def postgres_storage(live_postgres_pool: None) -> Iterator[object]:
    """Live PostgresStorageBackend bound to RAG_TEST_DATABASE_URL."""
    from server.db.postgres_store import PostgresStorageBackend
    from server.settings import settings

    reason = postgres_skip_reason()
    if reason is not None:
        pytest.skip(reason)

    original_backend = settings.storage_backend
    settings.database_url = TEST_DATABASE_URL
    settings.storage_backend = "postgres"

    backend = PostgresStorageBackend()
    backend.delete_experiment_data(CONTRACT_EXP_ID)
    try:
        yield backend
    finally:
        backend.delete_experiment_data(CONTRACT_EXP_ID)
        settings.storage_backend = original_backend


@pytest.fixture
def mongo_storage() -> Iterator[object]:
    """Live MongoStorageBackend bound to RAG_TEST_MONGODB_URI."""
    from server.db.mongo_store import MongoStorageBackend
    from server.settings import settings

    reason = mongo_skip_reason()
    if reason is not None:
        pytest.skip(reason)

    original_uri = settings.mongodb_uri
    original_backend = settings.storage_backend
    settings.mongodb_uri = TEST_MONGODB_URI
    settings.storage_backend = "mongodb"
    reset_mongo_client()

    backend = MongoStorageBackend()
    backend.delete_experiment_data(CONTRACT_EXP_ID)
    try:
        yield backend
    finally:
        backend.delete_experiment_data(CONTRACT_EXP_ID)
        reset_mongo_client()
        settings.mongodb_uri = original_uri
        settings.storage_backend = original_backend


@pytest.fixture(params=["mongodb", "postgres"], ids=["mongodb", "postgres"])
def storage(request: pytest.FixtureRequest) -> Iterator[object]:
    """Parametrized live StorageBackend for the shared contract suite."""
    fixture_name = "mongo_storage" if request.param == "mongodb" else "postgres_storage"
    yield request.getfixturevalue(fixture_name)
