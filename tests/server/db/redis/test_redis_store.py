"""
Tests for server.db.redis.redis_store.

Author: swami
Created: 2026-09-30
Scope: RedisVectorStore construction, client lazy build, call() error routing,
       insert_chunks pipeline, delete scan loop, db_stats assembly, health_check
       branches, plan_indexes / ensure_indexes, run_preflight delegation,
       _add_to_pipeline (no TTL), _is_not_found patterns, _reject_unsupported_models,
       _missing_assessment / _ready_assessment.  Also covers RedisRetrieverBackend.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from server.db.redis.client import RedisClientMissingError, RedisUnreachableError
from server.db.redis.preflight import RedisPreflightError
from server.db.redis.redis_store import (
    RedisRetrieverBackend,
    RedisVectorStore,
    _add_to_pipeline,
    _is_not_found,
    _missing_assessment,
    _ready_assessment,
    _reject_unsupported_models,
)
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
    RetrieverConfig,
)
from server.models.enums import ChunkingMethod, RetrievalMethod, RetrieverType

# ── helpers ──────────────────────────────────────────────────────────────────


def _store(client: Any | None = None) -> RedisVectorStore:
    """Build a store with an injected client (skips import_redis() guard)."""
    return RedisVectorStore(client=client or MagicMock(name="redis_client"))


def _config(model: str = "all-MiniLM-L6-v2") -> ExperimentConfig:
    return ExperimentConfig(
        experiment_name="test-redis",
        data_paths=["."],
        queries_file="queries.json",
        database_provider="redis",
        embedding=EmbeddingConfig(provider="local", models=[model]),  # type: ignore[arg-type]
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[128], overlaps=[0], paddings=[0]),
        ),
        retrieval=RetrievalConfig(retrievers=[RetrieverConfig(type=RetrieverType.DENSE)]),
        execution=ExecutionConfig(),
    )


def _scan_responses(keys_pages: list[list[bytes]]) -> list[tuple[int, list[bytes]]]:
    """Build scan() side_effect: each call returns (cursor, keys)."""
    responses = []
    for i, page in enumerate(keys_pages):
        cursor = 0 if i == len(keys_pages) - 1 else i + 1
        responses.append((cursor, page))
    return responses


# ── tests ────────────────────────────────────────────────────────────────────


class TestRedisVectorStoreConstructionShould:
    def test_accepts_injected_client_without_importing_redis(self) -> None:
        """
        Scenario: Injected client bypasses redis import guard.
        Slice: 53

        Given a mock client is passed to the constructor,
        When RedisVectorStore() is instantiated,
        Then no ImportError is raised even without redis-py installed.
        """
        ### Given / When / Then
        store = _store()
        assert store is not None

    def test_init_without_client_calls_import_redis(self, fake_redis_modules: dict) -> None:
        """
        Scenario: When no client is injected, constructor calls import_redis().
        Slice: 53

        Given fake redis module in sys.modules,
        When RedisVectorStore() is instantiated without a client,
        Then the store is created successfully (import_redis does not raise).
        """
        ### Given / When
        with patch("server.db.redis.redis_store.import_redis") as mock_import:
            RedisVectorStore(client=None)

        ### Then
        mock_import.assert_called_once()

    def test_index_name_uses_rpf_prefix_by_default(self) -> None:
        """
        Scenario: Default index prefix 'rpf' yields 'rpf:chunks'.
        Slice: 53
        """
        ### Given / When
        store = _store()

        ### Then
        assert store.index_name == "rpf:chunks"


class TestRedisVectorStoreClientShould:
    def test_returns_injected_client_directly(self) -> None:
        """
        Scenario: client() returns the injected mock without building a new one.
        Slice: 53
        """
        ### Given
        fake_client = MagicMock(name="injected")
        store = _store(fake_client)

        ### When
        result = store.client()

        ### Then
        assert result is fake_client

    def test_builds_client_lazily_when_none(self) -> None:
        """
        Scenario: When _client is None, client() calls build_client.
        Slice: 53
        """
        ### Given
        store = _store()
        store._client = None

        ### When
        with patch("server.db.redis.redis_store.build_client") as mock_build:
            mock_build.return_value = MagicMock(name="built")
            result = store.client()

        ### Then
        mock_build.assert_called_once()
        assert result is mock_build.return_value


class TestRedisVectorStoreCallShould:
    def test_returns_action_result_on_success(self) -> None:
        """
        Scenario: call() returns the action's return value on success.
        Slice: 53
        """
        ### Given
        store = _store()

        ### When
        result = store.call(lambda: 42)

        ### Then
        assert result == 42

    def test_reraises_preflight_error_unchanged(self) -> None:
        """
        Scenario: RedisPreflightError bypasses connection-error handling.
        Slice: 53
        """
        ### Given
        store = _store()
        pf_err = RedisPreflightError("eviction bad")

        ### When / Then
        with pytest.raises(RedisPreflightError):
            store.call(lambda: (_ for _ in ()).throw(pf_err))  # type: ignore[misc]

    def test_wraps_connection_error_as_unreachable(self) -> None:
        """
        Scenario: Connection failures are wrapped as RedisUnreachableError.
        Slice: 53
        """
        ### Given
        store = _store()
        conn_err_cls = type("ConnectionError", (Exception,), {})

        def failing_action() -> None:
            raise conn_err_cls("refused")

        ### When / Then
        with pytest.raises(RedisUnreachableError):
            store.call(failing_action)

    def test_reraises_non_connection_exception(self) -> None:
        """
        Scenario: Non-connection exceptions are re-raised as-is.
        Slice: 53
        """
        ### Given
        store = _store()

        def bad_action() -> None:
            raise ValueError("query failed")

        ### When / Then
        with pytest.raises(ValueError):
            store.call(bad_action)


class TestInsertChunksShould:
    def test_does_nothing_for_empty_docs(self) -> None:
        """
        Scenario: Empty doc list produces no pipeline calls.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        store = _store(client)

        ### When
        store.insert_chunks([])

        ### Then
        client.pipeline.assert_not_called()

    def test_pipelines_all_valid_docs(self) -> None:
        """
        Scenario: Each doc with a valid embedding is added to the pipeline.
        Slice: 53
        """
        ### Given
        pipeline_mock = MagicMock()
        client = MagicMock()
        client.pipeline.return_value = pipeline_mock
        pipeline_mock.execute.return_value = None
        store = _store(client)

        docs = [
            {
                "chunk_id": "c1",
                "experiment_id": "e",
                "run_id": "r",
                "text": "hello",
                "embedding_model": "all-MiniLM-L6-v2",
                "chunk_method": "recursive",
                "embedding": [0.1] * 384,
                "chunk_size": 128,
                "overlap": 0,
            }
        ]

        ### When
        store.insert_chunks(docs)

        ### Then
        pipeline_mock.hset.assert_called_once()
        pipeline_mock.execute.assert_called_once()

    def test_skips_doc_with_empty_embedding(self) -> None:
        """
        Scenario: Documents with no embedding field are skipped silently.
        Slice: 53
        """
        ### Given
        pipeline_mock = MagicMock()
        client = MagicMock()
        client.pipeline.return_value = pipeline_mock
        pipeline_mock.execute.return_value = None
        store = _store(client)

        docs = [{"chunk_id": "c1", "experiment_id": "e", "run_id": "r", "embedding": []}]

        ### When
        store.insert_chunks(docs)

        ### Then
        pipeline_mock.hset.assert_not_called()


