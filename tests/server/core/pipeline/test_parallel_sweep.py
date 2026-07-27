"""GWT tests for Slice 16 parallel sweep execution semantics.

Author: Codex
Created: 2026-07-20
Scope: Bounded concurrency, failure policy, cancellation, preflight, resume dispatch.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from server.core.experiment_control import ExperimentCancelledError
from server.core.orchestrator import (
    _run_sweep_inner,
    resume_sweep,
    run_sweep,
)
from server.core.search_index_plan import SearchIndexMismatchError
from server.core.sie_guard import SIEUnavailableError
from server.models.enums import (
    ExperimentStatus,
)
from tests.helpers.pipeline_sweep import _fake_storage_backend, _run_param, _slice_config


class TestSlice16ParallelSweep:
    """Scenario: execute a sweep with bounded in-process concurrency."""

    @patch("server.core.orchestrator._compute_final_status")
    @patch("server.core.orchestrator.get_storage_backend")
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
        mock_get_storage_backend: MagicMock,
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
        mock_get_storage_backend.return_value = _fake_storage_backend()
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
    @patch("server.core.orchestrator.get_storage_backend")
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
        mock_get_storage_backend: MagicMock,
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
        mock_get_storage_backend.return_value = _fake_storage_backend()
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
    @patch("server.core.orchestrator.get_storage_backend")
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
        mock_get_storage_backend: MagicMock,
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
        mock_get_storage_backend.return_value = _fake_storage_backend()
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
    @patch("server.core.orchestrator.get_storage_backend")
    def test_cancelled_before_run_start_skips_run_submission(
        self,
        mock_get_storage_backend: MagicMock,
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
        mock_get_storage_backend.return_value = _fake_storage_backend()
        config = _slice_config(parallelism=2)

        # When
        result = _run_sweep_inner("exp-cancel", config, set())

        # Then
        assert result["status"] == ExperimentStatus.CANCELLED
        mock_expand_sweep.assert_not_called()

    @patch("server.core.orchestrator.check_control")
    @patch("server.core.orchestrator._compute_final_status")
    @patch("server.core.orchestrator.get_storage_backend")
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
        mock_get_storage_backend: MagicMock,
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
        mock_get_storage_backend.return_value = _fake_storage_backend()
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
    @patch("server.core.orchestrator.get_storage_backend")
    @patch("server.core.orchestrator.unregister_sweep_control")
    @patch("server.core.orchestrator.register_sweep_control")
    def test_search_index_preflight_failure_marks_experiment_failed(
        self,
        mock_register_sweep_control: MagicMock,
        mock_unregister_sweep_control: MagicMock,
        mock_get_storage_backend: MagicMock,
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
        mock_get_storage_backend.return_value = _fake_storage_backend()
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
    @patch("server.core.orchestrator.get_storage_backend")
    @patch("server.core.orchestrator._compute_final_status")
    @patch("server.core.orchestrator._run_single")
    @patch("server.core.orchestrator.check_control")
    def test_infra_error_marks_status_as_failed(
        self,
        mock_check_control: MagicMock,
        mock_run_single: MagicMock,
        mock_compute_final_status: MagicMock,
        mock_get_storage_backend: MagicMock,
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
        mock_get_storage_backend.return_value = _fake_storage_backend()
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

    @patch("server.core.orchestrator._run_bayesian_inner")
    @patch("server.core.orchestrator._run_sweep_inner")
    def test_run_sweep_dispatches_bayesian_and_grid_paths(
        self,
        mock_run_sweep_inner: MagicMock,
        mock_run_bayesian_inner: MagicMock,
    ) -> None:
        """
        Scenario: run_sweep dispatches by execution.search_strategy.

        Given one grid and one bayesian configuration
        When run_sweep executes
        Then each execution path calls its own inner function.
        """
        config_bayesian = _slice_config(parallelism=1)
        config_bayesian.execution.search_strategy = "bayesian"
        config_grid = _slice_config(parallelism=1)

        mock_run_bayesian_inner.return_value = {
            "experiment_id": "exp-bayes",
            "run_ids": ["r-1"],
            "status": ExperimentStatus.COMPLETE,
        }
        mock_run_sweep_inner.return_value = {
            "experiment_id": "exp-grid",
            "run_ids": ["r-2"],
            "status": ExperimentStatus.COMPLETE,
        }

        run_sweep("exp-bayes", config_bayesian)
        run_sweep("exp-grid", config_grid)

        mock_run_bayesian_inner.assert_called_once_with("exp-bayes", config_bayesian, set())
        mock_run_sweep_inner.assert_called_once_with("exp-grid", config_grid, set())
