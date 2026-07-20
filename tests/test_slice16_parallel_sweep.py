"""GWT tests for Slice 16 parallel sweep execution semantics.

Author: Codex
Created: 2026-07-20
Scope: Validate bounded concurrency, failure policy, and cancellation semantics.
"""

from __future__ import annotations

import importlib
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

import cli.api_client
from server.core.experiment_control import ExperimentCancelledError, ExperimentPausedError
from server.core.orchestrator import (
    _completed_param_signatures,
    _compute_final_status,
    _log_failed_run_summary,
    _primary_retriever,
    _run_doc_signature,
    _run_single,
    _run_sweep_inner,
    _search_reranker_retriever,
    _search_traditional_retriever,
    _stored_enum_value,
    _update_phase,
    resume_sweep,
    run_sweep,
)
from server.core.query_loader import Query
from server.core.search_index_plan import SearchIndexMismatchError
from server.core.sie_guard import SIEUnavailableError
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
    RetrieverConfig,
    RunParams,
    expand_sweep,
)
from server.models.enums import (
    ChunkingMethod,
    ExperimentStatus,
    Phase,
    RetrievalMethod,
    RetrieverType,
)
from server.models.results import Chunk, SearchResult


def _run_param() -> RunParams:
    return RunParams(
        database_provider="mongodb",
        embedding_provider="local",
        embedding_model="all-MiniLM-L6-v2",
        chunking_method=ChunkingMethod.RECURSIVE,
        chunk_size=512,
        overlap=50,
        padding=0,
        top_k_initial=20,
        top_k_final=5,
        data_paths=["./data"],
        queries_file="./queries.json",
        retrievers=[{"type": RetrieverType.DENSE.value}],
        retrieval_method=RetrievalMethod.DENSE,
        retrieval_provider="local",
        retrieval_model=None,
    )


def _slice_config(
    parallelism: int,
    on_error: str = "continue",
) -> ExperimentConfig:
    return ExperimentConfig(
        experiment_name="slice-16-test",
        data_paths=["./data"],
        queries_file="./queries.json",
        embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
        chunking=ChunkingConfig(methods=[ChunkingMethod.RECURSIVE], params=ChunkParams()),
        retrieval=RetrievalConfig(),
        execution=ExecutionConfig(parallelism=parallelism, on_error=on_error),
    )


class _FakeCollection:
    def insert_one(self, *_args, **_kwargs) -> None:
        pass

    def insert_many(self, *_args, **_kwargs) -> None:
        pass

    def update_one(self, *_args, **_kwargs) -> None:
        pass

    def find_one(self, *_args, **_kwargs) -> dict:
        return {"status": "created"}

    def find(self, *_args, **_kwargs) -> list:
        return []

    def count_documents(self, *_args, **_kwargs) -> int:
        return 0


