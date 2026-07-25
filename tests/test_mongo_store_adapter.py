"""
Tests for server.db.mongo_store adapter + call-site port usage.

Author: Mani Sarkar
Created: 2026-07-25
Scope: MongoStorageBackend / MongoRetrieverBackend Protocol conformance;
       orchestrator/API modules do not import server.db.atlas directly
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

from server.db.mongo_store import MongoRetrieverBackend, MongoStorageBackend
from server.db.retriever_backend import RetrieverBackend
from server.db.storage import StorageBackend
from server.models.enums import RetrievalMethod

_REPO_ROOT = Path(__file__).resolve().parents[1]

_NO_DIRECT_ATLAS_MODULES = (
    "server/core/orchestrator.py",
    "server/api/experiments.py",
    "server/api/experiments_shared.py",
    "server/api/runs.py",
    "server/core/startup_reconciliation.py",
)


def _imports_atlas(module_path: Path) -> bool:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "server.db.atlas":
            return True
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "server.db.atlas" or alias.name.startswith("server.db.atlas."):
                    return True
    return False


class TestMongoStoreAdapterShould:
    """Scenario: Mongo adapters implement the storage and retriever ports."""

    def test_given_mongo_storage_adapter_when_checked_then_satisfies_storage_backend_protocol(
        self,
    ) -> None:
        """
        Scenario: Storage backend abstracts all data I/O via Protocol.
        Slice: slice-32-storage-backend-protocol

        Given a MongoStorageBackend instance,
        When it is checked against StorageBackend,
        Then it is a structural subtype of the Protocol.
        """
        ### Given
        adapter = MongoStorageBackend()

        ### When
        actual = isinstance(adapter, StorageBackend)

        ### Then
        assert actual is True, "MongoStorageBackend must satisfy StorageBackend Protocol"

    def test_given_mongo_retriever_adapter_when_checked_then_satisfies_retriever_backend_protocol(
        self,
    ) -> None:
        """
        Scenario: Retrieval flows through RetrieverBackend.
        Slice: slice-32-storage-backend-protocol

        Given a MongoRetrieverBackend instance,
        When it is checked against RetrieverBackend,
        Then it is a structural subtype of the Protocol.
        """
        ### Given
        adapter = MongoRetrieverBackend()

        ### When
        actual = isinstance(adapter, RetrieverBackend)

        ### Then
        assert actual is True, "MongoRetrieverBackend must satisfy RetrieverBackend Protocol"

    def test_given_mongo_retriever_when_search_called_then_dispatches_to_core_retriever(
        self,
    ) -> None:
        """
        Scenario: RetrieverBackend delegates search to existing Mongo retriever helpers.
        Slice: slice-32-storage-backend-protocol

        Given a MongoRetrieverBackend,
        When search() is called for dense retrieval,
        Then server.core.retriever.search is invoked with the same arguments.
        """
        ### Given
        adapter = MongoRetrieverBackend()
        expected_results = [MagicMock(name="SearchResult")]
        search_kwargs = {
            "method": RetrievalMethod.DENSE,
            "query_text": "what is rag?",
            "experiment_id": "exp-1",
            "embedding_model": "voyage-3.5-lite",
            "run_id": "run-1",
            "top_k": 5,
            "query_embedding": [0.1] * 1024,
        }

        ### When
        with patch(
            "server.db.mongo_store._mongo_search",
            return_value=expected_results,
        ) as mock_search:
            actual = adapter.search(**search_kwargs)

        ### Then
        assert actual is expected_results, "search() must return core retriever results"
        mock_search.assert_called_once_with(**search_kwargs)

    def test_given_orchestrator_and_api_modules_when_parsed_then_no_direct_atlas_imports(
        self,
    ) -> None:
        """
        Scenario: Call sites depend on ports — never on server.db.atlas.
        Slice: slice-32-storage-backend-protocol

        Given orchestrator, experiments*, runs, and startup_reconciliation modules,
        When their AST import graph is inspected,
        Then none import server.db.atlas directly.
        """
        ### Given / When
        offenders = [rel for rel in _NO_DIRECT_ATLAS_MODULES if _imports_atlas(_REPO_ROOT / rel)]

        ### Then
        assert offenders == [], (
            "These modules must not import server.db.atlas directly: " + ", ".join(offenders)
        )
