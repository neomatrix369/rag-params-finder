"""
Tests for server.db.store_factory.

Author: swami
Created: 2026-07-25
Scope: storage_backend routing — mongo default, unknown rejection, postgres NotImplemented
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from server.db.store_factory import get_retriever_backend, get_storage_backend


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

    def test_given_storage_backend_postgres_when_get_storage_backend_then_raises_not_implemented(
        self,
    ) -> None:
        """
        Scenario: Postgres storage raises clear NotImplemented until Slice 33.
        Slice: slice-32-storage-backend-protocol

        Given STORAGE_BACKEND="postgres",
        When get_storage_backend() is called,
        Then NotImplementedError mentions Slice 33+.
        """
        ### Given / When / Then
        with (
            patch("server.settings.settings.storage_backend", "postgres"),
            pytest.raises(NotImplementedError, match="Slice 33"),
        ):
            get_storage_backend()

    def test_given_storage_backend_postgres_when_get_retriever_backend_then_raises_not_implemented(
        self,
    ) -> None:
        """
        Scenario: Postgres retriever raises clear NotImplemented until Slice 34.
        Slice: slice-32-storage-backend-protocol

        Given STORAGE_BACKEND="postgres",
        When get_retriever_backend() is called,
        Then NotImplementedError mentions Slice 34+.
        """
        ### Given / When / Then
        with (
            patch("server.settings.settings.storage_backend", "postgres"),
            pytest.raises(NotImplementedError, match="Slice 34"),
        ):
            get_retriever_backend()