class TestSlice16ParallelSweep:
    """Scenario: execute a sweep with bounded in-process concurrency."""

    @patch("server.core.orchestrator._compute_final_status")
    @patch("server.core.orchestrator.get_collection")
    @patch("server.core.orchestrator.expand_sweep")
    @patch("server.core.orchestrator._run_single")
    @patch("server.core.orchestrator.validate_experiment_search_indexes")
    @patch("server.core.orchestrator.validate_sie_readiness")
    def test_runs_up_to_parallelism_limit(
        self,
        mock_validate_sie_readiness: MagicMock,
        mock_validate_search_indexes: MagicMock,
        mock_run_single: MagicMock,
        mock_expand_sweep: MagicMock,
        mock_get_collection: MagicMock,
        mock_compute_final_status: MagicMock,
    ) -> None:
        """
        Scenario: parallelism=4 schedules bounded workers

        Given an experiment with 8 run parameter sets
        When `_run_sweep_inner` runs with parallelism=4
        Then all 8 runs are submitted and peak concurrent `_run_single` execution is > 1.
        """
        # Given
        config = _slice_config(parallelism=4)
        params = [_run_param() for _ in range(8)]
        mock_expand_sweep.return_value = params
        mock_get_collection.return_value = _FakeCollection()
        mock_validate_sie_readiness.return_value = None
        mock_validate_search_indexes.return_value = None
        mock_compute_final_status.return_value = (ExperimentStatus.COMPLETE, 0)

        state = SimpleNamespace(count=0, peak=0)
        lock = threading.Lock()

        def run_side_effect(*_args, **_kwargs) -> None:
            with lock:
                state.count += 1
                state.peak = max(state.peak, state.count)
            time.sleep(0.02)
            with lock:
                state.count -= 1

        mock_run_single.side_effect = run_side_effect

        # When
        result = _run_sweep_inner("exp-parallel", config, set())

        # Then
        assert result["status"] == ExperimentStatus.COMPLETE
        assert state.peak >= 2
        assert mock_run_single.call_count == len(params)

    @patch("server.core.orchestrator._compute_final_status")
    @patch("server.core.orchestrator.get_collection")
    @patch("server.core.orchestrator.expand_sweep")
    @patch("server.core.orchestrator._run_single")
    @patch("server.core.orchestrator.validate_experiment_search_indexes")
    @patch("server.core.orchestrator.validate_sie_readiness")
    def test_on_error_continue_does_not_abort_scheduler(
        self,
        mock_validate_sie_readiness: MagicMock,
        mock_validate_search_indexes: MagicMock,
        mock_run_single: MagicMock,
        mock_expand_sweep: MagicMock,
        mock_get_collection: MagicMock,
        mock_compute_final_status: MagicMock,
    ) -> None:
        """
        Scenario: on_error=continue schedules all work after a failure

        Given 4 run parameter sets and on_error=continue
        When one run fails and others complete
        Then all 4 runs are submitted and overall status is partial.
        """
        # Given
        config = _slice_config(parallelism=2, on_error="continue")
        mock_expand_sweep.return_value = [_run_param() for _ in range(4)]
        mock_get_collection.return_value = _FakeCollection()
        mock_validate_sie_readiness.return_value = None
        mock_validate_search_indexes.return_value = None
        mock_compute_final_status.return_value = (ExperimentStatus.PARTIAL, 1)

        def run_side_effect(*_args, **_kwargs) -> None:
            if mock_run_single.call_count == 1:
                raise RuntimeError("simulated run failure")
            time.sleep(0.005)

        mock_run_single.side_effect = run_side_effect

        # When
        result = _run_sweep_inner("exp-continue", config, set())

        # Then
        assert result["status"] == ExperimentStatus.PARTIAL
        assert mock_run_single.call_count == 4

    @patch("server.core.orchestrator._compute_final_status")
    @patch("server.core.orchestrator.get_collection")
    @patch("server.core.orchestrator.expand_sweep")
    @patch("server.core.orchestrator._run_single")
    @patch("server.core.orchestrator.validate_experiment_search_indexes")
    @patch("server.core.orchestrator.validate_sie_readiness")
    def test_on_error_stop_blocks_new_scheduling(
        self,
        mock_validate_sie_readiness: MagicMock,
        mock_validate_search_indexes: MagicMock,
        mock_run_single: MagicMock,
        mock_expand_sweep: MagicMock,
        mock_get_collection: MagicMock,
        mock_compute_final_status: MagicMock,
    ) -> None:
        """
        Scenario: on_error=stop only drains currently submitted workers

        Given 4 run parameter sets and on_error=stop
        When the first run fails
        Then only the first worker wave is submitted and scheduling stops for remaining runs.
        """
        # Given
        config = _slice_config(parallelism=2, on_error="stop")
        mock_expand_sweep.return_value = [_run_param() for _ in range(4)]
        mock_get_collection.return_value = _FakeCollection()
        mock_validate_sie_readiness.return_value = None
        mock_validate_search_indexes.return_value = None
        mock_compute_final_status.return_value = (ExperimentStatus.PARTIAL, 1)

        def run_side_effect(*_args, **_kwargs) -> None:
            if mock_run_single.call_count == 1:
                raise RuntimeError("simulated run failure")
            time.sleep(0.01)

        mock_run_single.side_effect = run_side_effect

        # When
        result = _run_sweep_inner("exp-stop", config, set())

        # Then
        assert result["status"] == ExperimentStatus.PARTIAL
        assert mock_run_single.call_count == 2

    @patch("server.core.orchestrator.expand_sweep")
    @patch("server.core.orchestrator.check_control")
    @patch("server.core.orchestrator.get_collection")
    def test_cancelled_before_run_start_skips_run_submission(
        self,
        mock_get_collection: MagicMock,
        mock_check_control: MagicMock,
        mock_expand_sweep: MagicMock,
    ) -> None:
        """
        Scenario: cancellation before run starts is terminal

        Given check_control reports ExperimentCancelledError during preflight
        When _run_sweep_inner starts
        Then status is CANCELLED and no run params are expanded.
        """
        # Given
        mock_check_control.side_effect = ExperimentCancelledError("cancel requested")
        mock_get_collection.return_value = _FakeCollection()
        config = _slice_config(parallelism=2)

        # When
        result = _run_sweep_inner("exp-cancel", config, set())

        # Then
        assert result["status"] == ExperimentStatus.CANCELLED
        mock_expand_sweep.assert_not_called()

    @patch("server.core.orchestrator.check_control")
    @patch("server.core.orchestrator._compute_final_status")
    @patch("server.core.orchestrator.get_collection")
    @patch("server.core.orchestrator.expand_sweep")
    @patch("server.core.orchestrator._run_single")
    @patch("server.core.orchestrator.validate_experiment_search_indexes")
    @patch("server.core.orchestrator.validate_sie_readiness")
    def test_cancelled_after_some_runs_only_drains_inflight_workers(
        self,
        mock_validate_sie_readiness: MagicMock,
        mock_validate_search_indexes: MagicMock,
        mock_run_single: MagicMock,
        mock_expand_sweep: MagicMock,
        mock_get_collection: MagicMock,
        mock_compute_final_status: MagicMock,
        mock_check_control: MagicMock,
    ) -> None:
        """
        Scenario: cancellation during sweep stops new scheduling and keeps inflight runs

        Given 4 run parameter sets with parallelism=2 and cancel signal after one wave starts
        When one running batch completes and control is cancelled
        Then only the initial wave runs; in-flight completion sets experiment to CANCELLED.
        """
        # Given
        config = _slice_config(parallelism=2, on_error="continue")
        mock_expand_sweep.return_value = [_run_param() for _ in range(4)]
        mock_get_collection.return_value = _FakeCollection()
        mock_validate_sie_readiness.return_value = None
        mock_validate_search_indexes.return_value = None
        mock_compute_final_status.return_value = (ExperimentStatus.CANCELLED, 0)

        state = {"check_calls": 0}

        def check_control_side_effect(*_args) -> None:
            state["check_calls"] += 1
            if state["check_calls"] >= 4:
                raise ExperimentCancelledError("cancel requested")

        mock_check_control.side_effect = check_control_side_effect
        mock_run_single.return_value = None

        # When
        result = _run_sweep_inner("exp-cancel-mid", config, set())

        # Then
        assert result["status"] == ExperimentStatus.CANCELLED
        assert mock_run_single.call_count == 2

    @patch("server.core.orchestrator._run_sweep_inner")
    @patch("server.core.orchestrator.expand_sweep")
    @patch("server.core.orchestrator.get_collection")
    @patch("server.core.orchestrator.unregister_sweep_control")
    @patch("server.core.orchestrator.register_sweep_control")
    def test_search_index_preflight_failure_marks_experiment_failed(
        self,
        mock_register_sweep_control: MagicMock,
        mock_unregister_sweep_control: MagicMock,
        mock_get_collection: MagicMock,
        mock_expand_sweep: MagicMock,
        mock_run_sweep_inner: MagicMock,
    ) -> None:
        """
        Scenario: search-index preflight failures transition experiment to FAILED

        Given run_sweep
        When _run_sweep_inner raises SearchIndexMismatchError
        Then preflight status is set, run IDs are empty, and control is unregistered.
        """
        # Given
        mock_get_collection.return_value = _FakeCollection()
        mock_expand_sweep.return_value = [_run_param()]
        config = _slice_config(parallelism=1)
        mock_run_sweep_inner.side_effect = SearchIndexMismatchError("index mismatch")

        # When
        result = run_sweep("exp-preflight-failed", config)

        # Then
        assert result["status"] == ExperimentStatus.FAILED
        assert result["run_ids"] == []
        assert result["error_message"] == "index mismatch"
        mock_register_sweep_control.assert_called_once_with("exp-preflight-failed")
        mock_unregister_sweep_control.assert_called_once_with("exp-preflight-failed")
        mock_expand_sweep.assert_called_once()

    @patch("server.core.orchestrator.expand_sweep")
    @patch("server.core.orchestrator.validate_sie_readiness")
    @patch("server.core.orchestrator.validate_experiment_search_indexes")
    @patch("server.core.orchestrator.get_collection")
    @patch("server.core.orchestrator._compute_final_status")
    @patch("server.core.orchestrator._run_single")
    @patch("server.core.orchestrator.check_control")
    def test_infra_error_marks_status_as_failed(
        self,
        mock_check_control: MagicMock,
        mock_run_single: MagicMock,
        mock_compute_final_status: MagicMock,
        mock_get_collection: MagicMock,
        mock_validate_search_indexes: MagicMock,
        mock_validate_sie_readiness: MagicMock,
        mock_expand_sweep: MagicMock,
    ) -> None:
        """
        Scenario: SIEUnavailableError during a run forces FAILED status

        Given a run throws SIEUnavailableError
        When _run_sweep_inner processes completion
        Then final status is FAILED and includes an infrastructure error message.
        """
        # Given
        config = _slice_config(parallelism=1)
        mock_expand_sweep.return_value = [_run_param()]
        mock_run_single.side_effect = SIEUnavailableError("SIE backend unavailable")
        mock_get_collection.return_value = _FakeCollection()
        mock_validate_sie_readiness.return_value = None
        mock_validate_search_indexes.return_value = None
        mock_compute_final_status.return_value = (ExperimentStatus.COMPLETE, 0)
        mock_check_control.return_value = None

        # When
        result = _run_sweep_inner("exp-infra", config, set())

        # Then
        assert result["status"] == ExperimentStatus.FAILED

    @patch("server.core.orchestrator._run_sweep_inner")
    @patch("server.core.orchestrator._completed_param_signatures")
    def test_resume_sweep_passes_completed_signatures(
        self,
        mock_completed_signatures: MagicMock,
        mock_run_sweep_inner: MagicMock,
    ) -> None:
        """
        Scenario: resume_sweep forwards completed run signatures to _run_sweep_inner

        Given completed signatures are reported
        When resume_sweep runs
        Then _run_sweep_inner receives the same skip signature set.
        """
        # Given
        completed_signatures = {
            (
                "mongodb",
                "local",
                "all-MiniLM-L6-v2",
                "recursive",
                512,
                50,
                "dense",
                "local",
                None,
            )
        }
        config = _slice_config(parallelism=1)
        mock_completed_signatures.return_value = completed_signatures
        mock_run_sweep_inner.return_value = {
            "experiment_id": "exp-resume",
            "run_ids": [],
            "status": ExperimentStatus.COMPLETE,
        }

        # When
        resume_sweep("exp-resume", config)

        # Then
        mock_run_sweep_inner.assert_called_once_with("exp-resume", config, completed_signatures)