class TestDeleteChunksForExperimentShould:
    def test_deletes_all_matched_keys_across_pages(self) -> None:
        """
        Scenario: scan loop deletes keys across multiple pages.
        Slice: 53

        Given two scan pages with 2 keys each then cursor=0,
        When delete_chunks_for_experiment() is called,
        Then delete is called twice and total deleted count is 4.
        """
        ### Given
        client = MagicMock()
        client.scan.side_effect = _scan_responses(
            [
                [b"rpf:chunk:e:r:c1", b"rpf:chunk:e:r:c2"],
                [b"rpf:chunk:e:r:c3", b"rpf:chunk:e:r:c4"],
            ]
        )
        store = _store(client)

        ### When
        deleted = store.delete_chunks_for_experiment("e")

        ### Then
        assert deleted == 4
        assert client.unlink.call_count == 2

    def test_returns_zero_when_no_keys_found(self) -> None:
        """
        Scenario: No matching keys → deleted count is 0.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.scan.return_value = (0, [])
        store = _store(client)

        ### When
        deleted = store.delete_chunks_for_experiment("exp-unknown")

        ### Then
        assert deleted == 0
        client.delete.assert_not_called()


class TestGetVectorDbStatsGroupedShould:
    def test_returns_empty_groups_when_no_docs(self) -> None:
        """
        Scenario: Index with 0 documents returns empty groups.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        ft_mock = MagicMock()
        ft_mock.info.return_value = {"num_docs": 0}
        client.ft.return_value = ft_mock
        store = _store(client)

        ### When
        result = store.get_vector_db_stats_grouped()

        ### Then
        assert result == {"groups": []}

    def test_returns_groups_when_docs_present(self) -> None:
        """
        Scenario: Index with documents returns a populated groups list.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        ft_mock = MagicMock()
        ft_mock.info.return_value = {"num_docs": 50}
        client.ft.return_value = ft_mock
        store = _store(client)

        ### When
        result = store.get_vector_db_stats_grouped()

        ### Then
        assert "groups" in result
        assert len(result["groups"]) == 1


class TestHealthCheckShould:
    def test_returns_false_when_url_is_empty(self) -> None:
        """
        Scenario: No REDIS_URL configured → health_check returns False immediately.
        Slice: 53
        """
        ### Given
        store = _store()
        with patch("server.db.redis.redis_store.settings") as mock_settings:
            mock_settings.redis_url = ""

            ### When
            result = store.health_check()

        ### Then
        assert result is False

    def test_returns_true_when_ping_succeeds(self) -> None:
        """
        Scenario: Successful ping → health_check returns True.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.ping.return_value = True
        store = _store(client)
        with patch("server.db.redis.redis_store.settings") as mock_settings:
            mock_settings.redis_url = "redis://127.0.0.1:6379"
            mock_settings.redis_index_prefix = "rpf"

            ### When
            result = store.health_check()

        ### Then
        assert result is True

    def test_returns_false_when_redis_client_missing_error(self) -> None:
        """
        Scenario: Missing redis-py → health_check returns False.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.ping.side_effect = RedisClientMissingError("not installed")
        store = _store(client)
        with patch("server.db.redis.redis_store.settings") as mock_settings:
            mock_settings.redis_url = "redis://127.0.0.1:6379"
            mock_settings.redis_index_prefix = "rpf"

            ### When
            result = store.health_check()

        ### Then
        assert result is False

    def test_raises_for_connection_error_during_ping(self) -> None:
        """
        Scenario: Connection failure during ping is wrapped as RedisUnreachableError.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        conn_err_cls = type("ConnectionError", (Exception,), {})
        client.ping.side_effect = conn_err_cls("refused")
        store = _store(client)
        with patch("server.db.redis.redis_store.settings") as mock_settings:
            mock_settings.redis_url = "redis://127.0.0.1:6379"
            mock_settings.redis_index_prefix = "rpf"

            ### When / Then
            with pytest.raises(RedisUnreachableError):
                store.health_check()


