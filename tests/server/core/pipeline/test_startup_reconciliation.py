"""
Tests for startup orphan reconciliation (StorageBackend path).

Author: swami
Created: 2026-07-26
Scope: Slice 37 Should — Postgres-path coverage via StorageBackend mock
       (same code path as Mongo; no live DB required)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from server.core.startup_reconciliation import reconcile_orphaned_experiments
from server.models.enums import ExperimentStatus, Phase


class TestStartupReconciliationShould:
    def test_given_running_postgres_experiment_when_reconciled_then_marks_interrupted(
        self,
    ) -> None:
        """
        Scenario: given running postgres experiment when reconciled then marks interrupted.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Orphan RUNNING experiment with in-flight run becomes PARTIAL.
        Slice: 37 — boot reconciliation (Postgres path via StorageBackend)

        Given a RUNNING experiment (postgres sweep_summary) with one EMBEDDING run,
        When reconcile_orphaned_experiments runs,
        Then the in-flight run is interrupted and the experiment is reconciled.
        """
        ### Given
        storage = MagicMock()
        experiment = {
            "_id": "exp-pg-orphan",
            "run_count": 2,
            "sweep_summary": {"database_provider": "postgres", "storage_mode": "postgres-local"},
        }
        storage.find_running_experiments.return_value = [experiment]
        storage.find_run_statuses.side_effect = [
            [
                {
                    "run_id": "run-1",
                    "phase": Phase.EMBEDDING.value,
                }
            ],
            [
                {
                    "run_id": "run-1",
                    "phase": Phase.INTERRUPTED.value,
                }
            ],
        ]

        ### When
        with patch(
            "server.core.startup_reconciliation.get_storage_backend",
            return_value=storage,
        ):
            actual_count = reconcile_orphaned_experiments()

        ### Then
        assert actual_count == 1
        storage.mark_runs_interrupted.assert_called_once()
        interrupted_ids = storage.mark_runs_interrupted.call_args.args[0]
        assert interrupted_ids == ["run-1"]
        storage.update_experiment_reconciled.assert_called_once()
        kwargs = storage.update_experiment_reconciled.call_args.kwargs
        assert kwargs["status"] == ExperimentStatus.PARTIAL
        assert kwargs["completion_reason"] == "interrupted_before_completion"

    def test_given_no_running_experiments_when_reconciled_then_returns_zero(self) -> None:
        """
        Scenario: given no running experiments when reconciled then returns zero.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Clean boot with no orphans is a no-op.
        Slice: 37 — boot reconciliation

        Given find_running_experiments returns empty,
        When reconcile_orphaned_experiments runs,
        Then zero is returned and no writes occur.
        """
        ### Given
        storage = MagicMock()
        storage.find_running_experiments.return_value = []

        ### When
        with patch(
            "server.core.startup_reconciliation.get_storage_backend",
            return_value=storage,
        ):
            actual_count = reconcile_orphaned_experiments()

        ### Then
        assert actual_count == 0
        storage.mark_runs_interrupted.assert_not_called()
        storage.update_experiment_reconciled.assert_not_called()

    def test_given_waiting_experiment_with_checkpoints_when_reconciled_then_exempts(self) -> None:
        """
        Scenario: Waiting experiment with active DoubleWord batches is exempted from reconciliation.
        Slice: 48A — detached watcher + resume (S4)

        Given a RUNNING experiment with pre_embed.state="waiting" and active checkpoints,
        When reconcile_orphaned_experiments runs,
        Then the experiment is not marked as stale (exempted for watcher to resume).
        """
        ### Given
        storage = MagicMock()
        experiment = {
            "_id": "exp-doubleword-waiting",
            "run_count": 1,
            "pre_embed": {"state": "waiting"},
            "status": "running",
        }
        storage.find_running_experiments.return_value = [experiment]

        checkpoint_store_mock = MagicMock()
        checkpoint_store_mock.load.return_value = [
            {"batch_id": "batch1", "experiment_id": "exp-doubleword-waiting"}
        ]

        ### When
        with (
            patch("server.core.startup_reconciliation.get_storage_backend", return_value=storage),
            patch(
                "server.core.startup_reconciliation.CheckpointStore",
                return_value=checkpoint_store_mock,
            ),
        ):
            actual_count = reconcile_orphaned_experiments()

        ### Then
        assert actual_count == 0
        storage.update_experiment_reconciled.assert_not_called()

    def test_given_waiting_experiment_without_checkpoints_when_reconciled_then_marks_failed(
        self,
    ) -> None:
        """
        Scenario: Waiting experiment with no checkpoints is marked failed.
        Slice: 48A — detached watcher + resume (S4)

        Given a RUNNING experiment with pre_embed.state="waiting" but no checkpoints,
        When reconcile_orphaned_experiments runs,
        Then the experiment is marked as failed (batches cannot be resumed).
        """
        ### Given
        storage = MagicMock()
        experiment = {
            "_id": "exp-doubleword-orphaned",
            "run_count": 1,
            "pre_embed": {"state": "waiting"},
            "status": "running",
        }
        storage.find_running_experiments.return_value = [experiment]

        checkpoint_store_mock = MagicMock()
        checkpoint_store_mock.load.return_value = []  # No checkpoints

        ### When
        with (
            patch("server.core.startup_reconciliation.get_storage_backend", return_value=storage),
            patch(
                "server.core.startup_reconciliation.CheckpointStore",
                return_value=checkpoint_store_mock,
            ),
        ):
            actual_count = reconcile_orphaned_experiments()

        ### Then
        assert actual_count == 1
        storage.update_experiment_reconciled.assert_called_once()
        call_kwargs = storage.update_experiment_reconciled.call_args.kwargs
        assert call_kwargs["status"] == "failed"
        assert call_kwargs["completion_reason"] == "pre_embed_batches_cannot_be_resumed"
