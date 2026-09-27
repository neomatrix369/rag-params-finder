"""
Golden/characterization baseline for the vector-store flow — pre-refactor.

Author: Mani Sarkar
Created: 2026-09-27
Scope: Slice 49A (Stream 1) — pins today's Mongo and Postgres behaviour for
       chunk write -> search -> delete -> db-stats -> /healthz -> preflight,
       with all I/O mocked at the same boundaries the existing suite already
       mocks (server.settings.settings, the lazy adapter constructors inside
       server/db/ports/store_factory.py, and the guard-level snapshot/probe
       functions). These records MUST stay green, unchanged, through the
       Slice 49A/49B refactor (VectorStore port + registry) — any diff here
       after the refactor is a behaviour regression, not an expected update.

Reuse ledger: mocking patterns lifted from
tests/server/db/test_store_factory.py (factory delegation),
tests/server/core/guards/test_health_check.py (storage_health shape),
tests/server/core/guards/test_search_index_guard.py (preflight backend scope),
tests/contract/test_storage_backend_contract.py (_DB_STATS_KEYS contract).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from server.core.guards.health_check import storage_health
from server.core.guards.search_index_guard import validate_experiment_search_indexes
from server.core.guards.search_index_plan import SearchIndexSnapshot
from server.db.ports.store_factory import get_retriever_backend, get_storage_backend
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
)
from server.models.enums import ChunkingMethod, RetrievalMethod

# Same key contract as tests/contract/test_storage_backend_contract.py::_DB_STATS_KEYS —
# duplicated here (not imported) because a characterization baseline must not depend on
# the live/integration suite; it stands alone as the pinned unit-tier golden record.
_DB_STATS_KEYS = frozenset(
    {
        "database_provider",
        "collection_name",
        "cluster_host",
        "total_chunks",
        "unique_documents",
        "embedding_models",
        "embedding_dimensions",
        "index_names",
        "retrieval_methods",
        "chunking_methods",
        "chunking_breakdown",
        "estimated_storage_mb",
        "estimated_embedding_mb",
        "estimated_metadata_mb",
        "runs_with_data",
        "avg_chunks_per_run",
        "total_results",
        "unique_queries",
        "run_breakdown",
    }
)


def _golden_db_stats(provider: str) -> dict:
    """A representative get_experiment_db_stats() payload, keyed exactly like today."""
    return {
        "database_provider": provider,
        "collection_name": "chunks",
        "cluster_host": "golden-host",
        "total_chunks": 42,
        "unique_documents": 3,
        "embedding_models": ["all-MiniLM-L6-v2"],
        "embedding_dimensions": [384],
        "index_names": ["vector_index_384"],
        "retrieval_methods": ["dense"],
        "chunking_methods": ["recursive"],
        "chunking_breakdown": {"recursive": 42},
        "estimated_storage_mb": 1.2,
        "estimated_embedding_mb": 1.0,
        "estimated_metadata_mb": 0.2,
        "runs_with_data": 1,
        "avg_chunks_per_run": 42.0,
        "total_results": 0,
        "unique_queries": 0,
        "run_breakdown": {},
    }


def _local_dense_config() -> ExperimentConfig:
    return ExperimentConfig(
        experiment_name="vector-store-characterization",
        data_paths=["./data"],
        queries_file="./queries.json",
        embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
        ),
        retrieval=RetrievalConfig(methods=[RetrievalMethod.DENSE]),
        execution=ExecutionConfig(),
    )


class TestChunkWriteCharacterizationShould:
    """Scenario: get_storage_backend().insert_chunks delegates unchanged, per backend."""

    def test_given_mongo_backend_when_chunks_inserted_then_adapter_receives_exact_docs(
        self,
    ) -> None:
        """
        Scenario: Mongo chunk-write golden record.

        Given STORAGE_BACKEND=mongodb and a mocked Mongo adapter,
        When get_storage_backend().insert_chunks(docs) is called,
        Then the exact docs list reaches the adapter unmodified (today's contract
        that store_factory is a pure pass-through, never wrapping/copying chunks).
        """
        ### Given
        mock_storage = MagicMock(name="MongoStorageBackend")
        docs = [{"chunk_id": "c1", "text": "Pell Grant eligibility"}]

        ### When
        with (
            patch("server.settings.settings.storage_backend", "mongodb"),
            patch("server.settings.settings.mongodb_uri", "mongodb://localhost:27017/db"),
            patch("server.db.mongo.mongo_store.get_mongo_storage", return_value=mock_storage),
        ):
            get_storage_backend().insert_chunks(docs)

        ### Then
        mock_storage.insert_chunks.assert_called_once_with(docs)

    def test_given_postgres_backend_when_chunks_inserted_then_adapter_receives_exact_docs(
        self,
    ) -> None:
        """
        Scenario: Postgres chunk-write golden record.

        Given STORAGE_BACKEND=postgres and a mocked Postgres adapter,
        When get_storage_backend().insert_chunks(docs) is called,
        Then the exact docs list reaches the adapter unmodified.
        """
        ### Given
        mock_storage = MagicMock(name="PostgresStorageBackend")
        docs = [{"chunk_id": "c1", "text": "Pell Grant eligibility"}]

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
            get_storage_backend().insert_chunks(docs)

        ### Then
        mock_storage.insert_chunks.assert_called_once_with(docs)


class TestSearchCharacterizationShould:
    """Scenario: get_retriever_backend().search keeps its 7-positional-arg contract."""

    def test_given_mongo_backend_when_search_called_then_delegate_receives_same_positional_args(
        self,
    ) -> None:
        """
        Scenario: Mongo search golden record.

        Given STORAGE_BACKEND=mongodb and a mocked Mongo retriever,
        When get_retriever_backend().search(...) is invoked with today's
        7-positional-argument order,
        Then the mocked retriever receives exactly those arguments and returns
        the same result object (no re-wrapping).
        """
        ### Given
        expected = [MagicMock(name="hit")]
        mock_retriever = MagicMock(name="MongoRetrieverBackend")
        mock_retriever.search.return_value = expected

        ### When
        with (
            patch("server.settings.settings.storage_backend", "mongodb"),
            patch("server.settings.settings.mongodb_uri", "mongodb://localhost:27017/db"),
            patch(
                "server.db.mongo.mongo_store.get_mongo_retriever",
                return_value=mock_retriever,
            ),
        ):
            actual = get_retriever_backend().search(
                RetrievalMethod.DENSE,
                "what is the deadline?",
                "exp-1",
                "all-MiniLM-L6-v2",
                "run-1",
                5,
                [0.1] * 384,
            )

        ### Then
        assert actual is expected
        mock_retriever.search.assert_called_once_with(
            RetrievalMethod.DENSE,
            "what is the deadline?",
            "exp-1",
            "all-MiniLM-L6-v2",
            "run-1",
            5,
            [0.1] * 384,
        )

    def test_given_postgres_backend_when_sparse_search_then_delegate_reaches_sparse_path(
        self,
    ) -> None:
        """
        Scenario: Postgres sparse-search golden record (Slice 35 dispatch).

        Given STORAGE_BACKEND=postgres and the real PostgresRetrieverBackend,
        When search() is called with RetrievalMethod.SPARSE,
        Then it dispatches to retriever_postgres.sparse_search with the same
        positional args as today (mirrors test_store_factory.py's sparse test —
        pinned here as the 49A golden record, not merely a duplicate check).
        """
        ### Given
        from server.db.postgres.postgres_store import get_postgres_retriever

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


class TestChunkDeleteCharacterizationShould:
    """Scenario: delete_chunks_for_experiment returns the adapter's count unchanged."""

    def test_given_mongo_backend_when_delete_called_then_adapter_count_passes_through(
        self,
    ) -> None:
        """
        Scenario: Mongo delete golden record.

        Given STORAGE_BACKEND=mongodb and a mocked adapter reporting 7 deleted,
        When get_storage_backend().delete_chunks_for_experiment(experiment_id) runs,
        Then the factory returns exactly 7 (no adjustment/aggregation added).
        """
        ### Given
        mock_storage = MagicMock(name="MongoStorageBackend")
        mock_storage.delete_chunks_for_experiment.return_value = 7

        ### When
        with (
            patch("server.settings.settings.storage_backend", "mongodb"),
            patch("server.settings.settings.mongodb_uri", "mongodb://localhost:27017/db"),
            patch("server.db.mongo.mongo_store.get_mongo_storage", return_value=mock_storage),
        ):
            actual = get_storage_backend().delete_chunks_for_experiment("exp-1")

        ### Then
        assert actual == 7
        mock_storage.delete_chunks_for_experiment.assert_called_once_with("exp-1")

    def test_given_postgres_backend_when_delete_called_then_adapter_count_passes_through(
        self,
    ) -> None:
        """
        Scenario: Postgres delete golden record.

        Given STORAGE_BACKEND=postgres and a mocked adapter reporting 3 deleted,
        When get_storage_backend().delete_chunks_for_experiment(experiment_id) runs,
        Then the factory returns exactly 3.
        """
        ### Given
        mock_storage = MagicMock(name="PostgresStorageBackend")
        mock_storage.delete_chunks_for_experiment.return_value = 3

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
            actual = get_storage_backend().delete_chunks_for_experiment("exp-1")

        ### Then
        assert actual == 3
        mock_storage.delete_chunks_for_experiment.assert_called_once_with("exp-1")