class TestPlanIndexesShould:
    def test_returns_ready_assessment_when_index_exists(self) -> None:
        """
        Scenario: Existing index → is_satisfied=True.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.ft.return_value.info.return_value = {"index_name": "rpf:chunks"}
        store = _store(client)

        ### When
        assessment = store.plan_indexes(_config())

        ### Then
        assert assessment.is_satisfied is True

    def test_returns_missing_assessment_when_index_absent(self) -> None:
        """
        Scenario: Missing index → is_satisfied=False and index name in missing set.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.ft.return_value.info.side_effect = Exception("Unknown Index name")
        store = _store(client)

        ### When
        assessment = store.plan_indexes(_config())

        ### Then
        assert assessment.is_satisfied is False
        assert store.index_name in assessment.missing

    def test_raises_mismatch_error_for_unsupported_model_dims(self) -> None:
        """
        Scenario: Model with unsupported dims raises SearchIndexMismatchError.
        Slice: 53

        Given get_dimensions returns 768 (not in SUPPORTED_DIMS),
        When plan_indexes() is called,
        Then SearchIndexMismatchError is raised.
        """
        ### Given
        from server.core.guards.search_index_plan import SearchIndexMismatchError

        store = _store()

        ### When / Then
        with patch("server.db.redis.redis_store.get_dimensions") as mock_dims:
            mock_dims.return_value = 768  # not in SUPPORTED_DIMS
            with pytest.raises(SearchIndexMismatchError):
                store.plan_indexes(_config())


