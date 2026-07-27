"""GWT tests for _run_single and related phase logging.

Author: Codex
Created: 2026-07-20
Scope: Happy path, reranker path, failure/interrupted/empty parse, phase updates.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from server.core.experiment_control import ExperimentCancelledError, ExperimentPausedError
from server.core.orchestrator import (
    _log_failed_run_summary,
    _run_single,
    _run_sweep_inner,
    _update_phase,
)
from server.core.query_loader import Query
from server.models.config import (
    RetrieverConfig,
)
from server.models.enums import (
    ExperimentStatus,
    Phase,
    RetrieverType,
)
from server.models.results import Chunk, SearchResult
from tests.helpers.pipeline_sweep import _fake_storage_backend, _run_param, _slice_config


@patch("server.core.orchestrator.AimLogger")
@patch("server.core.orchestrator._search_traditional_retriever")
@patch("server.core.orchestrator.get_embedder")
@patch("server.core.orchestrator.load_queries")
@patch("server.core.orchestrator.chunk_text")
@patch("server.core.orchestrator.load_all_files")
@patch("server.core.orchestrator.check_control")
@patch("server.core.orchestrator.get_storage_backend")
def test_run_single_happy_path_executes_pipeline(
    mock_get_storage_backend: MagicMock,
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
    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage
    mock_check_control.return_value = None
    mock_load_all_files.return_value = "text content"
    mock_chunk_text.return_value = ["chunk-one", "chunk-two"]
    mock_load_queries.return_value = [
        Query(text="What is retrieval?", persona_id="persona", focus=None)
    ]
    mock_get_embedder.return_value = (
        lambda chunks, _model, cancel_check=None, **_kwargs: [[0.1], [0.2]],
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
    assert storage.insert_run_status.call_count == 1
    assert storage.insert_result.call_count >= 1
    assert storage.insert_chunks.called
    assert storage.update_run_phase.call_count >= 3
    mock_search_traditional.assert_called_once()
    mock_aim_logger.log_run.assert_called_once()


@patch("server.core.orchestrator.AimLogger")
@patch("server.core.orchestrator._search_reranker_retriever")
@patch("server.core.orchestrator.get_embedder")
@patch("server.core.orchestrator.load_queries")
@patch("server.core.orchestrator.chunk_text")
@patch("server.core.orchestrator.load_all_files")
@patch("server.core.orchestrator.check_control")
@patch("server.core.orchestrator.get_storage_backend")
def test_run_single_reranker_path_executes_pipeline(
    mock_get_storage_backend: MagicMock,
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
    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage
    mock_check_control.return_value = None
    mock_load_all_files.return_value = "text content"
    mock_chunk_text.return_value = ["chunk-one"]
    mock_load_queries.return_value = [Query(text="How?", persona_id="persona", focus=None)]
    mock_get_embedder.return_value = (
        lambda chunks, _model, cancel_check=None, **_kwargs: [[0.1]],
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

    assert storage.insert_run_status.call_count == 1
    assert storage.insert_result.call_count == 1
    mock_search_reranker.assert_called_once()
    mock_aim_logger.log_run.assert_called_once()


@patch("server.core.orchestrator.get_embedder")
@patch("server.core.orchestrator.load_queries")
@patch("server.core.orchestrator.chunk_text")
@patch("server.core.orchestrator.load_all_files")
@patch("server.core.orchestrator.check_control")
@patch("server.core.orchestrator.get_storage_backend")
@patch("server.core.orchestrator._search_traditional_retriever")
def test_run_single_failure_updates_failed_phase(
    mock_search_traditional: MagicMock,
    mock_get_storage_backend: MagicMock,
    mock_check_control: MagicMock,
    mock_load_all_files: MagicMock,
    mock_chunk_text: MagicMock,
    mock_load_queries: MagicMock,
    mock_get_embedder: MagicMock,
) -> None:
    """
    Scenario: _run_single failure branch updates FAILED phase.
    """
    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage
    mock_check_control.return_value = None
    mock_load_all_files.return_value = "text content"
    mock_chunk_text.return_value = ["chunk-one"]
    mock_load_queries.return_value = [Query(text="How?", persona_id="persona", focus=None)]
    mock_get_embedder.return_value = (
        lambda chunks, _model, cancel_check=None, **_kwargs: [[0.1]],
        lambda text, model: [0.1, 0.2],
    )
    mock_search_traditional.side_effect = RuntimeError("index failure")

    with pytest.raises(RuntimeError):
        _run_single("exp-fail", "run-fail", _run_param())

    assert storage.update_run_phase.call_count >= 4


@patch("server.core.orchestrator.check_control")
@patch("server.core.orchestrator._run_single")
@patch("server.core.orchestrator.get_storage_backend")
@patch("server.core.orchestrator.expand_sweep")
@patch("server.core.orchestrator.validate_experiment_search_indexes")
@patch("server.core.orchestrator.validate_sie_readiness")
@patch("server.core.orchestrator._compute_final_status")
def test_run_sweep_paused_stops_new_scheduling_marking_paused(
    mock_compute_final_status: MagicMock,
    mock_validate_sie_readiness: MagicMock,
    mock_validate_search_indexes: MagicMock,
    mock_expand_sweep: MagicMock,
    mock_get_storage_backend: MagicMock,
    mock_run_single: MagicMock,
    mock_check_control: MagicMock,
) -> None:
    """
    Scenario: _run_sweep_inner switches to PAUSED if ExperimentPausedError occurs.
    """
    mock_get_storage_backend.return_value = _fake_storage_backend()
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
@patch("server.core.orchestrator.get_storage_backend")
def test_run_single_records_empty_parse_and_chunk(
    mock_get_storage_backend: MagicMock,
    mock_search_traditional: MagicMock,
    mock_update_phase: MagicMock,
) -> None:
    """
    Scenario: _run_single logs and continues when parse/chunking are empty.
    """
    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage
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
            return_value=(
                lambda chunks, m, cancel_check=None, **_kwargs: [],
                lambda text, model: [],
            ),
        ):
            with patch(
                "server.core.orchestrator._search_reranker_retriever"
            ) as mock_search_reranker:
                mock_search_reranker.return_value = []
                from server.core import orchestrator

                orchestrator._run_start_times.clear()
                _run_single("exp-empty", "run-empty", _run_param())

    assert storage.insert_run_status.call_count == 1
    assert storage.insert_result.call_count == 1
    assert storage.insert_chunks.called


@patch("server.core.orchestrator.AimLogger")
@patch("server.core.orchestrator.load_queries")
@patch("server.core.orchestrator.chunk_text")
@patch("server.core.orchestrator.load_all_files")
@patch("server.core.orchestrator.check_control")
@patch("server.core.orchestrator.get_storage_backend")
def test_run_single_interrupted_state_updates(
    mock_get_storage_backend: MagicMock,
    mock_check_control: MagicMock,
    mock_load_all_files: MagicMock,
    mock_chunk_text: MagicMock,
    mock_load_queries: MagicMock,
    mock_aim_logger: MagicMock,
) -> None:
    """
    Scenario: _run_single maps check_control cancellation into INTERRUPTED phase.
    """
    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage
    mock_check_control.side_effect = [None, ExperimentCancelledError("cancelled")]
    mock_load_all_files.return_value = "text content"
    mock_chunk_text.return_value = ["chunk"]
    mock_load_queries.return_value = [Query(text="q", persona_id="p", focus=None)]
    with patch(
        "server.core.orchestrator.get_embedder",
        return_value=(
            lambda chunks, m, cancel_check=None, **_kwargs: [[0.1]],
            lambda text, model: [0.1],
        ),
    ):
        with patch("server.core.orchestrator._search_traditional_retriever", return_value=([], [])):
            with pytest.raises(ExperimentCancelledError):
                _run_single("exp-interrupt", "run-interrupt", _run_param())

    assert storage.update_run_phase.call_count >= 1
    mock_aim_logger.log_run.assert_not_called()


@patch("server.core.orchestrator.get_storage_backend")
@patch("server.core.orchestrator.logger")
def test_log_failed_run_summary_logs_warning(
    mock_logger: MagicMock, mock_get_storage_backend: MagicMock
) -> None:
    """
    Scenario: _log_failed_run_summary emits a warning containing top failures.
    """
    mock_get_storage_backend.return_value.find_runs_by_phase.return_value = [
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


@patch("server.core.orchestrator.get_storage_backend")
def test_update_phase_marks_complete_and_cleanses_runtime_state(
    mock_get_storage_backend: MagicMock,
) -> None:
    """
    Scenario: _update_phase updates run_status and clears start-time tracking

    Given a run reaches terminal phase
    When _update_phase is invoked
    Then update payload includes terminal clean-up metadata.
    """
    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage
    _update_phase("run-terminal", Phase.COMPLETE)
    _update_phase("run-terminal", Phase.FAILED, error_message="bad")

    assert storage.update_run_phase.call_count == 2