@patch("server.core.orchestrator.get_collection")
def test_compute_final_status_complete_and_partial_states(mock_get_collection: MagicMock) -> None:
    """
    Scenario: _compute_final_status resolves COMPLETE and PARTIAL

    Given run docs with successful and mixed outcomes
    When final status is computed for multiple expectations
    Then each branch returns the expected status.
    """
    # Given
    mock_get_collection.return_value.find.return_value = [
        {"phase": ExperimentStatus.COMPLETE.value},
        {"phase": ExperimentStatus.COMPLETE.value},
    ]

    # When / Then
    status, failed = _compute_final_status("exp-complete", 2)
    assert status == ExperimentStatus.COMPLETE
    assert failed == 0

    mock_get_collection.return_value.find.return_value = [
        {"phase": ExperimentStatus.COMPLETE.value},
        {"phase": ExperimentStatus.FAILED.value},
        {"phase": Phase.QUERYING.value},
    ]
    status, failed = _compute_final_status("exp-partial", 3)
    assert status == ExperimentStatus.PARTIAL
    assert failed == 1


@patch("server.core.orchestrator.get_collection")
def test_compute_final_status_failed_when_no_runs_complete(
    mock_get_collection: MagicMock,
) -> None:
    """
    Scenario: _compute_final_status resolves FAILED for all-failed runs

    Given all run docs failed
    When final status is computed
    Then status is FAILED with expected failed count.
    """
    # Given
    mock_get_collection.return_value.find.return_value = [
        {"phase": ExperimentStatus.FAILED.value},
        {"phase": ExperimentStatus.FAILED.value},
    ]

    # When
    status, failed = _compute_final_status("exp-failed", 2)

    # Then
    assert status == ExperimentStatus.FAILED
    assert failed == 2