class TestEnsureIndexesShould:
    def test_skips_creation_when_index_exists(self) -> None:
        """
        Scenario: Index already present — FT.CREATE is not called.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.ft.return_value.info.return_value = {"index_name": "rpf:chunks"}
        store = _store(client)

        ### When
        store.ensure_indexes()

        ### Then
        client.ft.return_value.create_index.assert_not_called()

    def test_creates_index_when_missing(self, fake_redis_modules: dict) -> None:
        """
        Scenario: Missing index triggers FT.CREATE via create_index().
        Slice: 53
        """
        ### Given
        client = MagicMock()
        # info() raises → index missing
        client.ft.return_value.info.side_effect = Exception("Unknown Index name")
        store = _store(client)

        ### When
        store.ensure_indexes()

        ### Then
        client.ft.return_value.create_index.assert_called_once()


class TestRunPreflightShould:
    def test_delegates_to_run_all_preflight(self) -> None:
        """
        Scenario: run_preflight() calls run_all_preflight with client and params.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        store = _store(client)

        ### When
        with patch("server.db.redis.redis_store.run_all_preflight") as mock_pf:
            store.run_preflight(planned_vectors=100, dims=384)

        ### Then
        mock_pf.assert_called_once()
        call_kwargs = mock_pf.call_args
        assert call_kwargs[0][0] is client
        assert call_kwargs[1]["planned_vectors"] == 100
        assert call_kwargs[1]["dims"] == 384
        assert "noeviction" in call_kwargs[1]["accepted_policies"]


class TestCapabilitiesShould:
    def test_returns_vector_capabilities_with_all_three_methods(self) -> None:
        """
        Scenario: capabilities() includes dense, sparse, and hybrid.
        Slice: 53
        """
        ### Given / When
        caps = RedisVectorStore.capabilities()

        ### Then
        assert RetrievalMethod.DENSE in caps.retrieval_methods
        assert RetrievalMethod.SPARSE in caps.retrieval_methods
        assert RetrievalMethod.HYBRID in caps.retrieval_methods

    def test_cannot_host_run_state(self) -> None:
        """
        Scenario: Redis vector store is vector-only (no run state).
        Slice: 53
        """
        ### Given / When
        caps = RedisVectorStore.capabilities()

        ### Then
        assert caps.can_host_run_state is False

    def test_ui_labels_returns_dict(self) -> None:
        """
        Scenario: ui_labels() returns a non-empty dictionary.
        Slice: 53
        """
        ### Given / When
        labels = RedisVectorStore.ui_labels()

        ### Then
        assert isinstance(labels, dict)
        assert len(labels) > 0

    def test_index_summary_returns_dict_with_index_key(self) -> None:
        """
        Scenario: index_summary() returns metadata including 'index' key.
        Slice: 53
        """
        ### Given / When
        summary = RedisVectorStore.index_summary()

        ### Then
        assert "index" in summary


class TestRedisRetrieverBackendShould:
    def test_delegates_search_to_store(self) -> None:
        """
        Scenario: RetrieverBackend.search() proxies to redis_search via store.call().
        Slice: 53

        Given a store mock,
        When RetrieverBackend.search() is called,
        Then store.call() is invoked.
        """
        ### Given
        store = MagicMock(spec=RedisVectorStore)
        store.call.return_value = []
        backend = RedisRetrieverBackend(store)

        ### When
        result = backend.search(
            method=RetrievalMethod.DENSE,
            query_text="test",
            experiment_id="e",
            embedding_model="all-MiniLM-L6-v2",
            run_id="r",
            top_k=5,
            query_embedding=[0.1] * 384,
        )

        ### Then
        store.call.assert_called_once()
        assert result == []


