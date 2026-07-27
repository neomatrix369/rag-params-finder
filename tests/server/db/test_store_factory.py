"""
Tests for server.db.ports.store_factory.

Author: Mani Sarkar
Created: 2026-07-25
Scope: storage_backend routing — mongodb default, unknown rejection, postgres adapters
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from server.db.ports.store_factory import get_retriever_backend, get_storage_backend
from server.db.postgres.postgres_store import get_postgres_retriever
from server.models.enums import RetrievalMethod


class TestStoreFactoryShould:
    """Scenario: factory selects StorageBackend / RetrieverBackend from settings."""

    def test_given_mongo_default_when_get_storage_backend_then_returns_mongo_adapter(
        self,
    ) -> None:
        """
        Scenario: Default backend remains Mongo.
        Slice: slice-32-storage-backend-protocol

        Given STORAGE_BACKEND is unset or "mongodb",
        When get_storage_backend() is called,
        Then the Mongo StorageBackend adapter is returned.
        """
        ### Given
        mock_storage = MagicMock(name="MongoStorageBackend")

        ### When
        with (
            patch("server.settings.settings.storage_backend", "mongodb"),
            patch(
                "server.settings.settings.mongodb_uri",
                "mongodb://localhost:27017/rag_params_finder?directConnection=true",
            ),
            patch(
                "server.db.mongo.mongo_store.get_mongo_storage",
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

        Given STORAGE_BACKEND is "mongodb",
        When get_retriever_backend() is called,
        Then the Mongo RetrieverBackend adapter is returned.
        """
        ### Given
        mock_retriever = MagicMock(name="MongoRetrieverBackend")

        ### When
        with (
            patch("server.settings.settings.storage_backend", "mongodb"),
            patch(
                "server.settings.settings.mongodb_uri",
                "mongodb://localhost:27017/rag_params_finder?directConnection=true",
            ),
            patch(
                "server.db.mongo.mongo_store.get_mongo_retriever",
                return_value=mock_retriever,
            ),
        ):
            actual = get_retriever_backend()

        ### Then
        assert actual is mock_retriever, f"Expected mongo retriever adapter, got {actual!r}"

    def test_given_legacy_mongo_alias_when_get_storage_backend_then_returns_mongo_adapter(
        self,
    ) -> None:
        """
        Scenario: Legacy STORAGE_BACKEND=mongo still selects MongoDB.
        Slice: naming consistency — mongodb canonical token

        Given STORAGE_BACKEND="mongo" (legacy alias),
        When get_storage_backend() is called,
        Then the MongoDB StorageBackend adapter is returned.
        """
        ### Given
        mock_storage = MagicMock(name="MongoStorageBackend")

        ### When
        with (
            patch("server.settings.settings.storage_backend", "mongo"),
            patch(
                "server.settings.settings.mongodb_uri",
                "mongodb://localhost:27017/rag_params_finder?directConnection=true",
            ),
            patch(
                "server.db.mongo.mongo_store.get_mongo_storage",
                return_value=mock_storage,
            ),
        ):
            actual = get_storage_backend()

        ### Then
        assert actual is mock_storage, f"Expected mongodb storage adapter, got {actual!r}"

    def test_given_mongo_without_uri_when_get_storage_backend_then_raises_value_error(
        self,
    ) -> None:
        """
        Scenario: Factory fails closed when MONGODB_URI is missing.
        Slice: slice-32-storage-backend-protocol

        Given STORAGE_BACKEND="mongodb" and MONGODB_URI is empty,
        When get_storage_backend() is called,
        Then ValueError names the missing URI (matches CI unit tier).
        """
        ### Given / When / Then
        with (
            patch("server.settings.settings.storage_backend", "mongodb"),
            patch("server.settings.settings.mongodb_uri", ""),
            pytest.raises(ValueError, match="requires MONGODB_URI"),
        ):
            get_storage_backend()

    def test_given_postgres_without_url_when_get_storage_backend_then_raises_value_error(
        self,
    ) -> None:
        """
        Scenario: Factory fails closed when DATABASE_URL is missing.
        Slice: 43 — Supabase/Postgres operator parity

        Given STORAGE_BACKEND="postgres" and DATABASE_URL is empty,
        When get_storage_backend() is called,
        Then ValueError names the missing URI.
        """
        ### Given / When / Then
        with (
            patch("server.settings.settings.storage_backend", "postgres"),
            patch("server.settings.settings.database_url", ""),
            pytest.raises(ValueError, match="requires DATABASE_URL"),
        ):
            get_storage_backend()

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
                "server.settings.settings.database_url",
                "postgresql://rag:rag@localhost:5433/rag_params_finder",
            ),
            patch(
                "server.db.postgres.postgres_store.get_postgres_storage",
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
                "server.settings.settings.database_url",
                "postgresql://rag:rag@localhost:5433/rag_params_finder",
            ),
            patch(
                "server.db.postgres.postgres_store.get_postgres_retriever",
                return_value=mock_retriever,
            ),
        ):
            actual = get_retriever_backend()

        ### Then
        assert actual is mock_retriever, f"Expected postgres retriever adapter, got {actual!r}"

    def test_given_postgres_retriever_when_sparse_search_then_routes_to_sparse_search(
        self,
    ) -> None:
        """
        Scenario: Postgres retriever dispatches sparse to the Slice 35 path.
        Slice: slice-35-postgres-sparse-hybrid

        Given the Postgres retriever adapter,
        When a sparse search is requested,
        Then sparse_search is invoked (no NotImplementedError).
        """
        ### Given
        retriever = get_postgres_retriever()
        expected = [MagicMock(name="hit")]

        ### When
        with patch(
            "server.core.retrieval.retriever_postgres.sparse_search",
            return_value=expected,
        ) as mock_sparse:
            actual = retriever.search(
                RetrievalMethod.SPARSE,
                "what is the deadline?",
                "exp-1",
                "all-MiniLM-L6-v2",
                "run-1",
                5,
                None,
            )

        ### Then
        assert actual is expected
        mock_sparse.assert_called_once_with(
            "what is the deadline?",
            "exp-1",
            "all-MiniLM-L6-v2",
            "run-1",
            5,
        )
