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
        assert known == frozenset({"mongodb", "postgres", "elasticsearch"})

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

    def test_given_mongodb_backend_when_resolve_adapter_called_then_no_psycopg_loaded(
        self,
    ) -> None:
        """
        Scenario: resolving the *mongodb* adapter never transitively loads psycopg.

        Given a fresh Python process with STORAGE_BACKEND=mongodb,
        When resolve_adapter("mongodb") is called (as get_vector_store() does),
        Then psycopg is not present in sys.modules afterward — a bare
        ``import server.db.ports.registry`` alone cannot catch a leak that
        only appears once the mongodb target module is actually imported
        (e.g. through a shared guard file that also imports Postgres helpers
        at module scope), so this test drives the real call path in a
        subprocess, where mid-process imports cannot be undone.
        """
        ### Given
        # "LEAKED::" marker isolates the assertion from unrelated stdout noise
        # (e.g. the settings-loaded INFO log line server startup emits).
        probe = (
            "import os, sys; "
            "os.environ['STORAGE_BACKEND'] = 'mongodb'; "
            "os.environ['MONGODB_URI'] = 'mongodb://localhost:27017/test'; "
            "from server.db.ports.registry import resolve_adapter; "
            "resolve_adapter('mongodb'); "
            "loaded = sorted(m for m in sys.modules if 'psycopg' in m or 'elasticsearch' in m); "
            "print('LEAKED::' + ','.join(loaded))"
        )

        ### When
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            check=True,
        )
        leaked = next(
            line.removeprefix("LEAKED::")
            for line in result.stdout.splitlines()
            if line.startswith("LEAKED::")
        )

        ### Then
        assert leaked == "", (
            f"psycopg/elasticsearch leaked in via resolve_adapter('mongodb'): {leaked}"
        )

    def test_given_mongodb_backend_when_get_vector_store_called_then_no_psycopg_loaded(
        self,
    ) -> None:
        """
        Scenario: the real call path (get_vector_store) never loads psycopg
        for a mongodb-only process.

        Given a fresh Python process with STORAGE_BACKEND=mongodb,
        When get_vector_store() is called,
        Then psycopg is not present in sys.modules afterward. This exercises
        the exact production entrypoint (store_factory.get_vector_store),
        not just the registry's resolve_adapter mechanism.
        """
        ### Given
        # "LEAKED::" marker isolates the assertion from unrelated stdout noise
        # (e.g. the settings-loaded INFO log line server startup emits).
        probe = (
            "import os, sys; "
            "os.environ['STORAGE_BACKEND'] = 'mongodb'; "
            "os.environ['MONGODB_URI'] = 'mongodb://localhost:27017/test'; "
            "from server.db.ports.store_factory import get_vector_store; "
            "get_vector_store(); "
            "loaded = sorted(m for m in sys.modules if 'psycopg' in m or 'elasticsearch' in m); "
            "print('LEAKED::' + ','.join(loaded))"
        )

        ### When
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            check=True,
        )
        leaked = next(
            line.removeprefix("LEAKED::")
            for line in result.stdout.splitlines()
            if line.startswith("LEAKED::")
        )

        ### Then
        assert leaked == "", f"psycopg/elasticsearch leaked in via get_vector_store(): {leaked}"

    def test_given_postgres_backend_when_resolve_adapter_called_then_no_pymongo_loaded(
        self,
    ) -> None:
        """
        Scenario: resolving the *postgres* adapter never transitively loads pymongo.

        Given a fresh Python process with STORAGE_BACKEND=postgres,
        When resolve_adapter("postgres") is called (as get_vector_store() does),
        Then pymongo is not present in sys.modules afterward — the reciprocal
        of the psycopg-leak check above. A bare ``import
        server.db.ports.registry`` alone cannot catch a leak that only
        appears once the postgres target module is actually imported (e.g.
        through a shared guard file that also imports Mongo helpers at
        module scope), so this test drives the real call path in a
        subprocess, where mid-process imports cannot be undone.
        """
        ### Given
        # "LEAKED::" marker isolates the assertion from unrelated stdout noise
        # (e.g. the settings-loaded INFO log line server startup emits).
        probe = (
            "import os, sys; "
            "os.environ['STORAGE_BACKEND'] = 'postgres'; "
            "os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost:5432/test'; "
            "from server.db.ports.registry import resolve_adapter; "
            "resolve_adapter('postgres'); "
            "loaded = sorted(m for m in sys.modules if 'pymongo' in m); "
            "print('LEAKED::' + ','.join(loaded))"
        )

        ### When
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            check=True,
        )
        leaked = next(
            line.removeprefix("LEAKED::")
            for line in result.stdout.splitlines()
            if line.startswith("LEAKED::")
        )

        ### Then
        assert leaked == "", f"pymongo leaked in via resolve_adapter('postgres'): {leaked}"

    def test_given_postgres_backend_when_get_vector_store_called_then_no_pymongo_loaded(
        self,
    ) -> None:
        """
        Scenario: the real call path (get_vector_store) never loads pymongo
        for a postgres-only process.

        Given a fresh Python process with STORAGE_BACKEND=postgres,
        When get_vector_store() is called,
        Then pymongo is not present in sys.modules afterward. This exercises
        the exact production entrypoint (store_factory.get_vector_store),
        not just the registry's resolve_adapter mechanism — the reciprocal
        of the mongodb-side get_vector_store check above.
        """
        ### Given
        # "LEAKED::" marker isolates the assertion from unrelated stdout noise
        # (e.g. the settings-loaded INFO log line server startup emits).
        probe = (
            "import os, sys; "
            "os.environ['STORAGE_BACKEND'] = 'postgres'; "
            "os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost:5432/test'; "
            "from server.db.ports.store_factory import get_vector_store; "
            "get_vector_store(); "
            "loaded = sorted(m for m in sys.modules if 'pymongo' in m); "
            "print('LEAKED::' + ','.join(loaded))"
        )

        ### When
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            check=True,
        )
        leaked = next(
            line.removeprefix("LEAKED::")
            for line in result.stdout.splitlines()
            if line.startswith("LEAKED::")
        )

        ### Then
        assert leaked == "", f"pymongo leaked in via get_vector_store(): {leaked}"


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