class TestDbStatsCharacterizationShould:
    """Scenario: get_experiment_db_stats keeps its exact key contract, per backend."""

    def test_given_mongo_backend_when_db_stats_requested_then_key_set_matches_contract(
        self,
    ) -> None:
        """
        Scenario: Mongo db-stats golden record.

        Given STORAGE_BACKEND=mongodb and a mocked adapter returning the golden payload,
        When get_storage_backend().get_experiment_db_stats(experiment_id) is called,
        Then the returned dict's key set matches _DB_STATS_KEYS exactly and the
        payload passes through unmodified.
        """
        ### Given
        golden = _golden_db_stats("mongodb")
        mock_storage = MagicMock(name="MongoStorageBackend")
        mock_storage.get_experiment_db_stats.return_value = golden

        ### When
        with (
            patch("server.settings.settings.storage_backend", "mongodb"),
            patch("server.settings.settings.mongodb_uri", "mongodb://localhost:27017/db"),
            patch("server.db.mongo.mongo_store.get_mongo_storage", return_value=mock_storage),
        ):
            actual = get_storage_backend().get_experiment_db_stats("exp-1")

        ### Then
        assert actual is golden
        assert frozenset(actual.keys()) == _DB_STATS_KEYS

    def test_given_postgres_backend_when_db_stats_requested_then_key_set_matches_contract(
        self,
    ) -> None:
        """
        Scenario: Postgres db-stats golden record.

        Given STORAGE_BACKEND=postgres and a mocked adapter returning the golden payload,
        When get_storage_backend().get_experiment_db_stats(experiment_id) is called,
        Then the returned dict's key set matches _DB_STATS_KEYS exactly.
        """
        ### Given
        golden = _golden_db_stats("postgres")
        mock_storage = MagicMock(name="PostgresStorageBackend")
        mock_storage.get_experiment_db_stats.return_value = golden

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
            actual = get_storage_backend().get_experiment_db_stats("exp-1")

        ### Then
        assert actual is golden
        assert frozenset(actual.keys()) == _DB_STATS_KEYS


