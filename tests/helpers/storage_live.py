"""Shared helpers for live Mongo / Postgres integration and contract tests."""

from __future__ import annotations

import os

import pytest

DEFAULT_POSTGRES_URL = "postgresql://rag:rag@localhost:5433/rag_params_finder"
DEFAULT_MONGODB_URI = "mongodb://localhost:27017/rag_params_finder?directConnection=true"

TEST_DATABASE_URL = os.environ.get("RAG_TEST_DATABASE_URL", DEFAULT_POSTGRES_URL)
TEST_MONGODB_URI = os.environ.get("RAG_TEST_MONGODB_URI", DEFAULT_MONGODB_URI)

CONTRACT_EXP_ID = "exp-contract-storage"
CONTRACT_RUN_ID = "run-contract-storage"


def postgres_reachable(url: str = TEST_DATABASE_URL) -> bool:
    """True when a TCP + auth handshake to Postgres succeeds."""
    try:
        import psycopg

        with psycopg.connect(url, connect_timeout=3):
            return True
    except Exception:
        return False


def mongo_reachable(uri: str = TEST_MONGODB_URI) -> bool:
    """True when a MongoDB ping succeeds."""
    try:
        from pymongo import MongoClient

        from server.db.mongodb_uri import mongo_client_kwargs

        client = MongoClient(uri, serverSelectionTimeoutMS=3000, **mongo_client_kwargs(uri))
        try:
            client.admin.command("ping")
            return True
        finally:
            client.close()
    except Exception:
        return False


def postgres_skip_reason(url: str = TEST_DATABASE_URL) -> str | None:
    """Why Postgres live tests cannot run, or None when they can.

    CI sets RAG_REQUIRE_POSTGRES=1 because it provisions a service container: a
    suite that silently skips there would report green forever. Locally the
    database is optional, so an unreachable one skips.
    """
    if postgres_reachable(url):
        return None
    if os.environ.get("RAG_REQUIRE_POSTGRES") == "1":
        pytest.fail(
            f"RAG_REQUIRE_POSTGRES=1 but no Postgres at {url}. "
            "The CI service container is missing or unhealthy.",
            pytrace=False,
        )
    return f"No Postgres at {url} — run ./start-services.sh --postgres"


def mongo_skip_reason(uri: str = TEST_MONGODB_URI) -> str | None:
    """Why Mongo live tests cannot run, or None when they can.

    CI sets RAG_REQUIRE_MONGO=1 with an Atlas Local service container.
    """
    if mongo_reachable(uri):
        return None
    if os.environ.get("RAG_REQUIRE_MONGO") == "1":
        pytest.fail(
            f"RAG_REQUIRE_MONGO=1 but no MongoDB at {uri}. "
            "The CI service container is missing or unhealthy.",
            pytrace=False,
        )
    return f"No MongoDB at {uri} — run ./start-services.sh --local"


def reset_mongo_client() -> None:
    """Drop the cached MongoClient so the next call picks up settings.mongodb_uri."""
    import server.db.atlas as atlas

    if atlas._client is not None:
        atlas._client.close()
    atlas._client = None
    atlas._db = None
