"""
Unit tests for server.core.guards.health_check.

Author: Mani Sarkar
Created: 2026-05-27
Scope: mongodb_health_status, postgres_health_status, storage_health —
       backend-aware readiness for Docker HEALTHCHECK and /healthz.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import psycopg

from server.core.health_check import (
    mongodb_health_status,
    postgres_health_status,
    storage_health,
)


def test_given_empty_mongodb_uri_when_health_checked_then_return_skipped() -> None:
    """
    Scenario: No Mongo URI means the probe is not applicable.
    Slice: postgres-aware-healthz

    Given MONGODB_URI is empty,
    When mongodb_health_status runs,
    Then it returns skipped.
    """
    ### Given
    with patch("server.core.guards.health_check.settings") as mock_settings:
        mock_settings.mongodb_uri = ""

        ### When
        actual_status = mongodb_health_status()

    ### Then
    assert actual_status == "skipped"


def test_given_placeholder_mongodb_uri_when_health_checked_then_return_error() -> None:
    """
    Scenario: A placeholder Atlas URI is treated as unreachable.
    Slice: postgres-aware-healthz

    Given MONGODB_URI still holds the example placeholder,
    When mongodb_health_status runs,
    Then it returns error.
    """
    ### Given
    with patch("server.core.guards.health_check.settings") as mock_settings:
        mock_settings.mongodb_uri = "your_mongodb_atlas_uri_here"

        ### When
        actual_status = mongodb_health_status()

    ### Then
    assert actual_status == "error"


def test_given_valid_uri_when_ping_succeeds_then_return_ok() -> None:
    """
    Scenario: A successful Atlas ping reports ok.
    Slice: postgres-aware-healthz

    Given a non-placeholder Mongo URI and a successful admin ping,
    When mongodb_health_status runs,
    Then it returns ok.
    """
    ### Given
    mock_client = MagicMock()
    with (
        patch("server.core.guards.health_check.settings") as mock_settings,
        # Patched at its source (pymongo.MongoClient), not at
        # server.core.guards.health_check.MongoClient — the import is now
        # lazy (function-scoped, mirroring postgres_health_status's psycopg
        # import) so the name no longer lives on the module object to patch.
        patch("pymongo.MongoClient", return_value=mock_client) as mock_mongo_client,
    ):
        mock_settings.mongodb_uri = "mongodb+srv://user:pass@cluster.mongodb.net/db"
        mock_settings.health_check_mongodb_timeout_ms = 5000

        ### When
        actual_status = mongodb_health_status()

    ### Then
    mock_mongo_client.assert_called_once()
    mock_client.admin.command.assert_called_once_with("ping")
    assert actual_status == "ok"


def test_given_empty_database_url_when_postgres_health_checked_then_return_skipped() -> None:
    """
    Scenario: Postgres mode without DATABASE_URL cannot claim readiness.
    Slice: postgres-aware-healthz

    Given DATABASE_URL is empty,
    When postgres_health_status runs,
    Then it returns skipped.
    """
    ### Given
    with patch("server.core.guards.health_check.settings") as mock_settings:
        mock_settings.database_url = ""

        ### When
        actual = postgres_health_status()

    ### Then
    assert actual == "skipped"


def test_given_reachable_postgres_when_health_checked_then_return_ok() -> None:
    """
    Scenario: A live SELECT 1 marks Postgres ready.
    Slice: postgres-aware-healthz

    Given DATABASE_URL is set and the connection succeeds,
    When postgres_health_status runs,
    Then it returns ok.
    """
    ### Given
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False
    with (
        patch("server.core.guards.health_check.settings") as mock_settings,
        # psycopg is imported lazily inside postgres_health_status() (GWT-1 —
        # a Mongo-only process must never load the Postgres driver), so there
        # is no module-level "health_check.psycopg" attribute to patch; patch
        # the real psycopg module's connect() instead.
        patch("psycopg.connect", return_value=mock_conn) as connect,
    ):
        mock_settings.database_url = "postgresql://rag:rag@localhost:5433/rag_params_finder"

        ### When
        actual = postgres_health_status()

    ### Then
    connect.assert_called_once()
    mock_conn.execute.assert_called_once_with("SELECT 1")
    assert actual == "ok"


def test_given_unreachable_postgres_when_health_checked_then_return_error() -> None:
    """
    Scenario: A connection failure marks Postgres unhealthy.
    Slice: postgres-aware-healthz

    Given DATABASE_URL is set and connect raises,
    When postgres_health_status runs,
    Then it returns error — Docker must not report healthy.
    """
    ### Given
    with (
        patch("server.core.guards.health_check.settings") as mock_settings,
        # See test_given_reachable_postgres_when_health_checked_then_return_ok
        # — psycopg is imported lazily, so patch the real module directly.
        patch(
            "psycopg.connect",
            side_effect=psycopg.OperationalError("connection refused"),
        ),
    ):
        mock_settings.database_url = "postgresql://rag:rag@localhost:5433/rag_params_finder"

        ### When
        actual = postgres_health_status()

    ### Then
    assert actual == "error"


class TestStorageHealthShould:
    """Scenario: /healthz probes only the configured storage backend."""

    def test_given_postgres_backend_when_storage_health_then_does_not_require_mongo(
        self,
    ) -> None:
        """
        Scenario: given postgres backend when storage health then does not require mongo.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: A Postgres stack is healthy without a Mongo ping.
        Slice: postgres-aware-healthz

        Given STORAGE_BACKEND=postgres and Postgres is reachable,
        When storage_health runs,
        Then ok is true with postgres=ok — Mongo is not consulted.
        """
        ### Given / When
        with (
            patch("server.core.guards.health_check.settings") as mock_settings,
            patch(
                "server.core.guards.health_check.postgres_health_status", return_value="ok"
            ) as postgres_probe,
            patch("server.core.guards.health_check.mongodb_health_status") as mongo_probe,
            patch(
                "server.core.guards.health_check.resolve_storage_mode",
                return_value="postgres-local",
            ),
        ):
            mock_settings.storage_backend = "postgres"
            mock_settings.vector_store_backend = "postgres"
            actual = storage_health()

        ### Then — legacy keys/values unchanged; new keys are additions only.
        assert actual["ok"] is True
        assert actual["storage_backend"] == "postgres"
        assert actual["storage_mode"] == "postgres-local"
        assert actual["postgres"] == "ok"
        assert actual["vector_store_backend"] == "postgres"
        assert actual["run_state_mode"] == "postgres-local"
        assert actual["stores"]["vector"]["ok"] is True
        assert actual["stores"]["run_state"]["ok"] is True
        postgres_probe.assert_called_once()
        mongo_probe.assert_not_called()

    def test_given_postgres_backend_unreachable_when_storage_health_then_not_ok(
        self,
    ) -> None:
        """
        Scenario: given postgres backend unreachable when storage health then not ok.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Unreachable pgvector fails the health gate.
        Slice: postgres-aware-healthz

        Given STORAGE_BACKEND=postgres and Postgres returns error,
        When storage_health runs,
        Then ok is false.
        """
        ### Given / When
        with (
            patch("server.core.guards.health_check.settings") as mock_settings,
            patch("server.core.guards.health_check.postgres_health_status", return_value="error"),
            patch(
                "server.core.guards.health_check.resolve_storage_mode",
                return_value="postgres-local",
            ),
        ):
            mock_settings.storage_backend = "postgres"
            mock_settings.vector_store_backend = "postgres"
            actual = storage_health()

        ### Then
        assert actual["ok"] is False
        assert actual["postgres"] == "error"
        assert "remediation" in actual
        assert "Session-mode" in str(actual["remediation"])
        assert "resume" in str(actual["remediation"]).lower()

    def test_given_mongo_backend_when_storage_health_then_uses_mongodb_probe(
        self,
    ) -> None:
        """
        Scenario: given mongo backend when storage health then uses mongodb probe.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: The default Mongo backend keeps its existing probe.
        Slice: postgres-aware-healthz

        Given STORAGE_BACKEND=mongodb and MongoDB reports ok,
        When storage_health runs,
        Then ok is true with mongodb=ok.
        """
        ### Given / When
        with (
            patch("server.core.guards.health_check.settings") as mock_settings,
            patch("server.core.guards.health_check.mongodb_health_status", return_value="ok"),
            patch("server.core.guards.health_check.postgres_health_status") as postgres_probe,
            patch(
                "server.core.guards.health_check.resolve_storage_mode",
                return_value="mongodb-cloud",
            ),
        ):
            mock_settings.storage_backend = "mongodb"
            mock_settings.vector_store_backend = "mongodb"
            actual = storage_health()

        ### Then — legacy keys/values unchanged; new keys are additions only.
        assert actual["ok"] is True
        assert actual["storage_backend"] == "mongodb"
        assert actual["storage_mode"] == "mongodb-cloud"
        assert actual["mongodb"] == "ok"
        assert actual["vector_store_backend"] == "mongodb"
        assert actual["run_state_mode"] == "mongodb-cloud"
        postgres_probe.assert_not_called()

    def test_given_mongo_skipped_when_storage_health_then_still_ok(self) -> None:
        """
        Scenario: given mongo skipped when storage health then still ok.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Unset MONGODB_URI still allows process liveness on Mongo mode.
        Slice: postgres-aware-healthz

        Given STORAGE_BACKEND=mongodb and mongodb_health_status returns skipped,
        When storage_health runs,
        Then ok remains true (legacy behaviour for host-only boots without URI).
        """
        ### Given / When
        with (
            patch("server.core.guards.health_check.settings") as mock_settings,
            patch("server.core.guards.health_check.mongodb_health_status", return_value="skipped"),
            patch(
                "server.core.guards.health_check.resolve_storage_mode",
                return_value="mongodb-local",
            ),
        ):
            mock_settings.storage_backend = "mongodb"
            mock_settings.vector_store_backend = "mongodb"
            actual = storage_health()

        ### Then
        assert actual["ok"] is True
        assert actual["mongodb"] == "skipped"
        assert actual["storage_mode"] == "mongodb-local"

    def test_given_split_store_with_vector_unreachable_when_storage_health_then_not_ok(
        self,
    ) -> None:
        """
        Scenario: Vector store unreachable (split-store /healthz).

        Given STORAGE_BACKEND=postgres (reachable) and
              VECTOR_STORE_BACKEND=elasticsearch (no reachable cluster in
              this test — the adapter reports not-ok),
        When storage_health() is called,
        Then it reports ok=False with stores.vector.ok=False and a
             remediation string, while stores.run_state.ok stays True and
             today's per-engine key (postgres) still reflects the run-state
             probe.
        """
        ### Given / When
        with (
            patch("server.core.guards.health_check.settings") as mock_settings,
            patch("server.core.guards.health_check.postgres_health_status", return_value="ok"),
            patch(
                "server.core.guards.health_check.resolve_storage_mode",
                return_value="postgres-local",
            ),
            patch(
                "server.db.elasticsearch.elasticsearch_vector_store.settings"
            ) as mock_es_settings,
        ):
            mock_settings.storage_backend = "postgres"
            mock_settings.vector_store_backend = "elasticsearch"
            mock_es_settings.elasticsearch_url = ""
            actual = storage_health()

        ### Then
        assert actual["ok"] is False
        assert actual["storage_backend"] == "postgres"
        assert actual["postgres"] == "ok"
        assert actual["vector_store_backend"] == "elasticsearch"
        assert actual["run_state_mode"] == "postgres-local"
        assert actual["stores"]["vector"]["ok"] is False
        assert actual["stores"]["vector"]["latency_ms"] is None
        assert "remediation" in actual["stores"]["vector"]
        assert actual["stores"]["run_state"]["ok"] is True
        assert actual["stores"]["run_state"]["container"] == "rag-params-finder-postgres-local"
        assert actual["stores"]["run_state"]["image"] == "pgvector/pgvector:0.8.5-pg16"

    def test_given_cloud_mode_when_storage_health_then_probe_omits_container(
        self,
    ) -> None:
        """
        Scenario: Cloud storage health does not claim a local container.

        Given STORAGE_BACKEND=mongodb and storage_mode mongodb-cloud,
        When storage_health runs,
        Then the public probe has no container or image.
        """
        ### Given / When
        with (
            patch("server.core.guards.health_check.settings") as mock_settings,
            patch("server.core.guards.health_check.mongodb_health_status", return_value="ok"),
            patch(
                "server.core.guards.health_check.resolve_storage_mode",
                return_value="mongodb-cloud",
            ),
        ):
            mock_settings.storage_backend = "mongodb"
            mock_settings.vector_store_backend = "mongodb"
            actual = storage_health()

        ### Then
        probe = actual["stores"]["vector"]
        assert "container" not in probe
        assert "image" not in probe


def test_given_unreachable_elasticsearch_when_healthz_called_then_status_is_503() -> None:
    """
    Scenario: ES unreachable at startup degrades clearly.

    Given the vector probe reports not-ok,
    When GET /healthz runs,
    Then the response is 503 and stores.vector.ok is false.
    """
    ### Given
    from server.main import healthz

    body = {
        "ok": False,
        "storage_backend": "mongodb",
        "storage_mode": "elasticsearch-local",
        "vector_store_backend": "elasticsearch",
        "run_state_mode": "mongodb-local",
        "stores": {
            "vector": {
                "provider": "elasticsearch",
                "mode": "elasticsearch-local",
                "ok": False,
                "latency_ms": None,
                "remediation": "Vector store 'elasticsearch' is unreachable.",
            },
            "run_state": {
                "provider": "mongodb",
                "mode": "mongodb-local",
                "ok": True,
                "latency_ms": 1,
            },
        },
    }

    ### When
    with patch("server.main.storage_health", return_value=body):
        response = asyncio.run(healthz())

    ### Then
    assert response.status_code == 503
    payload = response.body
    assert b'"ok":false' in payload or b'"ok": false' in payload
    assert b'"provider":"elasticsearch"' in payload or b'"provider": "elasticsearch"' in payload
