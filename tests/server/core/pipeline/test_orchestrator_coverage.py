"""Focused unit coverage for orchestrator edge helpers.

Author: Codex
Created: 2026-07-20
Scope: Trial log entry, sweep error handlers, bayesian trial mapping, early cancel, truncation.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from server.core.orchestrator import (
    _bayesian_trial_to_run_params,
    _finalise_bayesian_experiment,
    _log_failed_run_summary,
    _make_trial_log_entry,
    _run_sweep_inner,
    run_sweep,
)
from server.core.search_index_plan import SearchIndexMismatchError
from server.core.sie_guard import SIEUnavailableError
from server.models.config import (
    ExperimentConfig,
)
from server.models.enums import (
    ExperimentStatus,
)
from tests.helpers.pipeline_sweep import _fake_storage_backend, _run_param, _slice_config


class TestMakeTrialLogEntry:
    """_make_trial_log_entry is a pure dict constructor — one unit test per outcome shape.

    Exercises line 71 (the return statement), which was unreachable because every
    call site is deep inside the Bayesian trial loop (integration-only).
    """

    def test_returns_dict_with_all_fields_for_completed_trial(self) -> None:
        """
        Scenario: completed trial produces a dict with chunk_size, overlap, state, score.

        Given a RunParams for a completed trial and a score
        When _make_trial_log_entry is called
        Then the returned dict contains the expected field values.
        """
        ### Given
        params = _run_param()
        params.chunk_size = 256
        params.overlap = 32

        ### When
        entry = _make_trial_log_entry(params, state="completed", score=0.85)

        ### Then
        assert entry == {"chunk_size": 256, "overlap": 32, "state": "completed", "score": 0.85}

    def test_returns_none_score_for_pruned_trial(self) -> None:
        """
        Scenario: pruned trial has no score — score field is None.

        Given a RunParams and a None score
        When _make_trial_log_entry is called with state 'pruned'
        Then the returned dict has score=None.
        """
        ### Given
        params = _run_param()

        ### When
        entry = _make_trial_log_entry(params, state="pruned", score=None)

        ### Then
        assert entry["score"] is None
        assert entry["state"] == "pruned"


class TestExecuteSweepErrorHandlers:
    """_execute_sweep catches SearchIndexMismatchError and SIEUnavailableError.

    Exercises lines 245-246 (the two except-return branches). These paths are
    triggered when validate_experiment_search_indexes or validate_sie_readiness
    raise inside _run_sweep_inner / _run_bayesian_inner.
    """

    def _grid_config(self) -> ExperimentConfig:
        return _slice_config(parallelism=1)

    @patch("server.core.orchestrator.unregister_sweep_control")
    @patch("server.core.orchestrator.register_sweep_control")
    @patch("server.core.orchestrator._fail_experiment_preflight", return_value={"status": "failed"})
    @patch(
        "server.core.orchestrator._run_sweep_inner",
        side_effect=SearchIndexMismatchError("index missing"),
    )
    def test_search_index_mismatch_error_returns_preflight_failure(
        self, mock_inner, mock_fail, mock_reg, mock_unreg
    ) -> None:
        """
        Scenario: inner sweep raises SearchIndexMismatchError — preflight failure returned.

        Given _run_sweep_inner raises SearchIndexMismatchError
        When run_sweep is called
        Then _fail_experiment_preflight is called and its result returned.
        """
        ### Given
        config = self._grid_config()

        ### When
        result = run_sweep("exp-idx", config)

        ### Then
        mock_fail.assert_called_once_with("exp-idx", config, "index missing")
        assert result == {"status": "failed"}
        mock_unreg.assert_called_once_with("exp-idx")

    @patch("server.core.orchestrator.unregister_sweep_control")
    @patch("server.core.orchestrator.register_sweep_control")
    @patch("server.core.orchestrator._fail_experiment_preflight", return_value={"status": "failed"})
    @patch("server.core.orchestrator._run_sweep_inner", side_effect=SIEUnavailableError("SIE down"))
    def test_sie_unavailable_error_returns_preflight_failure(
        self, mock_inner, mock_fail, mock_reg, mock_unreg
    ) -> None:
        """
        Scenario: inner sweep raises SIEUnavailableError — preflight failure returned.

        Given _run_sweep_inner raises SIEUnavailableError
        When run_sweep is called
        Then _fail_experiment_preflight is called with the SIE error message.
        """
        ### Given
        config = self._grid_config()

        ### When
        result = run_sweep("exp-sie", config)

        ### Then
        mock_fail.assert_called_once_with("exp-sie", config, "SIE down")
        assert result == {"status": "failed"}


class TestBayesianTrialToRunParams:
    """_bayesian_trial_to_run_params extracts chunk_size and overlap from an Optuna trial.

    Exercises lines 592-596 (the suggest_categorical calls and RunParams construction).
    The trial argument is an Optuna Trial; mocked here to avoid a live Optuna study.
    """

    def test_extracts_chunk_size_and_overlap_from_trial_suggestions(self) -> None:
        """
        Scenario: trial suggestions are wired into RunParams.

        Given a config with chunk_sizes=[128, 256] and overlaps=[0, 50], and an Optuna
        trial mock that suggests 256 and 50
        When _bayesian_trial_to_run_params is called
        Then the returned RunParams has chunk_size=256 and overlap=50.
        """
        ### Given
        config = _slice_config(parallelism=1)
        config.chunking.params.chunk_sizes = [128, 256]
        config.chunking.params.overlaps = [0, 50]

        template = _run_param()

        trial_mock = MagicMock()
        trial_mock.suggest_categorical.side_effect = lambda name, choices: (
            256 if name == "chunk_size" else 50
        )

        ### When
        result = _bayesian_trial_to_run_params(config, template, trial_mock)

        ### Then
        assert result.chunk_size == 256
        assert result.overlap == 50
        trial_mock.suggest_categorical.assert_any_call("chunk_size", [128, 256])
        trial_mock.suggest_categorical.assert_any_call("overlap", [0, 50])


class TestRunSweepInnerEarlyCancel:
    """_run_sweep_inner returns CANCELLED immediately if already cancelled in DB.

    Exercises lines 743-744 (logger.info + return dict when already cancelled).
    """

    @patch("server.core.orchestrator.validate_sie_readiness")
    @patch("server.core.orchestrator.validate_experiment_search_indexes")
    @patch("server.core.orchestrator._experiment_cancelled_in_db", return_value=True)
    def test_returns_cancelled_without_running_any_runs(
        self, mock_cancelled, mock_idx, mock_sie
    ) -> None:
        """
        Scenario: experiment was cancelled before sweep started.

        Given _experiment_cancelled_in_db returns True
        When _run_sweep_inner is called
        Then it returns immediately with status CANCELLED and empty run_ids,
        without validating indexes or launching any runs.
        """
        ### Given
        config = _slice_config(parallelism=1)

        ### When
        result = _run_sweep_inner("exp-cancelled", config, skip_signatures=set())

        ### Then
        assert result["status"] == ExperimentStatus.CANCELLED
        assert result["run_ids"] == []
        assert result["experiment_id"] == "exp-cancelled"
        mock_idx.assert_not_called()
        mock_sie.assert_not_called()


class TestLogFailedRunSummaryTruncation:
    """_log_failed_run_summary truncates to 10 entries and appends a '+N more' suffix.

    Exercises line 976 (the `+N more` suffix appended when failed_count > 10).
    """

    @patch("server.core.orchestrator.get_storage_backend")
    def test_appends_more_suffix_when_failures_exceed_ten(self, mock_get_storage_backend) -> None:
        """
        Scenario: 12 failed runs — summary shows 10 entries then '+2 more'.

        Given find_runs_by_phase already limited to 10 docs (the Mongo adapter applies
        limit=10 internally) and failed_count=12
        When _log_failed_run_summary is called
        Then the warning log includes '+2 more'.
        """
        ### Given
        docs = [
            {
                "run_id": f"run-{i:04d}",
                "embedding_model": "all-MiniLM-L6-v2",
                "chunking_method": "recursive",
                "chunk_size": 512,
                "error_message": None,
            }
            for i in range(10)
        ]
        mock_get_storage_backend.return_value.find_runs_by_phase.return_value = iter(docs)

        ### When
        with patch("server.core.orchestrator.logger") as mock_log:
            _log_failed_run_summary("exp-many-fail", failed_count=12)

        ### Then
        warning_call = mock_log.warning.call_args
        log_message = warning_call[0][0] % warning_call[0][1:]
        assert "+2 more" in log_message


class TestFinaliseByesianExperimentAllTrialsFailedPromotion:
    """Lines 475-476: PARTIAL→FAILED promotion when failed_count == planned_trials.

    This defensive branch fires when _compute_final_status returns (PARTIAL, N)
    with N == planned_trials — a corner case that cannot occur in normal flow but
    is guarded explicitly. AT-08 covers the else-branch at 472-473; this test
    covers the subsequent promotion at 475-476.
    """

    @patch("server.core.orchestrator.get_storage_backend")
    @patch("server.core.orchestrator._log_bayesian_summary")
    @patch("server.core.orchestrator._count_failed_runs", return_value=0)
    @patch(
        "server.core.orchestrator._compute_final_status",
        return_value=(ExperimentStatus.PARTIAL, 3),  # failed_count == planned_trials
    )
    def test_partial_with_all_trials_failed_is_promoted_to_failed(
        self, mock_compute, mock_count, mock_log, mock_get_storage_backend
    ) -> None:
        """
        Scenario: _compute_final_status returns PARTIAL but failed_count equals planned_trials.

        Given mock returns (PARTIAL, 3) and planned_trials=3
        When _finalise_bayesian_experiment is called
        Then the persisted status is FAILED and completion_reason is 'all_trials_failed'.
        """
        ### Given
        storage = _fake_storage_backend()
        mock_get_storage_backend.return_value = storage
        update_calls: list[dict] = []
        storage.update_experiment.side_effect = lambda _experiment_id, update: update_calls.append(
            update
        )

        ### When
        _finalise_bayesian_experiment(
            experiment_id="exp-promote",
            config=_slice_config(parallelism=1),
            planned_trials=3,
            attempted_trials=3,
            discarded_trials=0,
            run_ids=["r1", "r2", "r3"],
            best_trial=None,
            infrastructure_error=None,
            cancelled=False,
            paused=False,
        )

        ### Then
        assert len(update_calls) == 1
        update = update_calls[0]
        assert update["status"] == ExperimentStatus.FAILED.value
        assert update["completion_reason"] == "all_trials_failed"