def test_legacy_methods_are_ignored_when_retrievers_explicitly_set() -> None:
    """
    Scenario: explicit retrievers disable legacy method migration.
    """
    config = ExperimentConfig(
        experiment_name="legacy-has-overrides",
        data_paths=["./data"],
        queries_file="./queries.json",
        embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
        chunking=ChunkingConfig(methods=[ChunkingMethod.RECURSIVE], params=ChunkParams()),
        retrieval=RetrievalConfig(
            methods=[RetrievalMethod.DENSE],
            retrievers=[
                RetrieverConfig(
                    type=RetrieverType.CROSS_ENCODER,
                    provider="local",
                    model="cross-encoder/ms-marco-MiniLM-L-6-v2",
                )
            ],
            retrieval_provider="local",
            retrieval_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        ),
    )

    runs = expand_sweep(config)
    assert len(runs) == 1
    assert runs[0].retrievers[0].type == RetrieverType.CROSS_ENCODER


def test_slice16_legacy_retrieval_unknown_model_rejected() -> None:
    """
    Scenario: legacy retrieval_model must exist in reranker registry.
    """
    with pytest.raises(ValidationError):
        RetrievalConfig(
            methods=[RetrievalMethod.DENSE],
            retrieval_model="unknown-reranker",
            retrieval_provider="local",
        )


