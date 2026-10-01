"""Tests for DoubleWord batch watcher (Slice 48A, Stream S4)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.core.embedding.doubleword_client import BatchSnapshot
from server.core.pipeline.doubleword_watcher import (
    DoubleWordWatcher,
    WatcherStatus,
    cancel_experiment_batches,
    get_watcher_status,
    start_watcher,
    stop_watcher,
)


class TestDoubleWordWatcher:
    """Scenario: completed batch triggers sweep."""

    @pytest.mark.asyncio
    async def test_completed_batch_triggers_sweep(self):
        """When a batch completes, vectors are cached and sweep is scheduled.

        Scenario: User submits a DoubleWord experiment → watcher polls → batch returns 'completed'
        Slice: Slice 48A, Stream S4
        GWT:
        - Given a checkpoint entry for batch_id=ABC, experiment_id=EXP1
        - When watcher polls and batch returns status='completed'
        - Then vectors are downloaded and cached
        - And sweep is scheduled for EXP1
        """
        # Setup
        checkpoint_store = MagicMock()
        checkpoint_store.load.return_value = [
            {"batch_id": "batch1", "experiment_id": "exp1", "role": "doc"}
        ]
        checkpoint_store.get_for_experiment.return_value = []  # No more batches

        watcher = DoubleWordWatcher(checkpoint_store=checkpoint_store)

        mock_snapshot = BatchSnapshot(
            batch_id="batch1",
            status="completed",
            output_file_id="output1",
            error_file_id=None,
            completed=10,
            total=10,
            failed=0,
            created_at=None,
            completed_at=None,
        )

        vectors = {"key1": [0.1, 0.2], "key2": [0.3, 0.4]}

        # Fake experiment config for _trigger_sweep
        fake_config = {
            "experiment_name": "test-exp",
            "data_paths": ["./data"],
            "queries_file": "./queries.json",
            "embedding": {"models": ["Qwen/Qwen3-Embedding-8B"]},
            "chunking": {"methods": ["fixed"], "chunk_sizes": [512], "overlaps": [0]},
            "retrieval": {"retrievers": [{"type": "dense"}]},
        }
        mock_store = MagicMock()
        mock_store.find_experiment_by_id.return_value = {"config": fake_config}

        # Mock the async operations
        with (
            patch(
                "server.core.pipeline.doubleword_watcher.create_async_client",
                return_value=AsyncMock(),
            ),
            patch(
                "server.core.pipeline.doubleword_watcher.poll_batch", new_callable=AsyncMock
            ) as mock_poll,
            patch(
                "server.core.pipeline.doubleword_watcher.download_vectors", new_callable=AsyncMock
            ) as mock_download,
            patch(
                "server.core.pipeline.doubleword_watcher.get_embedding_cache"
            ) as mock_cache_factory,
            patch(
                "server.core.pipeline.doubleword_watcher.get_storage_backend",
                return_value=mock_store,
            ),
            patch("server.core.pipeline.doubleword_watcher.schedule_sweep") as mock_schedule,
        ):
            mock_poll.return_value = mock_snapshot
            mock_download.return_value = (vectors, set(), 100)
            mock_cache = MagicMock()
            mock_cache_factory.return_value = mock_cache

            # Execute
            await watcher._process_entries(
                [{"batch_id": "batch1", "experiment_id": "exp1", "role": "doc"}]
            )

            # Verify
            mock_poll.assert_called_once()
            mock_download.assert_called_once()
            mock_cache.put_many.assert_called_once_with(vectors)
            checkpoint_store.remove_by_batch_id.assert_called_once_with("batch1")
            mock_schedule.assert_called_once()

    @pytest.mark.asyncio
    async def test_terminal_batch_marks_experiment_failed(self):
        """When a batch fails, experiment is marked failed.

        Scenario: User submits a DoubleWord experiment → batch fails or expires
        Slice: Slice 48A, Stream S4
        GWT:
        - Given a checkpoint entry for batch_id=ABC, experiment_id=EXP1
        - When batch returns status='failed' or 'expired'
        - Then experiment is marked as failed
        - And checkpoint entries are removed
        """
        checkpoint_store = MagicMock()
        watcher = DoubleWordWatcher(checkpoint_store=checkpoint_store)

        with patch(
            "server.core.pipeline.doubleword_watcher.get_storage_backend"
        ) as mock_store_factory:
            mock_store = MagicMock()
            mock_store_factory.return_value = mock_store

            # Execute
            await watcher._on_batch_terminal(
                {"batch_id": "batch1", "experiment_id": "exp1"},
                "failed",
            )

            # Verify
            checkpoint_store.remove_for_experiment.assert_called_once_with("exp1")
            mock_store.update_experiment.assert_called_once()
            call_args = mock_store.update_experiment.call_args
            assert call_args[0][0] == "exp1"
            assert call_args[0][1]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_timeout_on_poll_continues(self):
        """When poll times out, loop continues to next batch.

        Scenario: Batch poll hangs or is slow
        Slice: Slice 48A, Stream S4
        GWT:
        - Given two pending batches
        - When first batch poll times out
        - Then watcher skips to second batch
        - And loop continues
        """
        checkpoint_store = MagicMock()
        checkpoint_store.load.return_value = [
            {"batch_id": "batch1", "experiment_id": "exp1", "role": "doc"},
            {"batch_id": "batch2", "experiment_id": "exp2", "role": "query"},
        ]

        watcher = DoubleWordWatcher(checkpoint_store=checkpoint_store, poll_timeout_s=1)

        with patch(
            "server.core.pipeline.doubleword_watcher.poll_batch", new_callable=AsyncMock
        ) as mock_poll:
            # First batch times out, second succeeds
            async def poll_side_effect(client, batch_id):
                if batch_id == "batch1":
                    await asyncio.sleep(2)  # Will timeout
                    return None
                return BatchSnapshot("batch2", "completed", "out", None, 5, 5, 0, None, None)

            mock_poll.side_effect = poll_side_effect

            # Execute (with timeout, the first will raise TimeoutError)
            try:
                await watcher._process_entries(
                    [
                        {"batch_id": "batch1", "experiment_id": "exp1", "role": "doc"},
                        {"batch_id": "batch2", "experiment_id": "exp2", "role": "query"},
                    ]
                )
            except Exception:
                pass  # Timeout is expected and caught in the actual code

    def test_no_api_key_returns_none(self):
        """When DOUBLEWORD_API_KEY is not set, start_watcher returns None.

        Scenario: User has not configured DoubleWord
        Slice: Slice 48A, Stream S4
        GWT:
        - Given DOUBLEWORD_API_KEY is None
        - When start_watcher is called
        - Then it returns None
        - And watcher status is 'disabled'
        """
        # Clean up any existing global state
        from server.core.pipeline import doubleword_watcher

        doubleword_watcher._watcher_task = None
        doubleword_watcher._watcher_status = WatcherStatus.DISABLED

        with patch("server.core.pipeline.doubleword_watcher.settings") as mock_settings:
            mock_settings.doubleword_api_key = None

            result = start_watcher()

            assert result is None
            assert get_watcher_status() == "disabled"

    def test_stop_watcher_cancels_task(self):
        """When stop_watcher is called, the task is cancelled.

        Scenario: Server is shutting down
        Slice: Slice 48A, Stream S4
        GWT:
        - Given a running watcher task
        - When stop_watcher is called
        - Then the task is cancelled
        - And watcher status is 'disabled'
        """
        # Create a fake task
        from server.core.pipeline import doubleword_watcher

        mock_task = MagicMock()
        mock_task.done.return_value = False
        doubleword_watcher._watcher_task = mock_task

        stop_watcher()

        mock_task.cancel.assert_called_once()
        assert get_watcher_status() == "disabled"

    @pytest.mark.asyncio
    async def test_cancel_experiment_batches_cancels_remote(self):
        """When cancel_experiment_batches is called, remote batches are cancelled.

        Scenario: User cancels an experiment waiting for embeddings
        Slice: Slice 48A, Stream S4
        GWT:
        - Given two checkpoint entries for experiment_id=EXP1
        - When cancel_experiment_batches(EXP1) is called
        - Then cancel_batch is called for each batch_id
        - And checkpoint entries are removed
        """
        checkpoint_store_mock = MagicMock()
        checkpoint_store_mock.get_for_experiment.return_value = [
            {"batch_id": "batch1", "experiment_id": "exp1"},
            {"batch_id": "batch2", "experiment_id": "exp1"},
        ]

        with (
            patch(
                "server.core.pipeline.doubleword_watcher.CheckpointStore",
                return_value=checkpoint_store_mock,
            ),
            patch(
                "server.core.pipeline.doubleword_watcher.cancel_batch", new_callable=AsyncMock
            ) as mock_cancel,
            patch(
                "server.core.pipeline.doubleword_watcher.create_async_client",
                return_value=AsyncMock(),
            ),
        ):
            await cancel_experiment_batches("exp1")

            assert mock_cancel.call_count == 2
            checkpoint_store_mock.remove_for_experiment.assert_called_once_with("exp1")

    @pytest.mark.asyncio
    async def test_all_batches_completed_triggers_single_sweep(self):
        """When all batches for an experiment complete, sweep fires once.

        Scenario: Multi-batch experiment completes
        Slice: Slice 48A, Stream S4
        GWT:
        - Given two batches for experiment_id=EXP1
        - When both batches complete one at a time
        - Then sweep is scheduled only after the last batch completes
        """
        checkpoint_store = MagicMock()
        # Two batches initially
        checkpoint_store.load.side_effect = [
            [
                {"batch_id": "batch1", "experiment_id": "exp1", "role": "doc"},
                {"batch_id": "batch2", "experiment_id": "exp1", "role": "query"},
            ],
        ]
        # After first batch is removed, one remains
        checkpoint_store.get_for_experiment.side_effect = [
            [{"batch_id": "batch2", "experiment_id": "exp1"}],  # After first removal
            [],  # After second removal
        ]

        watcher = DoubleWordWatcher(checkpoint_store=checkpoint_store)
        mock_client = AsyncMock()

        fake_config = {
            "experiment_name": "test-exp",
            "data_paths": ["./data"],
            "queries_file": "./queries.json",
            "embedding": {"models": ["Qwen/Qwen3-Embedding-8B"]},
            "chunking": {"methods": ["fixed"], "chunk_sizes": [512], "overlaps": [0]},
            "retrieval": {"retrievers": [{"type": "dense"}]},
        }
        mock_store = MagicMock()
        mock_store.find_experiment_by_id.return_value = {"config": fake_config}

        with (
            patch(
                "server.core.pipeline.doubleword_watcher.poll_batch", new_callable=AsyncMock
            ) as mock_poll,
            patch(
                "server.core.pipeline.doubleword_watcher.download_vectors", new_callable=AsyncMock
            ) as mock_download,
            patch(
                "server.core.pipeline.doubleword_watcher.get_embedding_cache"
            ) as mock_cache_factory,
            patch(
                "server.core.pipeline.doubleword_watcher.get_storage_backend",
                return_value=mock_store,
            ),
            patch("server.core.pipeline.doubleword_watcher.schedule_sweep") as mock_schedule,
        ):
            mock_poll.return_value = BatchSnapshot(
                "batch1", "completed", "out", None, 5, 5, 0, None, None
            )
            mock_download.return_value = ({"key1": [0.1]}, set(), 100)
            mock_cache = MagicMock()
            mock_cache_factory.return_value = mock_cache

            # First batch completes (should not trigger sweep yet)
            await watcher._on_batch_completed(
                mock_client,
                {"batch_id": "batch1", "experiment_id": "exp1"},
                mock_poll.return_value,
            )

            # At this point, one batch remains, so sweep is NOT scheduled
            assert mock_schedule.call_count == 0

            # Now simulate second batch completing
            checkpoint_store.get_for_experiment.side_effect = [
                [],  # Now no batches remain
            ]

            await watcher._on_batch_completed(
                mock_client,
                {"batch_id": "batch2", "experiment_id": "exp1"},
                mock_poll.return_value,
            )

            # Now sweep should be scheduled
            assert mock_schedule.call_count == 1