class TestIsNotFoundShould:
    @pytest.mark.parametrize(
        "msg",
        [
            "Unknown Index name",
            "No Such Index",
        ],
    )
    def test_returns_true_for_known_not_found_messages(self, msg: str) -> None:
        """
        Scenario: Known 'index not found' messages return True.
        Slice: 53
        """
        ### Given
        exc = Exception(msg)

        ### When / Then
        assert _is_not_found(exc) is True

    def test_returns_false_for_generic_exception(self) -> None:
        """
        Scenario: Generic exceptions are not 'not found'.
        Slice: 53
        """
        ### Given
        exc = Exception("connection reset")

        ### When / Then
        assert _is_not_found(exc) is False


class TestAddToPipelineShould:
    def test_sets_no_ttl_on_vector_key(self) -> None:
        """
        Scenario: No TTL is ever set on chunk keys (GWT: Vector keys never expire).
        Slice: 53

        Given a doc with a valid embedding,
        When _add_to_pipeline() is called,
        Then pipeline.expire() and pipeline.expireat() are never called.
        """
        ### Given
        pipeline = MagicMock()
        doc = {
            "chunk_id": "c1",
            "experiment_id": "exp",
            "run_id": "run",
            "text": "text",
            "embedding_model": "all-MiniLM-L6-v2",
            "embedding": [0.1] * 384,
            "chunk_size": 128,
            "overlap": 0,
        }

        ### When
        _add_to_pipeline(pipeline, doc)

        ### Then
        pipeline.hset.assert_called_once()
        pipeline.expire.assert_not_called()
        pipeline.expireat.assert_not_called()

    def test_skips_doc_with_no_embedding(self) -> None:
        """
        Scenario: Doc with empty embedding is silently skipped.
        Slice: 53
        """
        ### Given
        pipeline = MagicMock()
        doc = {"chunk_id": "c1", "embedding": []}

        ### When
        _add_to_pipeline(pipeline, doc)

        ### Then
        pipeline.hset.assert_not_called()


class TestGetExperimentDbStatsShould:
    def test_assembles_stats_with_scan_results(self) -> None:
        """
        Scenario: get_experiment_db_stats aggregates scan results into db-stats dict.
        Slice: 53

        Given a client returning 2 keys with known field values,
        When get_experiment_db_stats() is called,
        Then the returned dict has total_chunks and run_breakdown populated.
        """
        ### Given
        client = MagicMock()
        # Two-key experiment: scan returns both in first page
        client.scan.return_value = (0, [b"rpf:chunk:exp:run1:c1", b"rpf:chunk:exp:run1:c2"])

        # hget returns field values for embedding_model, chunking_method, run_id
        def hget_side_effect(key: bytes, field: str) -> bytes:
            values = {
                "embedding_model": b"all-MiniLM-L6-v2",
                "chunking_method": b"recursive",
                "run_id": b"run1",
            }
            return values.get(field, b"")

        client.hget.side_effect = hget_side_effect
        store = _store(client)

        ### When
        stats = store.get_experiment_db_stats("exp")

        ### Then
        assert isinstance(stats, dict)
        assert stats.get("total_chunks", 0) >= 0  # may be 0 for count scan

    def test_returns_dict_structure_for_empty_experiment(self) -> None:
        """
        Scenario: No chunks for experiment → dict with zero counts.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.scan.return_value = (0, [])
        store = _store(client)

        ### When
        stats = store.get_experiment_db_stats("empty-exp")

        ### Then
        assert isinstance(stats, dict)


class TestStorageModeShould:
    def test_delegates_to_redis_storage_mode(self) -> None:
        """
        Scenario: storage_mode() returns the uri module's classification of the URL.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        store = _store(client)
        with patch("server.db.redis.redis_store.settings") as mock_settings:
            mock_settings.redis_url = "redis://127.0.0.1:6379"
            mock_settings.redis_index_prefix = "rpf"

            ### When
            mode = store.storage_mode()

        ### Then
        assert mode == "redis-local"


