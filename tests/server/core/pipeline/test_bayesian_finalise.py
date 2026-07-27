"""GWT tests for Bayesian finalise / status / trial-log helpers.

Author: Codex
Created: 2026-07-20
Scope: Bayesian experiment finalisation, status resolution, trial log, AT-01..AT-14.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from server.core.orchestrator import (
    _compute_final_status,
    _finalise_bayesian_experiment,
    _log_bayesian_summary,
    _resolve_bayesian_n_trials,
    _run_best_trial_payload,
)
from server.models.enums import (
    ExperimentStatus,
    Phase,
)
from tests.helpers.pipeline_sweep import _fake_storage_backend, _slice_config


@patch("server.core.orchestrator._count_failed_runs", return_value=0)
@patch("server.core.orchestrator._log_bayesian_summary")
@patch("server.core.orchestrator.get_storage_backend")
def test_finalise_bayesian_experiment_persists_summary(
    mock_get_storage_backend: MagicMock,
    mock_log_summary: MagicMock,
    mock_count_failed_runs: MagicMock,
) -> None:
    """
    Scenario: _finalise_bayesian_experiment stores Bayesian metadata in experiment docs

    Given bayesian completion with successful runs only
    When finalization runs
    Then run_count, grid_equivalent_count, and bayesian_summary are persisted.
    """
    config = _slice_config(parallelism=1)
    config.execution.search_strategy = "bayesian"
    config.execution.bayesian.n_trials = 4
    config.chunking.params.chunk_sizes = [128, 256, 512]
    config.chunking.params.overlaps = [0, 50]

    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage

    best_trial = {
        "query_avg_score": 0.82,
        "chunk_size": 256,
        "overlap": 50,
        "embedding_model": "all-MiniLM-L6-v2",
        "retrieval_method": "dense",
        "retrieval_type": "dense",
    }

    final_status, failed_count = _finalise_bayesian_experiment(
        experiment_id="exp-bayesian",
        config=config,
        planned_trials=4,
        cancelled=False,
        paused=False,
        run_ids=["run-1", "run-2", "run-3", "run-4"],
        attempted_trials=4,
        discarded_trials=0,
        best_trial=best_trial,
        infrastructure_error=None,
    )

    assert final_status == ExperimentStatus.COMPLETE
    assert failed_count == 0
    # _count_failed_runs is only used for cancelled/paused paths, not this branch.
    mock_count_failed_runs.assert_not_called()

    # Validate experiment document persisted fields
    update_call = storage.update_experiment.call_args.args[1]
    assert update_call["status"] == ExperimentStatus.COMPLETE
    assert update_call["run_count"] == 4
    assert update_call["failed_count"] == 0
    assert update_call["grid_equivalent_count"] == 6

    bayesian_summary = update_call["bayesian_summary"]
    assert bayesian_summary["best_query_avg_score"] == 0.82
    assert bayesian_summary["best_chunk_size"] == 256
    assert bayesian_summary["best_overlap"] == 50
    assert bayesian_summary["grid_equivalent_count"] == 6
    assert bayesian_summary["planned_trials"] == 4
    assert bayesian_summary["attempted_trials"] == 4
    assert bayesian_summary["discarded_trials"] == 0
    mock_log_summary.assert_called_once()


@patch("server.core.orchestrator._log_bayesian_summary")
@patch("server.core.orchestrator.get_storage_backend")
def test_finalise_bayesian_experiment_promotes_no_failure_partial_to_complete(
    mock_get_storage_backend: MagicMock,
    mock_log_summary: MagicMock,
) -> None:
    """
    Scenario: _finalise_bayesian_experiment treats a partial Bayesian run with no
    failures as complete

    Given attempted Bayesian trials are fewer than planned and none failed
    When finalization runs
    Then status is complete and the summary preserves the discarded/not-started split
    in summary metadata.
    """
    config = _slice_config(parallelism=1)
    config.execution.search_strategy = "bayesian"
    config.execution.bayesian.n_trials = 5
    config.chunking.params.chunk_sizes = [128, 256, 512]
    config.chunking.params.overlaps = [0, 50]

    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage

    final_status, failed_count = _finalise_bayesian_experiment(
        experiment_id="exp-bayesian-promoted",
        config=config,
        planned_trials=5,
        cancelled=False,
        paused=False,
        run_ids=["run-1", "run-2", "run-3"],
        attempted_trials=3,
        discarded_trials=2,
        best_trial=None,
        infrastructure_error=None,
    )

    assert final_status == ExperimentStatus.COMPLETE
    assert failed_count == 0

    update_call = storage.update_experiment.call_args.args[1]
    assert update_call["status"] == ExperimentStatus.COMPLETE
    assert update_call["run_count"] == 5
    assert update_call["failed_count"] == 0
    assert update_call["grid_equivalent_count"] == 6
    assert update_call["bayesian_summary"]["attempted_trials"] == 3
    assert update_call["bayesian_summary"]["discarded_trials"] == 2
    assert update_call["bayesian_summary"]["planned_trials"] == 5
    mock_log_summary.assert_not_called()


@patch("server.core.orchestrator.get_storage_backend")
def test_compute_final_status_complete_and_partial_states(
    mock_get_storage_backend: MagicMock,
) -> None:
    """
    Scenario: _compute_final_status resolves COMPLETE and PARTIAL

    Given run docs with successful and mixed outcomes
    When final status is computed for multiple expectations
    Then each branch returns the expected status.
    """
    # Given
    mock_get_storage_backend.return_value.find_run_statuses.return_value = [
        {"phase": ExperimentStatus.COMPLETE.value},
        {"phase": ExperimentStatus.COMPLETE.value},
    ]

    # When / Then
    status, failed = _compute_final_status("exp-complete", 2)
    assert status == ExperimentStatus.COMPLETE
    assert failed == 0

    mock_get_storage_backend.return_value.find_run_statuses.return_value = [
        {"phase": ExperimentStatus.COMPLETE.value},
        {"phase": ExperimentStatus.FAILED.value},
        {"phase": Phase.QUERYING.value},
    ]
    status, failed = _compute_final_status("exp-partial", 3)
    assert status == ExperimentStatus.PARTIAL
    assert failed == 1


@patch("server.core.orchestrator.get_storage_backend")
def test_compute_final_status_failed_when_no_runs_complete(
    mock_get_storage_backend: MagicMock,
) -> None:
    """
    Scenario: _compute_final_status resolves FAILED for all-failed runs

    Given all run docs failed
    When final status is computed
    Then status is FAILED with expected failed count.
    """
    # Given
    mock_get_storage_backend.return_value.find_run_statuses.return_value = [
        {"phase": ExperimentStatus.FAILED.value},
        {"phase": ExperimentStatus.FAILED.value},
    ]

    # When
    status, failed = _compute_final_status("exp-failed", 2)

    # Then
    assert status == ExperimentStatus.FAILED
    assert failed == 2


# ---------------------------------------------------------------------------
# trial_log coverage — _finalise_bayesian_experiment and _log_bayesian_summary
# ---------------------------------------------------------------------------

_TRIAL_LOG_FIXTURE: list[dict[str, object]] = [
    {"chunk_size": 256, "overlap": 0, "state": "completed", "score": 0.72},
    {"chunk_size": 512, "overlap": 50, "state": "completed", "score": 0.85},
    {"chunk_size": 256, "overlap": 0, "state": "pruned", "score": None},
    {"chunk_size": 768, "overlap": 100, "state": "failed", "score": None},
]


@patch("server.core.orchestrator._log_bayesian_summary")
@patch("server.core.orchestrator._count_failed_runs", return_value=0)
@patch("server.core.orchestrator._compute_final_status")
@patch("server.core.orchestrator.get_storage_backend")
def test_finalise_bayesian_experiment_stores_trial_log_in_bayesian_summary(
    mock_get_storage_backend: MagicMock,
    mock_compute_status: MagicMock,
    mock_count_failed: MagicMock,
    mock_log_summary: MagicMock,
) -> None:
    """
    Scenario: _finalise_bayesian_experiment persists trial_log inside bayesian_summary.

    Given a completed Bayesian experiment with a non-empty trial_log
    When finalization runs
    Then bayesian_summary in the MongoDB update contains the full trial_log list.
    """
    ### Given
    mock_compute_status.return_value = (ExperimentStatus.COMPLETE, 0)
    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage

    config = _slice_config(parallelism=1)
    config.execution.search_strategy = "bayesian"
    config.execution.bayesian.n_trials = 4
    config.chunking.params.chunk_sizes = [256, 512, 768]
    config.chunking.params.overlaps = [0, 50, 100]

    best_trial: dict[str, object] = {
        "query_avg_score": 0.85,
        "chunk_size": 512,
        "overlap": 50,
        "embedding_model": "all-MiniLM-L6-v2",
        "retrieval_method": "dense",
    }

    ### When
    final_status, _ = _finalise_bayesian_experiment(
        experiment_id="exp-trial-log",
        config=config,
        planned_trials=4,
        cancelled=False,
        paused=False,
        run_ids=["run-1", "run-2"],
        attempted_trials=4,
        discarded_trials=1,
        best_trial=best_trial,
        infrastructure_error=None,
        trial_log=_TRIAL_LOG_FIXTURE,
    )

    ### Then
    assert final_status == ExperimentStatus.COMPLETE
    update_call = storage.update_experiment.call_args.args[1]
    stored_log = update_call["bayesian_summary"]["trial_log"]
    assert len(stored_log) == 4
    completed = [e for e in stored_log if e["state"] == "completed"]
    pruned = [e for e in stored_log if e["state"] == "pruned"]
    failed_entries = [e for e in stored_log if e["state"] == "failed"]
    assert len(completed) == 2
    assert len(pruned) == 1
    assert len(failed_entries) == 1
    assert all(isinstance(e["score"], float) for e in completed)
    assert pruned[0]["score"] is None


@patch("server.core.orchestrator._log_bayesian_summary")
@patch("server.core.orchestrator._count_failed_runs", return_value=0)
@patch("server.core.orchestrator._compute_final_status")
@patch("server.core.orchestrator.get_storage_backend")
def test_finalise_bayesian_experiment_omits_trial_log_when_empty(
    mock_get_storage_backend: MagicMock,
    mock_compute_status: MagicMock,
    mock_count_failed: MagicMock,
    mock_log_summary: MagicMock,
) -> None:
    """
    Scenario: _finalise_bayesian_experiment does not store trial_log when empty.

    Given a Bayesian experiment finalized with no trial_log entries
    When finalization runs
    Then bayesian_summary does not contain the trial_log key.
    """
    ### Given
    mock_compute_status.return_value = (ExperimentStatus.COMPLETE, 0)
    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage

    config = _slice_config(parallelism=1)
    config.execution.search_strategy = "bayesian"
    config.execution.bayesian.n_trials = 2
    config.chunking.params.chunk_sizes = [256, 512]
    config.chunking.params.overlaps = [0]

    ### When
    _finalise_bayesian_experiment(
        experiment_id="exp-empty-log",
        config=config,
        planned_trials=2,
        cancelled=False,
        paused=False,
        run_ids=["run-1", "run-2"],
        attempted_trials=2,
        discarded_trials=0,
        best_trial=None,
        infrastructure_error=None,
        trial_log=[],
    )

    ### Then
    update_call = storage.update_experiment.call_args.args[1]
    assert "trial_log" not in update_call["bayesian_summary"]


def test_log_bayesian_summary_with_trial_log_logs_state_counts() -> None:
    """
    Scenario: _log_bayesian_summary emits state-count INFO and per-entry DEBUG logs.

    Given a trial_log with mixed states (completed, pruned, failed)
    When _log_bayesian_summary is called
    Then an INFO log with state counts is emitted and DEBUG logs for each trial entry.
    """
    ### Given
    best_trial: dict[str, object] = {
        "query_avg_score": 0.85,
        "chunk_size": 512,
        "overlap": 50,
        "embedding_model": "all-MiniLM-L6-v2",
        "retrieval_method": "dense",
    }

    ### When / Then — no exception raised and all paths execute
    with patch("server.core.orchestrator.logger") as mock_logger:
        _log_bayesian_summary(
            experiment_id="exp-log-test",
            best_trial=best_trial,
            planned_trials=4,
            grid_equivalent_count=6,
            trial_log=_TRIAL_LOG_FIXTURE,
        )

    info_calls = [call for call in mock_logger.info.call_args_list]
    debug_calls = [call for call in mock_logger.debug.call_args_list]

    # Two INFO calls: the completion summary + the state counts
    assert len(info_calls) == 2
    # State count call includes the by_state dict
    state_count_call = info_calls[1]
    assert "states" in state_count_call.args[0]
    assert state_count_call.args[2] == len(_TRIAL_LOG_FIXTURE)  # entries= param

    # One DEBUG call per trial entry
    assert len(debug_calls) == len(_TRIAL_LOG_FIXTURE)
    # Verify score formatting: completed entries show numeric, others show "—"
    completed_debug = debug_calls[0]  # First entry is completed with score=0.72
    assert "0.7200" in completed_debug.args[-1]
    pruned_debug = debug_calls[2]  # Third entry is pruned with score=None
    assert pruned_debug.args[-1] == "—"


def test_log_bayesian_summary_without_trial_log_skips_state_logging() -> None:
    """
    Scenario: _log_bayesian_summary with no trial_log emits only the completion INFO.

    Given no trial_log passed to _log_bayesian_summary
    When called
    Then only one INFO log is emitted (no state-count or debug entries).
    """
    ### Given
    best_trial: dict[str, object] = {
        "query_avg_score": 0.72,
        "chunk_size": 256,
        "overlap": 0,
        "embedding_model": "all-MiniLM-L6-v2",
        "retrieval_method": "dense",
    }

    ### When / Then
    with patch("server.core.orchestrator.logger") as mock_logger:
        _log_bayesian_summary(
            experiment_id="exp-no-log",
            best_trial=best_trial,
            planned_trials=2,
            grid_equivalent_count=4,
        )

    assert mock_logger.info.call_count == 1
    assert mock_logger.debug.call_count == 0


@patch("server.core.orchestrator.get_storage_backend")
def test_run_best_trial_payload_includes_run_id_in_projection(
    mock_get_storage_backend: MagicMock,
) -> None:
    """
    Scenario: _run_best_trial_payload passes run_id-bearing run_statuses to analyze_results.

    Given completed query results and run_status docs with run_id
    When _run_best_trial_payload is called
    Then analyze_results receives run_statuses with run_id and does not raise KeyError.

    Regression: run_id was previously omitted from the MongoDB projection, causing
    analyze_results to crash with KeyError when computing the best trial. The
    projection itself now lives in MongoStorageBackend.find_run_statuses (see
    tests/server/db/test_mongo_store_adapter.py); this test guards the orchestrator-level
    contract that find_run_statuses' output flows into analyze_results untouched.
    """
    ### Given
    query_results = [
        {
            "run_id": "run-1",
            "query_text": "What is a Pell Grant?",
            "results": [{"dense_score": 0.82, "rerank_score": None, "rank": 1}],
        }
    ]
    run_statuses = [
        {
            "run_id": "run-1",
            "database_provider": "mongodb",
            "embedding_provider": "local",
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking_method": "recursive",
            "chunk_size": 512,
            "overlap": 50,
            "padding": 0,
            "retrieval_method": "dense",
            "retrieval_provider": None,
            "retrieval_model": None,
            "retrievers": [{"type": "dense"}],
        }
    ]

    storage = _fake_storage_backend()
    storage.find_results_for_experiment.return_value = query_results
    storage.find_run_statuses.return_value = run_statuses
    mock_get_storage_backend.return_value = storage

    ### When — must not raise KeyError
    result = _run_best_trial_payload("exp-regression")

    ### Then
    # Function returns best config derived from the single run
    assert result is not None
    assert result.get("chunk_size") == 512
    assert result.get("overlap") == 50


# ---------------------------------------------------------------------------
# AT-01 / AT-02 — termination paths: cancelled and paused
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "flag,expected_status,expected_reason",
    [
        ("cancelled", ExperimentStatus.CANCELLED, "cancelled_by_user"),
        ("paused", ExperimentStatus.PAUSED, "paused_by_user"),
    ],
)
@patch("server.core.orchestrator._count_failed_runs", return_value=2)
@patch("server.core.orchestrator._log_bayesian_summary")
@patch("server.core.orchestrator.get_storage_backend")
def test_finalise_bayesian_experiment_early_stop_paths(
    mock_get_storage_backend: MagicMock,
    mock_log_summary: MagicMock,
    mock_count_failed_runs: MagicMock,
    flag: str,
    expected_status: ExperimentStatus,
    expected_reason: str,
) -> None:
    """
    Scenario: Bayesian sweep stopped by user action finalises with correct terminal status.

    Given a Bayesian experiment that was cancelled or paused by the user
    When _finalise_bayesian_experiment is called with the matching flag True
    Then the experiment document status equals the expected terminal status,
    the completion_reason matches the user-action label,
    and _count_failed_runs is called to record actual failure count.
    """
    ### Given
    config = _slice_config(parallelism=1)
    config.execution.search_strategy = "bayesian"
    config.execution.bayesian.n_trials = 4
    config.chunking.params.chunk_sizes = [128, 256]
    config.chunking.params.overlaps = [0, 50]

    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage

    ### When
    final_status, failed_count = _finalise_bayesian_experiment(
        experiment_id="exp-stop",
        config=config,
        planned_trials=4,
        cancelled=(flag == "cancelled"),
        paused=(flag == "paused"),
        run_ids=["run-1", "run-2"],
        attempted_trials=2,
        discarded_trials=0,
        best_trial=None,
        infrastructure_error=None,
    )

    ### Then
    assert final_status == expected_status
    assert failed_count == 2
    update = storage.update_experiment.call_args.args[1]
    assert update["status"] == expected_status
    assert update["completion_reason"] == expected_reason
    mock_count_failed_runs.assert_called_once_with("exp-stop")


# ---------------------------------------------------------------------------
# AT-03 — all Bayesian trials fail
# ---------------------------------------------------------------------------


@patch("server.core.orchestrator._count_failed_runs", return_value=3)
@patch("server.core.orchestrator._compute_final_status")
@patch("server.core.orchestrator._log_bayesian_summary")
@patch("server.core.orchestrator.get_storage_backend")
def test_finalise_bayesian_experiment_all_trials_failed(
    mock_get_storage_backend: MagicMock,
    mock_log_summary: MagicMock,
    mock_compute_final_status: MagicMock,
    mock_count_failed_runs: MagicMock,
) -> None:
    """
    Scenario: Every Bayesian trial fails — experiment marked FAILED with all_trials_failed.

    Given a Bayesian sweep where all 3 planned trials failed
    When _finalise_bayesian_experiment evaluates the terminal state
    Then status is FAILED and completion_reason is 'all_trials_failed'.
    """
    ### Given
    config = _slice_config(parallelism=1)
    config.execution.search_strategy = "bayesian"
    config.execution.bayesian.n_trials = 3
    config.chunking.params.chunk_sizes = [128, 256, 512]
    config.chunking.params.overlaps = [0, 50]

    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage
    mock_compute_final_status.return_value = (ExperimentStatus.FAILED, 3)

    ### When
    final_status, _ = _finalise_bayesian_experiment(
        experiment_id="exp-all-fail",
        config=config,
        planned_trials=3,
        cancelled=False,
        paused=False,
        run_ids=["run-1", "run-2", "run-3"],
        attempted_trials=3,
        discarded_trials=0,
        best_trial=None,
        infrastructure_error=None,
    )

    ### Then
    assert final_status == ExperimentStatus.FAILED
    update = storage.update_experiment.call_args.args[1]
    assert update["completion_reason"] == "all_trials_failed"


# ---------------------------------------------------------------------------
# AT-04 — partial Bayesian trial failures
# ---------------------------------------------------------------------------


@patch("server.core.orchestrator._count_failed_runs", return_value=1)
@patch("server.core.orchestrator._compute_final_status")
@patch("server.core.orchestrator._log_bayesian_summary")
@patch("server.core.orchestrator.get_storage_backend")
def test_finalise_bayesian_experiment_partial_failures(
    mock_get_storage_backend: MagicMock,
    mock_log_summary: MagicMock,
    mock_compute_final_status: MagicMock,
    mock_count_failed_runs: MagicMock,
) -> None:
    """
    Scenario: Some but not all Bayesian trials fail — FAILED with partial_failures reason.

    Given a Bayesian sweep where 1 of 3 trials failed
    When _finalise_bayesian_experiment evaluates the terminal state
    Then status is FAILED and completion_reason is 'partial_failures'.
    """
    ### Given
    config = _slice_config(parallelism=1)
    config.execution.search_strategy = "bayesian"
    config.execution.bayesian.n_trials = 3
    config.chunking.params.chunk_sizes = [128, 256, 512]
    config.chunking.params.overlaps = [0, 50]

    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage
    mock_compute_final_status.return_value = (ExperimentStatus.FAILED, 1)

    ### When
    final_status, _ = _finalise_bayesian_experiment(
        experiment_id="exp-partial-fail",
        config=config,
        planned_trials=3,
        cancelled=False,
        paused=False,
        run_ids=["run-1", "run-2", "run-3"],
        attempted_trials=3,
        discarded_trials=0,
        best_trial=None,
        infrastructure_error=None,
    )

    ### Then
    assert final_status == ExperimentStatus.FAILED
    update = storage.update_experiment.call_args.args[1]
    assert update["completion_reason"] == "partial_failures"


# ---------------------------------------------------------------------------
# AT-05 — no runs attempted before cancel
# ---------------------------------------------------------------------------


@patch("server.core.orchestrator._log_bayesian_summary")
@patch("server.core.orchestrator.get_storage_backend")
def test_finalise_bayesian_experiment_no_runs_attempted(
    mock_get_storage_backend: MagicMock,
    mock_log_summary: MagicMock,
) -> None:
    """
    Scenario: Bayesian sweep cancelled before any trial started.

    Given a Bayesian sweep that produced no run_ids
    When _finalise_bayesian_experiment runs
    Then status is CANCELLED and completion_reason is 'cancelled_before_attempt'.
    """
    ### Given
    config = _slice_config(parallelism=1)
    config.execution.search_strategy = "bayesian"
    config.execution.bayesian.n_trials = 4
    config.chunking.params.chunk_sizes = [128, 256]
    config.chunking.params.overlaps = [0, 50]

    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage

    ### When
    final_status, failed_count = _finalise_bayesian_experiment(
        experiment_id="exp-no-runs",
        config=config,
        planned_trials=4,
        cancelled=False,
        paused=False,
        run_ids=[],
        attempted_trials=0,
        discarded_trials=0,
        best_trial=None,
        infrastructure_error=None,
    )

    ### Then
    assert final_status == ExperimentStatus.CANCELLED
    assert failed_count == 0
    update = storage.update_experiment.call_args.args[1]
    assert update["completion_reason"] == "cancelled_before_attempt"


# ---------------------------------------------------------------------------
# AT-06 — infrastructure error overrides COMPLETE
# ---------------------------------------------------------------------------


@patch("server.core.orchestrator._count_failed_runs", return_value=0)
@patch("server.core.orchestrator._compute_final_status")
@patch("server.core.orchestrator._log_bayesian_summary")
@patch("server.core.orchestrator.get_storage_backend")
def test_finalise_bayesian_experiment_infrastructure_error_forces_failed(
    mock_get_storage_backend: MagicMock,
    mock_log_summary: MagicMock,
    mock_compute_final_status: MagicMock,
    mock_count_failed_runs: MagicMock,
) -> None:
    """
    Scenario: Infrastructure error overrides an otherwise COMPLETE status.

    Given a Bayesian sweep where runs completed but an infrastructure error occurred
    When _finalise_bayesian_experiment runs
    Then status is FAILED, completion_reason is 'infrastructure_error',
    and error_message is stored on the experiment document.
    """
    ### Given
    config = _slice_config(parallelism=1)
    config.execution.search_strategy = "bayesian"
    config.execution.bayesian.n_trials = 2
    config.chunking.params.chunk_sizes = [128, 256]
    config.chunking.params.overlaps = [0, 50]

    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage
    mock_compute_final_status.return_value = (ExperimentStatus.COMPLETE, 0)

    ### When
    final_status, _ = _finalise_bayesian_experiment(
        experiment_id="exp-infra-err",
        config=config,
        planned_trials=2,
        cancelled=False,
        paused=False,
        run_ids=["run-1", "run-2"],
        attempted_trials=2,
        discarded_trials=0,
        best_trial=None,
        infrastructure_error="Atlas Search index not ready after 30 retries",
    )

    ### Then
    assert final_status == ExperimentStatus.FAILED
    update = storage.update_experiment.call_args.args[1]
    assert update["status"] == ExperimentStatus.FAILED
    assert update["completion_reason"] == "infrastructure_error"
    assert "Atlas Search index not ready" in update["error_message"]


# ---------------------------------------------------------------------------
# AT-07 — infrastructure error does NOT override CANCELLED
# ---------------------------------------------------------------------------


@patch("server.core.orchestrator._count_failed_runs", return_value=1)
@patch("server.core.orchestrator._log_bayesian_summary")
@patch("server.core.orchestrator.get_storage_backend")
def test_finalise_bayesian_experiment_infrastructure_error_does_not_override_cancelled(
    mock_get_storage_backend: MagicMock,
    mock_log_summary: MagicMock,
    mock_count_failed_runs: MagicMock,
) -> None:
    """
    Scenario: Infrastructure error does not override CANCELLED — user intent wins.

    Given a Bayesian sweep that was cancelled AND had an infrastructure error
    When _finalise_bayesian_experiment runs
    Then status remains CANCELLED, not FAILED.
    """
    ### Given
    config = _slice_config(parallelism=1)
    config.execution.search_strategy = "bayesian"
    config.execution.bayesian.n_trials = 2
    config.chunking.params.chunk_sizes = [128, 256]
    config.chunking.params.overlaps = [0, 50]

    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage

    ### When
    final_status, _ = _finalise_bayesian_experiment(
        experiment_id="exp-cancel-infra",
        config=config,
        planned_trials=2,
        cancelled=True,
        paused=False,
        run_ids=["run-1"],
        attempted_trials=1,
        discarded_trials=0,
        best_trial=None,
        infrastructure_error="embedding service timeout",
    )

    ### Then
    assert final_status == ExperimentStatus.CANCELLED
    update = storage.update_experiment.call_args.args[1]
    assert update["status"] == ExperimentStatus.CANCELLED


# ---------------------------------------------------------------------------
# AT-08 — sampler candidate exhaustion sets termination_reason
# ---------------------------------------------------------------------------


@patch("server.core.orchestrator._count_failed_runs", return_value=0)
@patch("server.core.orchestrator._compute_final_status")
@patch("server.core.orchestrator._log_bayesian_summary")
@patch("server.core.orchestrator.get_storage_backend")
def test_finalise_bayesian_experiment_sampler_exhaustion_sets_termination_reason(
    mock_get_storage_backend: MagicMock,
    mock_log_summary: MagicMock,
    mock_compute_final_status: MagicMock,
    mock_count_failed_runs: MagicMock,
) -> None:
    """
    Scenario: Sampler exhausts unique candidates — termination_reason stored in summary.

    Given a Bayesian sweep where Optuna discarded trials and status is PARTIAL
    When _finalise_bayesian_experiment runs
    Then bayesian_summary contains termination_reason='sampler_candidate_exhaustion'.
    """
    ### Given
    config = _slice_config(parallelism=1)
    config.execution.search_strategy = "bayesian"
    config.execution.bayesian.n_trials = 6
    config.chunking.params.chunk_sizes = [128, 256]
    config.chunking.params.overlaps = [0, 50]

    storage = _fake_storage_backend()
    mock_get_storage_backend.return_value = storage
    # failed_count=1 keeps PARTIAL (the code promotes PARTIAL+0-failures to COMPLETE)
    mock_compute_final_status.return_value = (ExperimentStatus.PARTIAL, 1)

    ### When
    _finalise_bayesian_experiment(
        experiment_id="exp-sampler-exhaust",
        config=config,
        planned_trials=6,
        cancelled=False,
        paused=False,
        run_ids=["run-1", "run-2", "run-3", "run-4"],
        attempted_trials=4,
        discarded_trials=2,
        best_trial=None,
        infrastructure_error=None,
    )

    ### Then
    update = storage.update_experiment.call_args.args[1]
    assert update["bayesian_summary"].get("termination_reason") == "sampler_candidate_exhaustion"


# ---------------------------------------------------------------------------
# AT-09 / AT-10 / AT-11 — _run_best_trial_payload degenerate inputs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "description,query_results,best_params_value",
    [
        ("no query results in DB", [], None),
        (
            "analysis returns non-dict",
            [{"run_id": "r1", "query_text": "q", "results": []}],
            "not-a-dict",
        ),
        (
            "analysis returns empty dict",
            [{"run_id": "r1", "query_text": "q", "results": []}],
            {},
        ),
    ],
)
@patch("server.core.results_analyzer.analyze_results")
@patch("server.core.orchestrator.get_storage_backend")
def test_run_best_trial_payload_returns_none_on_degenerate_inputs(
    mock_get_storage_backend: MagicMock,
    mock_analyze: MagicMock,
    description: str,
    query_results: list,
    best_params_value: object,
) -> None:
    """
    Scenario: _run_best_trial_payload returns None gracefully when scoring cannot proceed.

    Given <description>
    When _run_best_trial_payload is called
    Then None is returned without raising.
    """
    ### Given
    storage = _fake_storage_backend()
    storage.find_results_for_experiment.return_value = query_results
    mock_get_storage_backend.return_value = storage
    mock_analyze.return_value = {"best_params": best_params_value}

    ### When
    result = _run_best_trial_payload("exp-degenerate")

    ### Then
    assert result is None, f"expected None for: {description}"


# ---------------------------------------------------------------------------
# AT-12 / AT-13 / AT-14 — _resolve_bayesian_n_trials budget negotiation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "n_trials_cfg,chunk_sizes,overlaps,expected",
    [
        (None, [128, 256, 512], [0, 50], 6),  # AT-12: None → grid-equivalent (3×2=6)
        (10, [128, 256, 512], [0, 50], 6),  # AT-13: exceeds grid → capped at 6
        (4, [128, 256, 512], [0, 50], 4),  # AT-14: within grid → used as configured
    ],
)
def test_resolve_bayesian_n_trials(
    n_trials_cfg: int | None,
    chunk_sizes: list[int],
    overlaps: list[int],
    expected: int,
) -> None:
    """
    Scenario: _resolve_bayesian_n_trials negotiates trial budget against grid-equivalent.

    Given n_trials configured as <n_trials_cfg> and chunk_sizes × overlaps grid
    When _resolve_bayesian_n_trials is called
    Then the returned count equals <expected>.
    """
    ### Given
    config = _slice_config(parallelism=1)
    config.execution.search_strategy = "bayesian"
    config.execution.bayesian.n_trials = n_trials_cfg
    config.chunking.params.chunk_sizes = chunk_sizes
    config.chunking.params.overlaps = overlaps

    ### When
    result = _resolve_bayesian_n_trials(config)

    ### Then
    assert result == expected


# ---------------------------------------------------------------------------
# Orchestrator coverage — easy-win unit tests for uncovered lines
# ---------------------------------------------------------------------------