class TestHealthzCharacterizationShould:
    """Scenario: storage_health() output shape is pinned, per backend."""

    def test_given_mongo_backend_ok_when_storage_health_then_shape_is_golden(
        self,
    ) -> None:
        """
        Scenario: Mongo /healthz golden record.

        Given STORAGE_BACKEND=mongodb, a successful ping, and storage_mode
        "mongodb-cloud",
        When storage_health() is called,
        Then the body is exactly {ok, storage_backend, storage_mode, mongodb}.
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
            actual = storage_health()

        ### Then
        assert actual == {
            "ok": True,
            "storage_backend": "mongodb",
            "storage_mode": "mongodb-cloud",
            "mongodb": "ok",
        }

    def test_given_postgres_backend_error_when_storage_health_then_shape_is_golden(
        self,
    ) -> None:
        """
        Scenario: Postgres /healthz golden record (unreachable).

        Given STORAGE_BACKEND=postgres and an unreachable pgvector,
        When storage_health() is called,
        Then ok is False, the postgres probe result is "error", and a
        remediation string is present (today's Session-mode / resume wording).
        """
        ### Given / When
        with (
            patch("server.core.guards.health_check.settings") as mock_settings,
            patch("server.core.guards.health_check.postgres_health_status", return_value="error"),
            patch(
                "server.core.guards.health_check.resolve_storage_mode",
                return_value="postgres-cloud",
            ),
        ):
            mock_settings.storage_backend = "postgres"
            actual = storage_health()

        ### Then
        assert actual["ok"] is False
        assert actual["storage_backend"] == "postgres"
        assert actual["storage_mode"] == "postgres-cloud"
        assert actual["postgres"] == "error"
        assert "Session-mode" in str(actual["remediation"])


class TestPreflightCharacterizationShould:
    """Scenario: validate_experiment_search_indexes preflight shape is pinned, per backend."""

    def test_given_mongo_backend_when_indexes_ready_then_preflight_is_satisfied(
        self,
    ) -> None:
        """
        Scenario: Mongo preflight golden record (satisfied).

        Given STORAGE_BACKEND=mongodb and a snapshot with all required indexes ready,
        When validate_experiment_search_indexes runs,
        Then the assessment is satisfied and the Atlas snapshot path is the one consulted.
        """
        ### Given
        config = _local_dense_config()
        ready = SearchIndexSnapshot(
            chunks_ready=frozenset({"vector_index_384"}),
            chunks_building=frozenset(),
            cluster_total=1,
            cluster_limit=3,
            unknown_count=0,
        )

        ### When
        with (
            patch("server.settings.settings.storage_backend", "mongodb"),
            patch(
                "server.core.guards.search_index_guard.collect_search_index_snapshot",
                return_value=ready,
            ) as atlas_snapshot,
        ):
            actual = validate_experiment_search_indexes(config)

        ### Then
        assert actual.is_satisfied
        atlas_snapshot.assert_called()

    def test_given_postgres_backend_when_catalog_ready_then_preflight_is_satisfied_without_atlas(
        self,
    ) -> None:
        """
        Scenario: Postgres preflight golden record (satisfied, no Atlas I/O).

        Given STORAGE_BACKEND=postgres, the vector extension present, and all
        HNSW/GIN catalog indexes present,
        When validate_experiment_search_indexes runs,
        Then the assessment is satisfied and the Atlas snapshot function is never called.
        """
        ### Given
        config = _local_dense_config()
        required = frozenset(
            {
                "chunks_embedding_384_hnsw",
                "chunks_embedding_1024_hnsw",
                "chunks_text_search_gin",
            }
        )
        ready = SearchIndexSnapshot(
            chunks_ready=required,
            chunks_building=frozenset(),
            cluster_total=3,
            cluster_limit=3,
            unknown_count=0,
        )

        ### When
        with (
            patch("server.settings.settings.storage_backend", "postgres"),
            patch(
                "server.core.guards.search_index_guard.postgres_vector_extension_present",
                return_value=True,
            ),
            patch(
                "server.core.guards.search_index_guard.collect_postgres_index_snapshot",
                return_value=ready,
            ),
            patch("server.core.guards.search_index_guard.collect_search_index_snapshot") as atlas,
        ):
            actual = validate_experiment_search_indexes(config)

        ### Then
        assert actual.is_satisfied
        atlas.assert_not_called()


class TestStorageModeCharacterizationShould:
    """Scenario: resolve_storage_mode's four-value output is pinned, per backend/location.

    Slice 49A relocates this branch behind VectorStore.storage_mode() — the
    returned string values (the observable contract callers/tests depend on)
    must not change.
    """

    @pytest.mark.parametrize(
        ("storage_backend", "mongodb_uri", "database_url", "expected_mode"),
        [
            ("mongodb", "mongodb+srv://user:pass@cluster.mongodb.net/db", "", "mongodb-cloud"),
            (
                "mongodb",
                "mongodb://localhost:27017/db?directConnection=true",
                "",
                "mongodb-local",
            ),
            (
                "postgres",
                "",
                "postgresql://postgres.proj:pw@aws-1.pooler.supabase.com:5432/postgres",
                "postgres-cloud",
            ),
            (
                "postgres",
                "",
                "postgresql://rag:rag@localhost:5433/rag_params_finder",
                "postgres-local",
            ),
        ],
    )
    def test_given_backend_and_uri_when_storage_mode_resolved_then_matches_golden_value(
        self,
        storage_backend: str,
        mongodb_uri: str,
        database_url: str,
        expected_mode: str,
    ) -> None:
        """
        Scenario: resolve_storage_mode four-value golden matrix.

        Given each (STORAGE_BACKEND, connection URI) pairing in today's system,
        When resolve_storage_mode() is called,
        Then the exact four-value token is returned.
        """
        ### Given / When
        from server.core.guards.health_check import resolve_storage_mode

        with (
            patch("server.settings.settings.storage_backend", storage_backend),
            patch("server.settings.settings.mongodb_uri", mongodb_uri),
            patch("server.settings.settings.database_url", database_url),
        ):
            actual = resolve_storage_mode()

        ### Then
        assert actual == expected_mode