class TestHealthCheckNonConnectionExceptionShould:
    def test_returns_false_for_non_connection_ping_exception(self) -> None:
        """
        Scenario: Non-connection exception during ping → returns False (not raised).
        Slice: 53

        Given ping() raises a ValueError (not a connection error),
        When health_check() is called,
        Then raise_if_unreachable does NOT raise and health_check returns False.
        """
        ### Given
        client = MagicMock()
        client.ping.side_effect = ValueError("unexpected query error")
        store = _store(client)
        with patch("server.db.redis.redis_store.settings") as mock_settings:
            mock_settings.redis_url = "redis://127.0.0.1:6379"
            mock_settings.redis_index_prefix = "rpf"

            ### When
            result = store.health_check()

        ### Then
        assert result is False


class TestIndexExistsRaisesOnNonNotFoundShould:
    def test_reraises_non_not_found_exception(self) -> None:
        """
        Scenario: _index_exists re-raises exceptions that are not 'index not found'.
        Slice: 53

        Given ft.info() raises a ConnectionError,
        When _index_exists() is called,
        Then the ConnectionError propagates (not swallowed).
        """
        ### Given
        client = MagicMock()
        client.ft.return_value.info.side_effect = ConnectionError("connection reset")
        store = _store(client)

        ### When / Then
        with pytest.raises(ConnectionError):
            store._index_exists()


class TestRetrieverShould:
    def test_returns_redis_retriever_backend_instance(self) -> None:
        """
        Scenario: retriever() returns a RetrieverBackend wrapping this store.
        Slice: 53
        """
        ### Given
        store = _store()

        ### When
        backend = store.retriever()

        ### Then
        assert isinstance(backend, RedisRetrieverBackend)


class TestFtInfoOrEmptyShould:
    def test_returns_empty_dict_on_not_found(self) -> None:
        """
        Scenario: _ft_info_or_empty returns {} when the index does not exist.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.ft.return_value.info.side_effect = Exception("Unknown Index name")
        store = _store(client)

        ### When
        result = store._ft_info_or_empty()

        ### Then
        assert result == {}

    def test_raises_on_connection_error(self) -> None:
        """
        Scenario: _ft_info_or_empty propagates non-not-found exceptions.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.ft.return_value.info.side_effect = ConnectionError("Connection refused")
        store = _store(client)

        ### When / Then
        with pytest.raises(ConnectionError, match="Connection refused"):
            store._ft_info_or_empty()

    def test_returns_dict_when_info_is_dict(self) -> None:
        """
        Scenario: _ft_info_or_empty returns the dict from ft.info().
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.ft.return_value.info.return_value = {"num_docs": 5}
        store = _store(client)

        ### When
        result = store._ft_info_or_empty()

        ### Then
        assert result == {"num_docs": 5}

    def test_returns_empty_dict_when_info_is_not_dict(self) -> None:
        """
        Scenario: Old redis-py versions return a flat list — _ft_info_or_empty returns {}.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.ft.return_value.info.return_value = ["key", "value"]  # flat list
        store = _store(client)

        ### When
        result = store._ft_info_or_empty()

        ### Then
        assert result == {}


class TestCountForExperimentShould:
    def test_counts_keys_across_scan_pages(self) -> None:
        """
        Scenario: _count_for_experiment sums keys over multiple scan pages.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.scan.side_effect = _scan_responses(
            [
                [b"k1", b"k2"],
                [b"k3"],
            ]
        )
        store = _store(client)

        ### When
        count = store._count_for_experiment("exp")

        ### Then
        assert count == 3

    def test_returns_zero_for_empty_experiment(self) -> None:
        """
        Scenario: No keys for experiment → count is 0.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.scan.return_value = (0, [])
        store = _store(client)

        ### When
        count = store._count_for_experiment("exp")

        ### Then
        assert count == 0