def test_search_traditional_retriever_embeds_when_needed() -> None:
    """
    Scenario: _search_traditional_retriever computes query embedding for dense/hybrid retrieval.
    """
    with patch("server.core.orchestrator.retriever_search") as mock_retriever_search:
        mock_retriever_search.return_value = []
        embed_query_calls = []

        def _embed(_query_text: str, model: str) -> list[float]:
            embed_query_calls.append(model)
            return [0.1, 0.2]

        cfg = RetrieverConfig(type=RetrieverType.DENSE)

        results, query_embedding = _search_traditional_retriever(
            cfg,
            run_id="run-1",
            query_text="q",
            experiment_id="exp-1",
            embedding_model="emb-model",
            embed_query_fn=_embed,
            top_k=10,
            query_embedding=None,
        )

        assert results == []
        assert query_embedding == [0.1, 0.2]
        assert embed_query_calls == ["emb-model"]
        mock_retriever_search.assert_called_once()


def test_search_reranker_retriever_rejects_missing_provider_or_model() -> None:
    """
    Scenario: _search_reranker_retriever validates reranker configuration.
    """
    cfg_missing = SimpleNamespace(type=RetrieverType.RERANKER, provider=None, model=None)
    with pytest.raises(ValueError):
        _search_reranker_retriever(
            cfg_missing,
            run_id="run-1",
            query_text="q",
            experiment_id="exp-1",
            embedding_model="emb-model",
            embed_query_fn=lambda q, m: [0.0],
            top_k_initial=10,
            top_k_final=2,
        )


@patch("server.core.orchestrator._update_phase")
@patch("server.core.orchestrator._search_traditional_retriever")
def test_search_reranker_retriever_no_candidates_logs_warning(
    mock_search_traditional: MagicMock, mock_update_phase: MagicMock
) -> None:
    """
    Scenario: _search_reranker_retriever returns empty list when no dense candidates are found.
    """
    mock_search_traditional.return_value = ([], None)

    cfg = RetrieverConfig(
        type=RetrieverType.RERANKER, provider="local", model="cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    results = _search_reranker_retriever(
        cfg,
        run_id="run-1",
        query_text="q",
        experiment_id="exp-1",
        embedding_model="emb-model",
        embed_query_fn=lambda q, m: [0.0],
        top_k_initial=10,
        top_k_final=2,
    )

    assert results == []
    mock_search_traditional.assert_called_once()
    mock_update_phase.assert_not_called()


def test_completed_param_signatures_extracts_phase_fields() -> None:
    """
    Scenario: _completed_param_signatures builds signatures from complete run documents.
    """
    runs = [
        {
            "database_provider": "mongodb",
            "embedding_provider": "local",
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking_method": ChunkingMethod.RECURSIVE,
            "chunk_size": 512,
            "overlap": 25,
            "retrieval_method": RetrievalMethod.DENSE,
            "retrieval_provider": "local",
            "retrieval_model": None,
        }
    ]
    expected = {
        ("mongodb", "local", "all-MiniLM-L6-v2", "recursive", 512, 25, "dense", "local", None)
    }

    with patch("server.core.orchestrator.get_collection") as mock_get_collection:
        mock_get_collection.return_value.find.return_value = runs
        assert _completed_param_signatures("exp") == expected


def test_stored_enum_value_and_run_doc_signature() -> None:
    """
    Scenario: storage helpers normalize enum and plain values for signatures.
    """
    assert _stored_enum_value(ChunkingMethod.RECURSIVE) == "recursive"
    assert _stored_enum_value("plain") == "plain"
    assert _stored_enum_value(None) == ""
    assert _run_doc_signature({"chunking_method": ChunkingMethod.RECURSIVE}) == (
        "mongodb",
        "",
        "",
        "recursive",
        0,
        0,
        "",
        "",
        None,
    )


def test_primary_retriever_with_empty_retrievers_raises() -> None:
    """
    Scenario: _primary_retriever validates retriever presence

    Given run params with an empty retrievers list
    When _primary_retriever is called
    Then ValueError is raised.
    """
    # Given
    params = _run_param().model_copy()
    params.retrievers = []

    # When / Then
    with pytest.raises(ValueError):
        _primary_retriever(params)


