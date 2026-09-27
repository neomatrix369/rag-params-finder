"""
Tests for server.db.ports.registry.

Author: Mani Sarkar
Created: 2026-09-27
Scope: table-driven vector-store registry — known-provider listing,
       unknown-provider rejection with guidance, lazy import mechanism,
       and the two real registry targets (Slice 49A Stream 2).

TestResolveAdapterRealTargetsShould asserts the *real* registry targets
("mongodb" -> MongoVectorStore, "postgres" -> PostgresVectorStore) import
cleanly now that Stream 3 added mongo_vector_store.py / postgres_vector_store.py.
"""

from __future__ import annotations

import subprocess
import sys
import types

import pytest

from server.db.ports import registry as registry_module
from server.db.ports.registry import known_vector_stores, resolve_adapter


class TestKnownVectorStoresShould:
    """Scenario: listing the registry's provider keys."""

    def test_given_static_registry_when_known_stores_called_then_returns_mongodb_and_postgres(
        self,
    ) -> None:
        """
        Scenario: the registry's known set matches its table.

        Given the static _VECTOR_STORE_REGISTRY,
        When known_vector_stores() is called,
        Then it returns exactly the registered provider keys.
        """
        ### Given
        ### When
        known = known_vector_stores()

        ### Then
        assert known == frozenset({"mongodb", "postgres"})

    def test_given_known_vector_stores_when_return_type_inspected_then_it_is_a_frozenset(
        self,
    ) -> None:
        """
        Scenario: callers cannot mutate the registry via the returned set.

        Given known_vector_stores(),
        When the return type is inspected,
        Then it is a frozenset (immutable).
        """
        ### Given
        ### When
        known = known_vector_stores()

        ### Then
        assert isinstance(known, frozenset)


class TestResolveAdapterUnknownProviderShould:
    """Scenario: Unknown vector store is rejected with guidance (spec GWT)."""

    def test_given_unregistered_provider_when_resolve_adapter_called_then_error_lists_known_stores(
        self,
    ) -> None:
        """
        Scenario: an unregistered provider key is rejected clearly.

        Given VECTOR_STORE_BACKEND=unknown,
        When resolve_adapter("unknown") is called,
        Then a ValueError is raised naming "unknown" and listing the known
        vector stores (mongodb, postgres) so the operator knows what to set
        instead.
        """
        ### Given
        provider = "unknown"

        ### When
        ### Then
        with pytest.raises(ValueError) as excinfo:
            resolve_adapter(provider)
        message = str(excinfo.value)
        assert "unknown" in message
        assert "mongodb" in message
        assert "postgres" in message


class TestResolveAdapterMechanismShould:
    """Scenario: resolve_adapter performs a lazy, generic importlib lookup."""

    def test_given_registered_stub_target_when_resolve_adapter_called_then_returns_exact_class(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Scenario: the resolution mechanism works against any registered
        target, independent of whether Stream 3's real composites exist yet.

        Given a registry entry pointing at a stub module:class,
        When resolve_adapter(provider) is called,
        Then it returns that exact class object.
        """
        ### Given
        stub_module = types.ModuleType("tests._stub_vector_store_module")

        class _StubVectorStore:
            """Stand-in for a composite adapter class."""

        stub_module.StubVectorStore = _StubVectorStore  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "tests._stub_vector_store_module", stub_module)
        monkeypatch.setitem(
            registry_module._VECTOR_STORE_REGISTRY,
            "stub",
            "tests._stub_vector_store_module:StubVectorStore",
        )

        ### When
        resolved = resolve_adapter("stub")

        ### Then
        assert resolved is _StubVectorStore

    def test_given_missing_target_module_when_resolve_adapter_called_then_module_not_found_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Scenario: a registry entry pointing at a non-existent module fails
        with the underlying import error rather than a swallowed/special case.

        Given a registered provider whose target module does not exist,
        When resolve_adapter(provider) is called,
        Then a ModuleNotFoundError propagates (not a silently-wrong result).
        """
        ### Given
        monkeypatch.setitem(
            registry_module._VECTOR_STORE_REGISTRY,
            "ghost",
            "tests._nonexistent_module_for_registry_test:GhostVectorStore",
        )

        ### When
        ### Then
        with pytest.raises(ModuleNotFoundError):
            resolve_adapter("ghost")

    def test_given_fresh_process_when_registry_imported_then_no_psycopg_or_elasticsearch_loaded(
        self,
    ) -> None:
        """
        Scenario: importing the registry module never pulls in a driver.

        Given a fresh Python process,
        When only server.db.ports.registry is imported,
        Then neither psycopg (nor psycopg2) nor any elasticsearch client
        module is present in sys.modules — drivers load only inside
        resolve_adapter, for the one provider actually requested.
        """
        ### Given
        probe = (
            "import sys; "
            "import server.db.ports.registry; "
            "loaded = sorted(m for m in sys.modules if 'psycopg' in m or 'elasticsearch' in m); "
            "print(','.join(loaded))"
        )

        ### When
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            check=True,
        )

        ### Then
        assert result.stdout.strip() == ""


class TestResolveAdapterRealTargetsShould:
    """Scenario: resolving the real registry entries (Stream 3 composites)."""

    def test_given_mongodb_provider_when_resolve_adapter_called_then_imports_mongo_vector_store(
        self,
    ) -> None:
        """
        Scenario: Registry resolves the configured vector store by lazy import.

        Given VECTOR_STORE_BACKEND is unset and STORAGE_BACKEND=mongodb,
        When resolve_adapter("mongodb") is called,
        Then the registry lazily imports MongoVectorStore.
        """
        ### Given
        ### When
        adapter = resolve_adapter("mongodb")

        ### Then
        assert adapter.__name__ == "MongoVectorStore"

    def test_given_postgres_provider_when_resolve_adapter_called_then_imports_postgres_vector_store(
        self,
    ) -> None:
        """
        Scenario: Registry resolves the configured vector store by lazy import.

        Given STORAGE_BACKEND=postgres and VECTOR_STORE_BACKEND unset,
        When resolve_adapter("postgres") is called,
        Then the registry lazily imports PostgresVectorStore.
        """
        ### Given
        ### When
        adapter = resolve_adapter("postgres")

        ### Then
        assert adapter.__name__ == "PostgresVectorStore"
