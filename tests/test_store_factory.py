"""
Tests for server.db.store_factory.

Author: Mani Sarkar
Created: 2026-07-25
Scope: storage_backend routing — mongo default, unknown rejection, postgres NotImplemented
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from server.db.postgres_store import get_postgres_retriever
from server.db.store_factory import get_retriever_backend, get_storage_backend
from server.models.enums import RetrievalMethod


class TestStoreFactoryShould:
    """Scenario: factory selects StorageBackend / RetrieverBackend from settings."""

    def test_given_mongo_default_when_get_storage_backend_then_returns_mongo_adapter(
        self,
    ) -> None:
        """
        Scenario: Default backend remains Mongo.
        Slice: slice-32-storage-backend-protocol

        Given STORAGE_BACKEND is unset or "mongo",
        When get_storage_backend() is called,
        Then the Mongo StorageBackend adapter is returned.
        """
        ### Given
        mock_storage = MagicMock(name="MongoStorageBackend")

        ### When
        with (
            patch("server.settings.settings.storage_backend", "mongo"),
            patch(
                "server.db.mongo_store.get_mongo_storage",
                return_value=mock_storage,
            ),
        ):
            actual = get_storage_backend()

        ### Then
        assert actual is mock_storage, f"Expected mongo storage adapter, got {actual!r}"

    def test_given_storage_backend_mongo_when_get_retriever_backend_then_returns_mongo_adapter(
        self,
    ) -> None:
        """
        Scenario: Default retriever backend remains Mongo.
        Slice: slice-32-storage-backend-protocol

        Given STORAGE_BACKEND is "mongo",
        When get_retriever_backend() is called,
        Then the Mongo RetrieverBackend adapter is returned.
        """
        ### Given
        mock_retriever = MagicMock(name="MongoRetrieverBackend")

        ### When
        with (
            patch("server.settings.settings.storage_backend", "mongo"),
            patch(
                "server.db.mongo_store.get_mongo_retriever",
                return_value=mock_retriever,
            ),
        ):
            actual = get_retriever_backend()

        ### Then
        assert actual is mock_retriever, f"Expected mongo retriever adapter, got {actual!r}"

    def test_given_storage_backend_redis_when_get_storage_backend_then_raises_value_error(
        self,
    ) -> None:
        """
        Scenario: Factory rejects unknown backend.
        Slice: slice-32-storage-backend-protocol

        Given STORAGE_BACKEND="redis",
        When get_storage_backend() is called,
        Then a clear ValueError is raised with no silent fallback.
        """
        ### Given / When / Then
        with (
            patch("server.settings.settings.storage_backend", "redis"),
            pytest.raises(ValueError, match="Unknown storage backend 'redis'"),
        ):
            get_storage_backend()

    def test_given_storage_backend_redis_when_get_retriever_backend_then_raises_value_error(
        self,
    ) -> None:
        """
        Scenario: Factory rejects unknown backend for retriever path.
        Slice: slice-32-storage-backend-protocol

        Given STORAGE_BACKEND="redis",
        When get_retriever_backend() is called,
        Then a clear ValueError is raised.
        """
        ### Given / When / Then
        with (
            patch("server.settings.settings.storage_backend", "redis"),
            pytest.raises(ValueError, match="Unknown storage backend 'redis'"),
        ):
            get_retriever_backend()

    def test_given_storage_backend_postgres_when_get_storage_backend_then_returns_pg_adapter(
        self,
    ) -> None:
        """
        Scenario: Postgres selects the pgvector StorageBackend adapter.
        Slice: slice-33-postgres-schema-crud

        Given STORAGE_BACKEND="postgres",
        When get_storage_backend() is called,
        Then the Postgres StorageBackend adapter is returned.
        """
        ### Given
        mock_storage = MagicMock(name="PostgresStorageBackend")

        ### When
        with (
            patch("server.settings.settings.storage_backend", "postgres"),
            patch(
                "server.db.postgres_store.get_postgres_storage",
                return_value=mock_storage,
            ),
        ):
            actual = get_storage_backend()

        ### Then
        assert actual is mock_storage, f"Expected postgres storage adapter, got {actual!r}"

    def test_given_storage_backend_postgres_when_get_retriever_backend_then_returns_pg_adapter(
        self,
    ) -> None:
        """
        Scenario: Postgres selects the pgvector RetrieverBackend adapter.
        Slice: slice-34-postgres-dense-retrieval

        Given STORAGE_BACKEND="postgres",
        When get_retriever_backend() is called,
        Then the Postgres RetrieverBackend adapter is returned.
        """
        ### Given
        mock_retriever = MagicMock(name="PostgresRetrieverBackend")

        ### When
        with (
            patch("server.settings.settings.storage_backend", "postgres"),
            patch(
                "server.db.postgres_store.get_postgres_retriever",
                return_value=mock_retriever,
            ),
        ):
            actual = get_retriever_backend()

        ### Then
        assert actual is mock_retriever, f"Expected postgres retriever adapter, got {actual!r}"

    def test_given_storage_backend_postgres_when_sparse_retrieval_requested_then_names_slice_35(
        self,
    ) -> None:
        """
        Scenario: Unimplemented Postgres retrieval methods fail loudly, not silently.
        Slice: slice-34-postgres-dense-retrieval

        Given the Postgres retriever adapter,
        When a sparse search is requested,
        Then NotImplementedError names Slice 35 and suggests a working alternative —
        a sweep that quietly fell back to dense would invalidate its own comparison.
        """
        ### Given
        retriever = get_postgres_retriever()

        ### When / Then
        with pytest.raises(NotImplementedError, match="Slice 35"):
            retriever.search(
                RetrievalMethod.SPARSE,
                "what is the deadline?",
                "exp-1",
                "all-MiniLM-L6-v2",
                "run-1",
                5,
                None,
            )