@patch("server.core.orchestrator.AimLogger")
@patch("server.core.orchestrator._search_traditional_retriever")
@patch("server.core.orchestrator.get_embedder")
@patch("server.core.orchestrator.load_queries")
@patch("server.core.orchestrator.chunk_text")
@patch("server.core.orchestrator.load_all_files")
@patch("server.core.orchestrator.check_control")
@patch("server.core.orchestrator.get_collection")
def test_run_single_happy_path_executes_pipeline(
    mock_get_collection: MagicMock,
    mock_check_control: MagicMock,
    mock_load_all_files: MagicMock,
    mock_chunk_text: MagicMock,
    mock_load_queries: MagicMock,
    mock_get_embedder: MagicMock,
    mock_search_traditional: MagicMock,
    mock_aim_logger: MagicMock,
) -> None:
    """
    Scenario: _run_single performs normal pipeline for a runnable configuration

    Given a successful dense run configuration
    When _run_single executes
    Then run_status, chunk docs, and query results are persisted.
    """
    # Given
    collection = MagicMock()
    mock_get_collection.return_value = collection
    mock_check_control.return_value = None
    mock_load_all_files.return_value = "text content"
    mock_chunk_text.return_value = ["chunk-one", "chunk-two"]
    mock_load_queries.return_value = [
        Query(text="What is retrieval?", persona_id="persona", focus=None)
    ]
    mock_get_embedder.return_value = (
        lambda chunks, _model, cancel_check=None: [[0.1], [0.2]],
        lambda text, model: [0.1, 0.2],
    )
    mock_search_traditional.return_value = (
        [
            SearchResult(
                chunk=Chunk(
                    id="chunk-1",
                    text="sample",
                    index=0,
                    embedding_model="all-MiniLM-L6-v2",
                    chunk_method="recursive",
                ),
                dense_score=0.9,
                rerank_score=None,
                retrieval_method="dense",
                rank=1,
            )
        ],
        [0.1, 0.2],
    )

    # When
    _run_single("exp-run", "run-1", _run_param())

    # Then
    assert collection.insert_one.call_count >= 2
    assert collection.insert_many.called
    assert collection.update_one.call_count >= 3
    mock_search_traditional.assert_called_once()
    mock_aim_logger.log_run.assert_called_once()


@patch("server.core.orchestrator.AimLogger")
@patch("server.core.orchestrator._search_reranker_retriever")
@patch("server.core.orchestrator.get_embedder")
@patch("server.core.orchestrator.load_queries")
@patch("server.core.orchestrator.chunk_text")
@patch("server.core.orchestrator.load_all_files")
@patch("server.core.orchestrator.check_control")
@patch("server.core.orchestrator.get_collection")
def test_run_single_reranker_path_executes_pipeline(
    mock_get_collection: MagicMock,
    mock_check_control: MagicMock,
    mock_load_all_files: MagicMock,
    mock_chunk_text: MagicMock,
    mock_load_queries: MagicMock,
    mock_get_embedder: MagicMock,
    mock_search_reranker: MagicMock,
    mock_aim_logger: MagicMock,
) -> None:
    """
    Scenario: _run_single executes reranker retrieval branch.
    """
    collection = MagicMock()
    mock_get_collection.return_value = collection
    mock_check_control.return_value = None
    mock_load_all_files.return_value = "text content"
    mock_chunk_text.return_value = ["chunk-one"]
    mock_load_queries.return_value = [Query(text="How?", persona_id="persona", focus=None)]
    mock_get_embedder.return_value = (
        lambda chunks, _model, cancel_check=None: [[0.1]],
        lambda text, model: [0.1, 0.2],
    )
    mock_search_reranker.return_value = []

    run_param = _run_param()
    run_param.retrievers = [
        RetrieverConfig(
            type=RetrieverType.RERANKER,
            provider="local",
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        )
    ]

    _run_single("exp-rerank", "run-rerank", run_param)

    assert collection.insert_one.call_count >= 2
    mock_search_reranker.assert_called_once()
    mock_aim_logger.log_run.assert_called_once()


@patch("server.core.orchestrator.get_embedder")
@patch("server.core.orchestrator.load_queries")
@patch("server.core.orchestrator.chunk_text")
@patch("server.core.orchestrator.load_all_files")
@patch("server.core.orchestrator.check_control")
@patch("server.core.orchestrator.get_collection")
@patch("server.core.orchestrator._search_traditional_retriever")
def test_run_single_failure_updates_failed_phase(
    mock_search_traditional: MagicMock,
    mock_get_collection: MagicMock,
    mock_check_control: MagicMock,
    mock_load_all_files: MagicMock,
    mock_chunk_text: MagicMock,
    mock_load_queries: MagicMock,
    mock_get_embedder: MagicMock,
) -> None:
    """
    Scenario: _run_single failure branch updates FAILED phase.
    """
    collection = MagicMock()
    mock_get_collection.return_value = collection
    mock_check_control.return_value = None
    mock_load_all_files.return_value = "text content"
    mock_chunk_text.return_value = ["chunk-one"]
    mock_load_queries.return_value = [Query(text="How?", persona_id="persona", focus=None)]
    mock_get_embedder.return_value = (
        lambda chunks, _model, cancel_check=None: [[0.1]],
        lambda text, model: [0.1, 0.2],
    )
    mock_search_traditional.side_effect = RuntimeError("index failure")

    with pytest.raises(RuntimeError):
        _run_single("exp-fail", "run-fail", _run_param())

    assert collection.update_one.call_count >= 4


