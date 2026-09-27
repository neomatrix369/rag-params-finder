"""
Tests for MongoVectorStore and PostgresVectorStore composite adapters.

Author: Mani Sarkar
Created: 2026-09-27
Scope: structural VectorStore Protocol conformance + delegation-only behaviour
       for the two Stream 3 composite adapters. Underlying stores/retrievers
       are mocked — no live DB is hit.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from server.db.mongo.mongo_vector_store import MongoVectorStore
from server.db.ports.vector_store import VectorCapabilities, VectorStore
from server.db.postgres.postgres_vector_store import PostgresVectorStore


class TestMongoVectorStoreShould:
    """Scenario: MongoVectorStore satisfies VectorStore and delegates to Mongo primitives."""

    def test_given_instance_when_isinstance_checked_then_satisfies_vector_store_protocol(
        self,
    ) -> None:
        """
        Scenario: structural conformance to the runtime_checkable VectorStore Protocol.

        Given a MongoVectorStore built from mock storage/retriever,
        When isinstance() is checked against VectorStore,
        Then it structurally satisfies the port.
        """
        ### Given
        store = MongoVectorStore(storage=MagicMock(), retriever=MagicMock())

        ### When / Then
        assert isinstance(store, VectorStore)

    def test_given_mock_storage_when_insert_chunks_called_then_delegates_with_same_args(
        self,
    ) -> None:
        """
        Scenario: chunk write delegates to MongoStorageBackend.insert_chunks.

        Given a MongoVectorStore wrapping a mock MongoStorageBackend,
        When insert_chunks(docs) is called,
        Then the mock storage's insert_chunks is called once with the same docs.
        """
        ### Given
        mock_storage = MagicMock()
        store = MongoVectorStore(storage=mock_storage, retriever=MagicMock())
        docs = [{"chunk_id": "c1"}]

        ### When
        store.insert_chunks(docs)

        ### Then
        mock_storage.insert_chunks.assert_called_once_with(docs)

    def test_given_mock_storage_when_delete_chunks_called_then_delegates_and_returns_count(
        self,
    ) -> None:
        """
        Scenario: chunk delete delegates to MongoStorageBackend.delete_chunks_for_experiment.

        Given a MongoVectorStore wrapping a mock MongoStorageBackend,
        When delete_chunks_for_experiment(experiment_id) is called,
        Then the mock is called with the experiment_id and its return value passes through.
        """
        ### Given
        mock_storage = MagicMock()
        mock_storage.delete_chunks_for_experiment.return_value = 7
        store = MongoVectorStore(storage=mock_storage, retriever=MagicMock())

        ### When
        result = store.delete_chunks_for_experiment("exp-1")

        ### Then
        mock_storage.delete_chunks_for_experiment.assert_called_once_with("exp-1")
        assert result == 7

    def test_given_mock_storage_when_stats_methods_called_then_delegate_to_storage(
        self,
    ) -> None:
        """
        Scenario: stats methods delegate to MongoStorageBackend.

        Given a MongoVectorStore wrapping a mock MongoStorageBackend,
        When get_experiment_db_stats and get_vector_db_stats_grouped are called,
        Then both delegate to the mock storage and return its values.
        """
        ### Given
        mock_storage = MagicMock()
        mock_storage.get_experiment_db_stats.return_value = {"stat": 1}
        mock_storage.get_vector_db_stats_grouped.return_value = {"grouped": 2}
        store = MongoVectorStore(storage=mock_storage, retriever=MagicMock())

        ### When
        experiment_stats = store.get_experiment_db_stats("exp-1")
        grouped_stats = store.get_vector_db_stats_grouped()

        ### Then
        mock_storage.get_experiment_db_stats.assert_called_once_with("exp-1")
        mock_storage.get_vector_db_stats_grouped.assert_called_once_with()
        assert experiment_stats == {"stat": 1}
        assert grouped_stats == {"grouped": 2}

    def test_given_mock_retriever_when_retriever_called_then_returns_the_same_instance(
        self,
    ) -> None:
        """
        Scenario: retriever() returns the composed MongoRetrieverBackend, unchanged.

        Given a MongoVectorStore wrapping a mock retriever,
        When retriever() is called,
        Then it returns that exact mock (search stays a single contract).
        """
        ### Given
        mock_retriever = MagicMock()
        store = MongoVectorStore(storage=MagicMock(), retriever=mock_retriever)

        ### When
        result = store.retriever()

        ### Then
        assert result is mock_retriever

    def test_given_store_when_ensure_indexes_called_then_delegates_to_mongo_indexes_module(
        self,
    ) -> None:
        """
        Scenario: ensure_indexes() delegates to server.db.mongo.indexes.ensure_indexes.

        Given a MongoVectorStore,
        When ensure_indexes() is called,
        Then the module-level Mongo index bootstrap function is invoked once.
        """
        ### Given
        store = MongoVectorStore(storage=MagicMock(), retriever=MagicMock())

        ### When / Then
        with patch("server.db.mongo.mongo_vector_store._mongo_ensure_indexes") as mock_ensure:
            store.ensure_indexes()
            mock_ensure.assert_called_once_with()

    def test_given_store_when_health_check_called_then_delegates_to_mongodb_health_status(
        self,
    ) -> None:
        """
        Scenario: health_check() delegates to the existing Mongo health-probe helper.

        Given a MongoVectorStore,
        When health_check() is called and the probe returns "ok",
        Then health_check() returns True.
        """
        ### Given
        store = MongoVectorStore(storage=MagicMock(), retriever=MagicMock())

        ### When
        with patch("server.db.mongo.mongo_vector_store.mongodb_health_status", return_value="ok"):
            result = store.health_check()

        ### Then
        assert result is True

    def test_given_store_when_capabilities_called_then_declares_mongo_capabilities(
        self,
    ) -> None:
        """
        Scenario: capabilities() returns Mongo's declared VectorCapabilities.

        Given a MongoVectorStore,
        When capabilities() is called,
        Then it returns a VectorCapabilities that can host run state and supports
        the Voyage/local/SIE embedding dims (384, 1024, 30522).
        """
        ### Given
        store = MongoVectorStore(storage=MagicMock(), retriever=MagicMock())

        ### When
        capabilities = store.capabilities()

        ### Then
        assert isinstance(capabilities, VectorCapabilities)
        assert capabilities.can_host_run_state is True
        assert capabilities.supported_embedding_dims == frozenset({384, 1024, 30522})


class TestPostgresVectorStoreShould:
    """Scenario: PostgresVectorStore satisfies VectorStore and delegates to Postgres primitives."""

    def test_given_instance_when_isinstance_checked_then_satisfies_vector_store_protocol(
        self,
    ) -> None:
        """
        Scenario: structural conformance to the runtime_checkable VectorStore Protocol.

        Given a PostgresVectorStore built from mock storage/retriever,
        When isinstance() is checked against VectorStore,
        Then it structurally satisfies the port.
        """
        ### Given
        store = PostgresVectorStore(storage=MagicMock(), retriever=MagicMock())

        ### When / Then
        assert isinstance(store, VectorStore)

    def test_given_mock_storage_when_insert_chunks_called_then_delegates_with_same_args(
        self,
    ) -> None:
        """
        Scenario: chunk write delegates to PostgresStorageBackend.insert_chunks.

        Given a PostgresVectorStore wrapping a mock PostgresStorageBackend,
        When insert_chunks(docs) is called,
        Then the mock storage's insert_chunks is called once with the same docs.
        """
        ### Given
        mock_storage = MagicMock()
        store = PostgresVectorStore(storage=mock_storage, retriever=MagicMock())
        docs = [{"chunk_id": "c1"}]

        ### When
        store.insert_chunks(docs)

        ### Then
        mock_storage.insert_chunks.assert_called_once_with(docs)

    def test_given_mock_storage_when_delete_chunks_called_then_delegates_and_returns_count(
        self,
    ) -> None:
        """
        Scenario: chunk delete delegates to PostgresStorageBackend.delete_chunks_for_experiment.

        Given a PostgresVectorStore wrapping a mock PostgresStorageBackend,
        When delete_chunks_for_experiment(experiment_id) is called,
        Then the mock is called with the experiment_id and its return value passes through.
        """
        ### Given
        mock_storage = MagicMock()
        mock_storage.delete_chunks_for_experiment.return_value = 3
        store = PostgresVectorStore(storage=mock_storage, retriever=MagicMock())

        ### When
        result = store.delete_chunks_for_experiment("exp-2")

        ### Then
        mock_storage.delete_chunks_for_experiment.assert_called_once_with("exp-2")
        assert result == 3

    def test_given_mock_storage_when_stats_methods_called_then_delegate_to_storage(
        self,
    ) -> None:
        """
        Scenario: stats methods delegate to PostgresStorageBackend.

        Given a PostgresVectorStore wrapping a mock PostgresStorageBackend,
        When get_experiment_db_stats and get_vector_db_stats_grouped are called,
        Then both delegate to the mock storage and return its values.
        """
        ### Given
        mock_storage = MagicMock()
        mock_storage.get_experiment_db_stats.return_value = {"stat": 1}
        mock_storage.get_vector_db_stats_grouped.return_value = {"grouped": 2}
        store = PostgresVectorStore(storage=mock_storage, retriever=MagicMock())

        ### When
        experiment_stats = store.get_experiment_db_stats("exp-2")
        grouped_stats = store.get_vector_db_stats_grouped()

        ### Then
        mock_storage.get_experiment_db_stats.assert_called_once_with("exp-2")
        mock_storage.get_vector_db_stats_grouped.assert_called_once_with()
        assert experiment_stats == {"stat": 1}
        assert grouped_stats == {"grouped": 2}

    def test_given_mock_retriever_when_retriever_called_then_returns_the_same_instance(
        self,
    ) -> None:
        """
        Scenario: retriever() returns the composed PostgresRetrieverBackend, unchanged.

        Given a PostgresVectorStore wrapping a mock retriever,
        When retriever() is called,
        Then it returns that exact mock (search stays a single contract).
        """
        ### Given
        mock_retriever = MagicMock()
        store = PostgresVectorStore(storage=MagicMock(), retriever=mock_retriever)

        ### When
        result = store.retriever()

        ### Then
        assert result is mock_retriever

    def test_given_store_when_ensure_indexes_called_then_delegates_to_bootstrap_schema(
        self,
    ) -> None:
        """
        Scenario: ensure_indexes() delegates to server.db.postgres.postgres.bootstrap_schema.

        Given a PostgresVectorStore and a configured DATABASE_URL,
        When ensure_indexes() is called,
        Then bootstrap_schema is invoked once with the configured URI.
        """
        ### Given
        store = PostgresVectorStore(storage=MagicMock(), retriever=MagicMock())

        ### When / Then
        with (
            patch("server.db.postgres.postgres_vector_store.settings") as mock_settings,
            patch("server.db.postgres.postgres_vector_store.bootstrap_schema") as mock_bootstrap,
        ):
            mock_settings.database_url = "postgresql://example"
            store.ensure_indexes()
            mock_bootstrap.assert_called_once_with("postgresql://example")

    def test_given_store_when_health_check_called_then_delegates_to_postgres_health_status(
        self,
    ) -> None:
        """
        Scenario: health_check() delegates to the existing Postgres health-probe helper.

        Given a PostgresVectorStore,
        When health_check() is called and the probe returns "error",
        Then health_check() returns False.
        """
        ### Given
        store = PostgresVectorStore(storage=MagicMock(), retriever=MagicMock())

        ### When
        with patch(
            "server.db.postgres.postgres_vector_store.postgres_health_status",
            return_value="error",
        ):
            result = store.health_check()

        ### Then
        assert result is False

    def test_given_store_when_capabilities_called_then_declares_postgres_capabilities(
        self,
    ) -> None:
        """
        Scenario: capabilities() returns Postgres's declared VectorCapabilities.

        Given a PostgresVectorStore,
        When capabilities() is called,
        Then it returns a VectorCapabilities that can host run state and supports
        the two pgvector embedding column widths (384, 1024).
        """
        ### Given
        store = PostgresVectorStore(storage=MagicMock(), retriever=MagicMock())

        ### When
        capabilities = store.capabilities()

        ### Then
        assert isinstance(capabilities, VectorCapabilities)
        assert capabilities.can_host_run_state is True
        assert capabilities.supported_embedding_dims == frozenset({384, 1024})
