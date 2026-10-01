"""
Regression test: Run-state capability — vector-only adapters must NOT implement StorageBackend.

Author: Mani Sarkar
Created: 2026-10-01
Scope: Ensure Elasticsearch and Redis adapters cannot accidentally be used as StorageBackend
       (run-state CRUD is reserved for Mongo/Postgres only per DECISIONS #240). Verify by
       isinstance() checks on constructed instances with mocked clients, preventing future
       regression where methods might be accidentally added.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from server.db.elasticsearch.elasticsearch_vector_store import ElasticsearchVectorStore
from server.db.ports.storage import StorageBackend
from server.db.redis.redis_store import RedisVectorStore

# ── Helpers ──────────────────────────────────────────────────────────────────


def _fake_elasticsearch_client() -> Any:
    """Build a minimal mock Elasticsearch client for unit tests."""
    fake = MagicMock(name="elasticsearch_client")
    fake.ping.return_value = True
    fake.indices = SimpleNamespace(
        get_mapping=MagicMock(return_value={"index": {"mappings": {}}}),
        create=MagicMock(),
        exists=MagicMock(return_value=True),
    )
    fake.bulk = MagicMock(return_value={"items": []})
    fake.delete_by_query = MagicMock(return_value={"deleted": 0})
    fake.count = MagicMock(return_value={"count": 0})
    fake.search = MagicMock(return_value={"aggregations": {"buckets": {"buckets": []}}})
    return fake


def _fake_redis_client() -> Any:
    """Build a minimal mock Redis client for unit tests."""
    fake = MagicMock(name="redis_client")
    fake.ping.return_value = True
    fake.pipeline.return_value = MagicMock()
    fake.scan.return_value = (0, [])
    fake.ft.return_value = MagicMock(
        info=MagicMock(return_value={"num_docs": 0}),
    )
    return fake


class TestStorageBackendCapabilityConstraintShould:
    """Verify that vector-only adapters do not implement StorageBackend (run-state port)."""

    def test_given_elasticsearch_vector_store_when_isinstance_checked_then_not_storage_backend(
        self,
    ) -> None:
        """
        Scenario: Elasticsearch adapter must not satisfy StorageBackend protocol.
        Slice: Regression test for DECISIONS #240 (run-state CRUD reserved for Mongo/Postgres)

        Given an ElasticsearchVectorStore instance with a mocked client,
        When isinstance(instance, StorageBackend) is checked,
        Then it returns False (Elasticsearch is vector-only, not run-state-capable).
        """
        ### Given
        client = _fake_elasticsearch_client()
        store = ElasticsearchVectorStore(client=client)

        ### When / Then
        assert not isinstance(store, StorageBackend), (
            "ElasticsearchVectorStore must not implement StorageBackend protocol. "
            "Run-state CRUD is reserved for MongoDB and PostgreSQL adapters only."
        )

    def test_given_redis_vector_store_when_isinstance_checked_then_not_storage_backend(
        self,
    ) -> None:
        """
        Scenario: Redis adapter must not satisfy StorageBackend protocol.
        Slice: Regression test for DECISIONS #240 (run-state CRUD reserved for Mongo/Postgres)

        Given a RedisVectorStore instance with a mocked client,
        When isinstance(instance, StorageBackend) is checked,
        Then it returns False (Redis is vector-only, not run-state-capable).
        """
        ### Given
        client = _fake_redis_client()
        store = RedisVectorStore(client=client)

        ### When / Then
        assert not isinstance(store, StorageBackend), (
            "RedisVectorStore must not implement StorageBackend protocol. "
            "Run-state CRUD is reserved for MongoDB and PostgreSQL adapters only."
        )

    def test_given_elasticsearch_vector_store_when_storage_backend_methods_checked_then_missing(
        self,
    ) -> None:
        """
        Scenario: Elasticsearch has no run-state methods (by construction, not by protocol).
        Slice: Regression test — defensive check for accidental method addition

        Given an ElasticsearchVectorStore instance,
        When we check for StorageBackend methods like insert_experiment,
        Then they are not present (construction-based guarantee, not protocol-based).
        """
        ### Given
        client = _fake_elasticsearch_client()
        store = ElasticsearchVectorStore(client=client)

        ### When / Then
        required_methods = [
            "insert_experiment",
            "find_experiment_by_id",
            "find_running_experiments",
            "delete_experiment_data",
        ]
        for method_name in required_methods:
            # Check that these methods are not callable on the store
            # (they exist as stubs in the Protocol but should not be implemented here)
            method = getattr(store, method_name, None)
            assert method is None or not callable(method), (
                f"ElasticsearchVectorStore.{method_name} should not be implemented. "
                "Run-state CRUD is not permitted on vector-only adapters."
            )

    def test_given_redis_vector_store_when_storage_backend_methods_checked_then_missing(
        self,
    ) -> None:
        """
        Scenario: Redis has no run-state methods (by construction, not by protocol).
        Slice: Regression test — defensive check for accidental method addition

        Given a RedisVectorStore instance,
        When we check for StorageBackend methods like insert_experiment,
        Then they are not present (construction-based guarantee, not protocol-based).
        """
        ### Given
        client = _fake_redis_client()
        store = RedisVectorStore(client=client)

        ### When / Then
        required_methods = [
            "insert_experiment",
            "find_experiment_by_id",
            "find_running_experiments",
            "delete_experiment_data",
        ]
        for method_name in required_methods:
            # Check that these methods are not callable on the store
            method = getattr(store, method_name, None)
            assert method is None or not callable(method), (
                f"RedisVectorStore.{method_name} should not be implemented. "
                "Run-state CRUD is not permitted on vector-only adapters."
            )