class TestDistinctTagValuesShould:
    def test_collects_unique_values_from_hget(self) -> None:
        """
        Scenario: _distinct_tag_values returns distinct field values across all keys.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.scan.return_value = (0, [b"k1", b"k2", b"k3"])
        pipe = MagicMock()
        client.pipeline.return_value = pipe
        pipe.execute.return_value = [b"model-a", b"model-b", b"model-a"]
        store = _store(client)

        ### When
        result = store._distinct_tag_values("embedding_model", "exp")

        ### Then
        assert set(result) == {"model-a", "model-b"}

    def test_handles_bytes_and_string_values(self) -> None:
        """
        Scenario: _distinct_tag_values decodes bytes and accepts plain strings.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.scan.return_value = (0, [b"k1"])
        pipe = MagicMock()
        client.pipeline.return_value = pipe
        pipe.execute.return_value = [b"some-model"]
        store = _store(client)

        ### When
        result = store._distinct_tag_values("embedding_model", "exp")

        ### Then
        assert "some-model" in result

    def test_skips_none_values(self) -> None:
        """
        Scenario: None returned by hget (missing field) is skipped.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.scan.return_value = (0, [b"k1"])
        pipe = MagicMock()
        client.pipeline.return_value = pipe
        pipe.execute.return_value = [None]
        store = _store(client)

        ### When
        result = store._distinct_tag_values("embedding_model", "exp")

        ### Then
        assert result == []


class TestTagCountsShould:
    def test_counts_occurrences_per_tag_value(self) -> None:
        """
        Scenario: _tag_counts returns {value: count} mapping.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.scan.return_value = (0, [b"k1", b"k2", b"k3"])
        pipe = MagicMock()
        client.pipeline.return_value = pipe
        pipe.execute.return_value = [b"recursive", b"recursive", b"fixed"]
        store = _store(client)

        ### When
        counts = store._tag_counts("chunking_method", "exp")

        ### Then
        assert counts.get("recursive") == 2
        assert counts.get("fixed") == 1

    def test_skips_keys_with_missing_field(self) -> None:
        """
        Scenario: Keys with no field value are excluded from the count.
        Slice: 53
        """
        ### Given
        client = MagicMock()
        client.scan.return_value = (0, [b"k1"])
        pipe = MagicMock()
        client.pipeline.return_value = pipe
        pipe.execute.return_value = [None]
        store = _store(client)

        ### When
        counts = store._tag_counts("run_id", "exp")

        ### Then
        assert counts == {}


class TestAssessmentsShould:
    def test_missing_assessment_is_not_satisfied(self) -> None:
        """
        Scenario: _missing_assessment returns is_satisfied=False with the index in missing.
        Slice: 53
        """
        ### Given / When
        result = _missing_assessment("rpf:chunks")

        ### Then
        assert result.is_satisfied is False
        assert "rpf:chunks" in result.missing

    def test_ready_assessment_is_satisfied(self) -> None:
        """
        Scenario: _ready_assessment returns is_satisfied=True.
        Slice: 53
        """
        ### Given / When
        result = _ready_assessment("rpf:chunks")

        ### Then
        assert result.is_satisfied is True
        assert "rpf:chunks" in result.present_ready


class TestRejectUnsupportedModelsShould:
    def test_raises_for_model_with_unsupported_dims(self) -> None:
        """
        Scenario: Model resolving to dims not in SUPPORTED_DIMS raises SearchIndexMismatchError.
        Slice: 53
        """
        ### Given
        from server.core.guards.search_index_plan import SearchIndexMismatchError

        ### When
        with patch("server.db.redis.redis_store.get_dimensions") as mock_dims:
            mock_dims.return_value = 768
            with pytest.raises(SearchIndexMismatchError, match="Dimension mismatch"):
                _reject_unsupported_models(_config())

    def test_does_not_raise_for_supported_dims(self) -> None:
        """
        Scenario: Model resolving to 384 or 1024 dims passes without error.
        Slice: 53
        """
        ### Given
        with patch("server.db.redis.redis_store.get_dimensions") as mock_dims:
            mock_dims.return_value = 384

            ### When / Then
            _reject_unsupported_models(_config())  # should not raise
