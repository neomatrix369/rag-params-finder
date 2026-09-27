"""
Tests for the VECTOR_STORE_BACKEND setting and get_vector_store()/get_retriever_backend() wiring.

Author: Mani Sarkar
Created: 2026-09-27
Scope: Slice 49A Stream 4 — VECTOR_STORE_BACKEND default-to-STORAGE_BACKEND,
       the 49A equality lock ("split stores arrive in Slice 49B"),
       elasticsearch rejection as a run-state store, unknown vector-store
       rejection, get_retriever_backend() delegating to
       get_vector_store().retriever(), and the single DatabaseProvider Literal
       shared by RunStatus and ExperimentConfig.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
)
from server.models.config import DatabaseProvider as ConfigDatabaseProvider
from server.models.enums import ChunkingMethod, RetrievalMethod
from server.models.status import DatabaseProvider as StatusDatabaseProvider
from server.models.status import RunStatus
from server.settings import Settings


def _minimal_experiment_config_kwargs(database_provider: str) -> dict:
    """Smallest ExperimentConfig payload that passes model validation."""
    return {
        "experiment_name": "exp",
        "data_paths": ["./data"],
        "queries_file": "./queries.json",
        "database_provider": database_provider,
        "embedding": EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
        "chunking": ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
        ),
        "retrieval": RetrievalConfig(methods=[RetrievalMethod.DENSE]),
        "execution": ExecutionConfig(),
    }


def _minimal_run_status_kwargs(database_provider: str) -> dict:
    """Smallest RunStatus payload that passes model validation."""
    return {
        "run_id": "run-1",
        "experiment_id": "exp-1",
        "phase": "queued",
        "database_provider": database_provider,
        "embedding_provider": "local",
        "embedding_model": "all-MiniLM-L6-v2",
        "chunking_method": "fixed",
        "chunk_size": 512,
        "overlap": 50,
        "retrieval_method": "dense",
        "retrieval_provider": "local",
    }


class TestVectorStoreBackendDefaultShould:
    """Scenario: VECTOR_STORE_BACKEND defaults to STORAGE_BACKEND when unset."""

    @pytest.mark.parametrize(
        "storage_backend, connection_kwargs",
        [
            ("mongodb", {"mongodb_uri": "mongodb://localhost:27017/db"}),
            (
                "postgres",
                {"database_url": "postgresql://rag:rag@localhost:5433/rag_params_finder"},
            ),
        ],
    )
    def test_given_vector_store_backend_unset_when_settings_load_then_defaults_to_storage_backend(
        self, storage_backend: str, connection_kwargs: dict
    ) -> None:
        """
        Scenario: VECTOR_STORE_BACKEND defaults to STORAGE_BACKEND.

        Given STORAGE_BACKEND=<storage_backend> and VECTOR_STORE_BACKEND unset,
        When settings load,
        Then the active vector store equals <storage_backend>.
        """
        ### Given
        ### When
        loaded = Settings(
            _env_file=None,
            storage_backend=storage_backend,
            **connection_kwargs,
        )

        ### Then
        assert loaded.vector_store_backend == storage_backend


class TestVectorStoreBackendLockShould:
    """Scenario: pairing rule (ii) (Slice 49B, DECISIONS #241).

    Replaces the 49A equality lock: a run-state-capable vector store
    (mongodb/postgres) must equal STORAGE_BACKEND; a vector-only store
    (elasticsearch, or the test-only ``memory`` provider) may pair with
    either run-state store.
    """

    @pytest.mark.parametrize(
        "storage_backend, vector_store_backend",
        [
            ("postgres", "mongodb"),
            ("mongodb", "postgres"),
        ],
    )
    def test_given_two_run_state_capable_backends_mismatched_when_settings_validate_then_raises(
        self, storage_backend: str, vector_store_backend: str
    ) -> None:
        """
        Scenario: A store that can hold run state must hold it.

        Given STORAGE_BACKEND=<storage_backend> and
              VECTOR_STORE_BACKEND=<vector_store_backend>, both run-state
              capable and mismatched,
        When settings validate,
        Then a clear error explains that a store able to hold run state
             must also hold it.
        """
        ### Given
        connection_kwargs = (
            {"mongodb_uri": "mongodb://localhost:27017/db"}
            if storage_backend == "mongodb"
            else {"database_url": "postgresql://rag:rag@localhost:5433/rag_params_finder"}
        )

        ### When / Then
        with pytest.raises(ValidationError, match="can hold run state, so it must hold both"):
            Settings(
                _env_file=None,
                storage_backend=storage_backend,
                vector_store_backend=vector_store_backend,
                **connection_kwargs,
            )

    @pytest.mark.parametrize("storage_backend", ["mongodb", "postgres"])
    def test_given_vector_only_backend_when_settings_validate_then_accepted(
        self, storage_backend: str
    ) -> None:
        """
        Scenario Outline: A vector-only store pairs with either run-state store.

        Given STORAGE_BACKEND=<storage_backend> and
              VECTOR_STORE_BACKEND=elasticsearch (vector-only,
              can_host_run_state=False, not yet registered — Slice 50),
        When settings validate,
        Then they are accepted.
        """
        ### Given
        connection_kwargs = (
            {"mongodb_uri": "mongodb://localhost:27017/db"}
            if storage_backend == "mongodb"
            else {"database_url": "postgresql://rag:rag@localhost:5433/rag_params_finder"}
        )

        ### When
        loaded = Settings(
            _env_file=None,
            storage_backend=storage_backend,
            vector_store_backend="elasticsearch",
            **connection_kwargs,
        )

        ### Then
        assert loaded.vector_store_backend == "elasticsearch"
        assert loaded.storage_backend == storage_backend

    @pytest.mark.parametrize("storage_backend", ["mongodb", "postgres"])
    def test_given_registered_vector_only_backend_when_settings_validate_then_accepted(
        self, storage_backend: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Scenario Outline: A vector-only store pairs with either run-state store
        (registry-driven path — a registered adapter with
        ``can_host_run_state=False``, not the not-yet-registered fallback).

        Given STORAGE_BACKEND=<storage_backend> and
              VECTOR_STORE_BACKEND=memory (registered for this test only,
              declares can_host_run_state=False),
        When settings validate,
        Then they are accepted.
        """
        ### Given
        from server.db.ports import registry as vector_store_registry

        monkeypatch.setitem(
            vector_store_registry._VECTOR_STORE_REGISTRY,
            "memory",
            "tests.helpers.memory_vector_store:MemoryVectorStore",
        )
        connection_kwargs = (
            {"mongodb_uri": "mongodb://localhost:27017/db"}
            if storage_backend == "mongodb"
            else {"database_url": "postgresql://rag:rag@localhost:5433/rag_params_finder"}
        )

        ### When
        loaded = Settings(
            _env_file=None,
            storage_backend=storage_backend,
            vector_store_backend="memory",
            **connection_kwargs,
        )

        ### Then
        assert loaded.vector_store_backend == "memory"


class TestStorageBackendElasticsearchRejectionShould:
    """Scenario: elasticsearch is rejected as a run-state store."""

    def test_given_storage_backend_elasticsearch_when_validate_then_raises_vector_store_only(
        self,
    ) -> None:
        """
        Scenario: elasticsearch is rejected as a run-state store.

        Given STORAGE_BACKEND=elasticsearch,
        When settings validate,
        Then a clear error names elasticsearch as vector-store-only
             and instructs setting STORAGE_BACKEND to mongodb or postgres.
        """
        ### Given
        ### When / Then
        with pytest.raises(
            ValidationError,
            match="elasticsearch is vector-store-only",
        ) as excinfo:
            Settings(_env_file=None, storage_backend="elasticsearch")

        ### Then
        assert "mongodb" in str(excinfo.value)
        assert "postgres" in str(excinfo.value)


class TestUnknownVectorStoreShould:
    """Scenario: unknown vector store is rejected with guidance."""

    def test_given_vector_store_backend_unknown_when_validate_then_raises_naming_known_stores(
        self,
    ) -> None:
        """
        Scenario: Unknown vector store is rejected with guidance.

        Given VECTOR_STORE_BACKEND=unknown,
        When settings validate (the registry resolution point),
        Then a clear error names the value and lists the known vector stores.
        """
        ### Given
        ### When / Then
        match = "Unknown VECTOR_STORE_BACKEND='unknown'"
        with pytest.raises(ValidationError, match=match) as excinfo:
            Settings(
                _env_file=None,
                storage_backend="mongodb",
                vector_store_backend="unknown",
                mongodb_uri="mongodb://localhost:27017/db",
            )

        ### Then
        assert "mongodb" in str(excinfo.value)
        assert "postgres" in str(excinfo.value)


class TestGetRetrieverBackendDelegationShould:
    """Scenario: the retriever factory reads the vector store."""

    def test_given_get_vector_store_patched_when_get_retriever_backend_called_then_returns_it(
        self,
    ) -> None:
        """
        Scenario: The retriever factory reads the vector store.

        Given get_vector_store() is patched to return a fake VectorStore,
        When get_retriever_backend() is called,
        Then it returns get_vector_store().retriever() —
             same name and signature as before the port split.
        """
        ### Given
        from server.db.ports.store_factory import get_retriever_backend

        mock_vector_store = MagicMock(name="VectorStore")
        mock_retriever = MagicMock(name="RetrieverBackend")
        mock_vector_store.retriever.return_value = mock_retriever

        ### When
        with patch(
            "server.db.ports.store_factory.get_vector_store",
            return_value=mock_vector_store,
        ):
            actual = get_retriever_backend()

        ### Then
        assert actual is mock_retriever
        mock_vector_store.retriever.assert_called_once_with()


class TestEnsureStorageReadyTwoStoreShould:
    """Scenario: Vector store misconfigured (boot behaviour, DECISIONS #250).

    ``ensure_storage_ready()`` checks both stores' configuration; a missing/
    placeholder URI on *either* side fails boot naming the specific setting.
    """

    def test_given_split_store_with_missing_vector_uri_when_ensure_ready_then_raises_naming_it(
        self,
    ) -> None:
        """
        Scenario: Vector store misconfigured.

        Given VECTOR_STORE_BACKEND=elasticsearch and ELASTICSEARCH_URL unset
              (STORAGE_BACKEND=postgres, configured),
        When ensure_storage_ready() runs (as it does from server lifespan),
        Then it raises naming ELASTICSEARCH_URL.
        """
        ### Given
        loaded = Settings(
            _env_file=None,
            storage_backend="postgres",
            vector_store_backend="elasticsearch",
            database_url="postgresql://rag:rag@localhost:5433/rag_params_finder",
        )

        ### When / Then
        with pytest.raises(ValueError, match="ELASTICSEARCH_URL"):
            loaded.ensure_storage_ready()

    def test_given_split_store_with_both_uris_present_when_ensure_ready_then_does_not_raise(
        self,
    ) -> None:
        """
        Scenario: A configured split store passes the boot check.

        Given STORAGE_BACKEND=postgres (configured) and
              VECTOR_STORE_BACKEND=elasticsearch with ELASTICSEARCH_URL set,
        When ensure_storage_ready() runs,
        Then it does not raise (reachability is a /healthz + preflight concern,
             not a boot-time one).
        """
        ### Given
        loaded = Settings(
            _env_file=None,
            storage_backend="postgres",
            vector_store_backend="elasticsearch",
            database_url="postgresql://rag:rag@localhost:5433/rag_params_finder",
            elasticsearch_url="http://localhost:9200",
        )

        ### When / Then
        loaded.ensure_storage_ready()  # no raise


class TestSingleDatabaseProviderLiteralShould:
    """Scenario: One DatabaseProvider Literal."""

    def test_given_status_and_config_modules_when_imported_then_share_the_same_literal_object(
        self,
    ) -> None:
        """
        Scenario: status.py and config.py expose the identical Literal object.

        Given server.models.status.DatabaseProvider and
              server.models.config.DatabaseProvider,
        When both are imported,
        Then they are the same object (one owner, no duplicate definition).
        """
        ### Given / When
        ### Then
        assert StatusDatabaseProvider is ConfigDatabaseProvider

    @pytest.mark.parametrize("provider", ["mongodb", "postgres", "supabase"])
    def test_given_each_known_provider_when_validating_both_models_then_both_accept(
        self, provider: str
    ) -> None:
        """
        Scenario: One DatabaseProvider Literal — RunStatus and ExperimentConfig
        validate the same set of provider values.

        Given the server package,
        When RunStatus and ExperimentConfig are validated with each known
             provider,
        Then both accept it (sourced from one Literal in
             server/models/config.py).
        """
        ### Given
        ### When
        run_status = RunStatus(**_minimal_run_status_kwargs(provider))
        experiment_config = ExperimentConfig(**_minimal_experiment_config_kwargs(provider))

        ### Then
        assert run_status.database_provider == provider
        assert experiment_config.database_provider in {"mongodb", "postgres"}

    def test_given_an_unknown_provider_when_validating_both_models_then_both_reject(
        self,
    ) -> None:
        """
        Scenario: One DatabaseProvider Literal — both models reject an unknown
        provider identically.

        Given a provider value outside the Literal ("dynamodb"),
        When RunStatus and ExperimentConfig are validated,
        Then both raise ValidationError.
        """
        ### Given
        ### When / Then
        with pytest.raises(ValidationError):
            RunStatus(**_minimal_run_status_kwargs("dynamodb"))
        with pytest.raises(ValidationError):
            ExperimentConfig(**_minimal_experiment_config_kwargs("dynamodb"))