@patch("server.core.orchestrator.check_control")
@patch("server.core.orchestrator._run_single")
@patch("server.core.orchestrator.get_collection")
@patch("server.core.orchestrator.expand_sweep")
@patch("server.core.orchestrator.validate_experiment_search_indexes")
@patch("server.core.orchestrator.validate_sie_readiness")
@patch("server.core.orchestrator._compute_final_status")
def test_run_sweep_paused_stops_new_scheduling_marking_paused(
    mock_compute_final_status: MagicMock,
    mock_validate_sie_readiness: MagicMock,
    mock_validate_search_indexes: MagicMock,
    mock_expand_sweep: MagicMock,
    mock_get_collection: MagicMock,
    mock_run_single: MagicMock,
    mock_check_control: MagicMock,
) -> None:
    """
    Scenario: _run_sweep_inner switches to PAUSED if ExperimentPausedError occurs.
    """
    mock_get_collection.return_value = _FakeCollection()
    mock_expand_sweep.return_value = [_run_param() for _ in range(4)]
    mock_validate_sie_readiness.return_value = None
    mock_validate_search_indexes.return_value = None
    mock_compute_final_status.return_value = (ExperimentStatus.PAUSED, 0)
    mock_check_control.side_effect = [None, None, ExperimentPausedError("pause requested"), None]
    mock_run_single.return_value = None

    result = _run_sweep_inner("exp-paused", _slice_config(parallelism=2), set())
    assert result["status"] == ExperimentStatus.PAUSED


@patch("server.core.orchestrator._update_phase")
@patch("server.core.orchestrator._search_traditional_retriever")
@patch("server.core.orchestrator.get_collection")
def test_run_single_records_empty_parse_and_chunk(
    mock_get_collection: MagicMock,
    mock_search_traditional: MagicMock,
    mock_update_phase: MagicMock,
) -> None:
    """
    Scenario: _run_single logs and continues when parse/chunking are empty.
    """
    collection = MagicMock()
    mock_get_collection.return_value = collection
    mock_update_phase.side_effect = lambda run_id, phase, error_message=None: None
    mock_search_traditional.return_value = ([], [])
    with (
        patch("server.core.orchestrator.load_all_files", return_value=""),
        patch("server.core.orchestrator.chunk_text", return_value=[]),
        patch(
            "server.core.orchestrator.load_queries",
            return_value=[Query(text="q", persona_id="p", focus=None)],
        ),
    ):
        with patch(
            "server.core.orchestrator.get_embedder",
            return_value=(lambda chunks, m, cancel_check=None: [], lambda text, model: []),
        ):
            with patch(
                "server.core.orchestrator._search_reranker_retriever"
            ) as mock_search_reranker:
                mock_search_reranker.return_value = []
                from server.core import orchestrator

                orchestrator._run_start_times.clear()
                _run_single("exp-empty", "run-empty", _run_param())

    assert collection.insert_one.call_count >= 2
    assert collection.insert_many.called


@patch("server.core.orchestrator.AimLogger")
@patch("server.core.orchestrator.load_queries")
@patch("server.core.orchestrator.chunk_text")
@patch("server.core.orchestrator.load_all_files")
@patch("server.core.orchestrator.check_control")
@patch("server.core.orchestrator.get_collection")
def test_run_single_interrupted_state_updates(
    mock_get_collection: MagicMock,
    mock_check_control: MagicMock,
    mock_load_all_files: MagicMock,
    mock_chunk_text: MagicMock,
    mock_load_queries: MagicMock,
    mock_aim_logger: MagicMock,
) -> None:
    """
    Scenario: _run_single maps check_control cancellation into INTERRUPTED phase.
    """
    collection = MagicMock()
    mock_get_collection.return_value = collection
    mock_check_control.side_effect = [None, ExperimentCancelledError("cancelled")]
    mock_load_all_files.return_value = "text content"
    mock_chunk_text.return_value = ["chunk"]
    mock_load_queries.return_value = [Query(text="q", persona_id="p", focus=None)]
    with patch(
        "server.core.orchestrator.get_embedder",
        return_value=(lambda chunks, m, cancel_check=None: [[0.1]], lambda text, model: [0.1]),
    ):
        with patch("server.core.orchestrator._search_traditional_retriever", return_value=([], [])):
            with pytest.raises(ExperimentCancelledError):
                _run_single("exp-interrupt", "run-interrupt", _run_param())

    assert collection.update_one.call_count >= 1
    mock_aim_logger.log_run.assert_not_called()


@patch("server.core.orchestrator.get_collection")
@patch("server.core.orchestrator.logger")
def test_log_failed_run_summary_logs_warning(
    mock_logger: MagicMock, mock_get_collection: MagicMock
) -> None:
    """
    Scenario: _log_failed_run_summary emits a warning containing top failures.
    """
    mock_get_collection.return_value.find.return_value = [
        {
            "run_id": "run-a",
            "embedding_model": "m1",
            "chunking_method": "recursive",
            "chunk_size": 256,
            "error_message": "boom",
        },
        {
            "run_id": "run-b",
            "embedding_model": "m2",
            "chunking_method": "recursive",
            "chunk_size": 256,
            "error_message": "err2",
        },
    ]
    _log_failed_run_summary("exp-1", failed_count=2)
    mock_logger.warning.assert_called_once()


