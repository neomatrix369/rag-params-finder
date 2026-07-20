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
from server.core.experiment_control import ExperimentCancelledError
from server.core.orchestrator import _run_sweep_inner
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
    RunParams,
)
from server.models.enums import ChunkingMethod, ExperimentStatus, RetrievalMethod, RetrieverType


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