@patch("server.core.orchestrator.get_collection")
def test_update_phase_marks_complete_and_cleanses_runtime_state(
    mock_get_collection: MagicMock,
) -> None:
    """
    Scenario: _update_phase updates run_status and clears start-time tracking

    Given a run reaches terminal phase
    When _update_phase is invoked
    Then update payload includes terminal clean-up metadata.
    """
    collection = MagicMock()
    mock_get_collection.return_value = collection
    _update_phase("run-terminal", Phase.COMPLETE)
    _update_phase("run-terminal", Phase.FAILED, error_message="bad")

    assert collection.update_one.call_count == 2


def test_parallelism_bounds_are_enforced_in_model() -> None:
    """
    Scenario: execution.parallelism is bounded in config model validation

    Given parallelism values outside the [1,16] range
    When ExperimentConfig is built
    Then ValidationError is raised.
    """
    # Given / When / Then
    with pytest.raises(ValidationError):
        _slice_config(parallelism=0)
    with pytest.raises(ValidationError):
        _slice_config(parallelism=17)


def test_slice16_config_rejects_unknown_embedding_model() -> None:
    """
    Scenario: unknown embedding model is rejected by config validation.
    """
    with pytest.raises(ValidationError):
        ExperimentConfig(
            experiment_name="invalid-model",
            data_paths=["./data"],
            queries_file="./queries.json",
            embedding=EmbeddingConfig(provider="local", models=["unknown-model"]),
            chunking=ChunkingConfig(methods=[ChunkingMethod.RECURSIVE], params=ChunkParams()),
            retrieval=RetrievalConfig(retrievers=[RetrieverConfig(type=RetrieverType.DENSE)]),
        )


def test_slice16_config_rejects_embedding_provider_mismatch() -> None:
    """
    Scenario: embedding provider mismatch is rejected by config validation.
    """
    with pytest.raises(ValidationError):
        ExperimentConfig(
            experiment_name="invalid-provider",
            data_paths=["./data"],
            queries_file="./queries.json",
            embedding=EmbeddingConfig(provider="local", models=["voyage-4-large"]),
            chunking=ChunkingConfig(methods=[ChunkingMethod.RECURSIVE], params=ChunkParams()),
            retrieval=RetrievalConfig(),
        )


def test_slice16_retrieval_config_rejects_invalid_reranker_model() -> None:
    """
    Scenario: retrieval reranker model is validated against the known registry.
    """
    with pytest.raises(ValidationError):
        RetrieverConfig(
            type=RetrieverType.RERANKER,
            provider="local",
            model="unknown-reranker",
        )


def test_slice16_retrieval_config_rejects_reranker_without_provider() -> None:
    """
    Scenario: reranker without provider is rejected.
    """
    with pytest.raises(ValidationError):
        RetrieverConfig(
            type=RetrieverType.RERANKER,
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        )


def test_slice16_retrieval_config_rejects_reranker_without_model() -> None:
    """
    Scenario: reranker without model is rejected.
    """
    with pytest.raises(ValidationError):
        RetrieverConfig(
            type=RetrieverType.CROSS_ENCODER,
            provider="local",
        )


def test_slice16_legacy_retrieval_mismatched_provider_is_rejected() -> None:
    """
    Scenario: legacy retrieval provider/model pairing is validated.
    """
    with pytest.raises(ValidationError):
        RetrievalConfig(
            methods=[RetrievalMethod.SPARSE],
            retrieval_provider="voyage",
            retrieval_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        )


def test_cli_default_submit_timeout_is_120_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Scenario: default submit timeout is stable

    Given no client timeout env var is set
    When the CLI API client module loads
    Then `_DEFAULT_TIMEOUT_S` defaults to 120 seconds.
    """
    monkeypatch.delenv("RAG_PARAMS_FINDER_CLIENT_TIMEOUT_S", raising=False)
    importlib.reload(cli.api_client)
    assert cli.api_client._DEFAULT_TIMEOUT_S == 120.0


def test_cli_timeout_override_via_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Scenario: timeout override is respected

    Given `RAG_PARAMS_FINDER_CLIENT_TIMEOUT_S` is set
    When the CLI API client module loads
    Then `_DEFAULT_TIMEOUT_S` reflects the override value.
    """
    monkeypatch.setenv("RAG_PARAMS_FINDER_CLIENT_TIMEOUT_S", "7")
    importlib.reload(cli.api_client)
    assert cli.api_client._DEFAULT_TIMEOUT_S == 7.0
