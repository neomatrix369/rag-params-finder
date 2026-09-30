"""Supervised asyncio watcher for pending DoubleWord embedding batches."""

from __future__ import annotations

import asyncio
from enum import StrEnum

from server.core.embedding.doubleword_client import (
    cancel_batch,
    create_async_client,
    download_vectors,
    poll_batch,
)
from server.core.embedding.embedding_cache import get_embedding_cache
from server.core.pipeline.executors import schedule_sweep
from server.core.pipeline.pre_embed import CheckpointStore
from server.db.ports.store_factory import get_storage_backend
from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)


class WatcherStatus(StrEnum):
    RUNNING = "running"
    RESTARTING = "restarting"
    DISABLED = "disabled"


_watcher_task: asyncio.Task | None = None
_watcher_status: WatcherStatus = WatcherStatus.DISABLED


class DoubleWordWatcher:
    """Polls .rpf_state/doubleword_batches.json and processes completed batches."""

    def __init__(self, checkpoint_store=None, poll_interval_s: int = 10, poll_timeout_s: int = 5):
        self._store = checkpoint_store or CheckpointStore()
        self._poll_interval = poll_interval_s or settings.doubleword_poll_interval_s
        self._poll_timeout = poll_timeout_s or settings.doubleword_poll_timeout_s
        self._consecutive_errors = 0

    async def run(self) -> None:
        """Main poll loop. Runs until cancelled."""
        while True:
            try:
                entries = await asyncio.to_thread(self._store.load)
                if entries:
                    await self._process_entries(entries)
                    self._consecutive_errors = 0
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._consecutive_errors += 1
                logger.warning(
                    "doubleword_watcher poll error (consecutive=%s): %s",
                    self._consecutive_errors,
                    e,
                )

            # Stretch interval when many pending batches (>10) — avoid hammering API
            interval = self._poll_interval
            try:
                pending = await asyncio.to_thread(self._store.load)
                if len(pending) > 10:
                    interval = 30
            except Exception:
                pass
            await asyncio.sleep(interval)

    async def _process_entries(self, entries: list[dict]) -> None:
        """Process each pending batch entry."""
        client = create_async_client()

        for entry in entries:
            batch_id = entry.get("batch_id")
            experiment_id = entry.get("experiment_id")
            if not batch_id or not experiment_id:
                continue

            try:
                snapshot = await asyncio.wait_for(
                    poll_batch(client, batch_id),
                    timeout=self._poll_timeout,
                )
            except TimeoutError:
                logger.warning("doubleword_watcher timeout polling batch_id=%s", batch_id)
                continue
            except Exception as e:
                logger.warning("doubleword_watcher error polling batch_id=%s: %s", batch_id, e)
                continue

            if snapshot.status == "completed":
                await self._on_batch_completed(client, entry, snapshot)
            elif snapshot.status in ("failed", "expired", "cancelled"):
                await self._on_batch_terminal(entry, snapshot.status)

    async def _on_batch_completed(self, client, entry: dict, snapshot) -> None:
        """Download vectors, cache them, drop checkpoint, trigger sweep if all batches done."""
        experiment_id = entry["experiment_id"]
        batch_id = entry["batch_id"]

        try:
            vectors, errors, _tokens = await download_vectors(
                client, snapshot.output_file_id, snapshot.error_file_id
            )
        except Exception as e:
            logger.error("doubleword_watcher download error batch_id=%s: %s", batch_id, e)
            return

        if errors:
            logger.warning(
                "doubleword_watcher batch_id=%s had %d error items", batch_id, len(errors)
            )

        if vectors:
            cache = get_embedding_cache()
            await asyncio.to_thread(cache.put_many, vectors)

        await asyncio.to_thread(self._store.remove_by_batch_id, batch_id)
        logger.info(
            "doubleword_watcher batch completed and cached: batch_id=%s experiment_id=%s",
            batch_id,
            experiment_id,
        )

        # Check if all batches for this experiment are done
        remaining = await asyncio.to_thread(self._store.get_for_experiment, experiment_id)
        if not remaining:
            await self._trigger_sweep(experiment_id)

    async def _on_batch_terminal(self, entry: dict, status: str) -> None:
        """Handle failed/expired/cancelled batches — mark experiment failed."""
        experiment_id = entry["experiment_id"]
        batch_id = entry["batch_id"]

        logger.error(
            "doubleword_watcher batch terminal: batch_id=%s status=%s experiment_id=%s",
            batch_id,
            status,
            experiment_id,
        )

        await asyncio.to_thread(self._store.remove_for_experiment, experiment_id)

        try:
            store = get_storage_backend()
            await asyncio.to_thread(
                store.update_experiment,
                experiment_id,
                {
                    "status": "failed",
                    "pre_embed": {
                        "state": "failed",
                        "reason": f"DoubleWord batch {status}: batch_id={batch_id}",
                    },
                },
            )
        except Exception as e:
            logger.error("doubleword_watcher failed to mark experiment failed: %s", e)

    async def _trigger_sweep(self, experiment_id: str) -> None:
        """Schedule the sweep now that all embeddings are cached."""
        from server.core.pipeline.orchestrator import run_sweep  # local import avoids circular

        logger.info("doubleword_watcher triggering sweep: experiment_id=%s", experiment_id)

        try:
            store = get_storage_backend()
            experiment = await asyncio.to_thread(store.find_experiment_by_id, experiment_id)
            if experiment is None:
                logger.warning("doubleword_watcher experiment not found: %s", experiment_id)
                return

            config_dict = experiment.get("config") or experiment.get("sweep_config")
            if not config_dict:
                logger.error("doubleword_watcher no config for experiment: %s", experiment_id)
                return

            from server.models.config import ExperimentConfig  # local import to avoid circular

            config = ExperimentConfig.model_validate(config_dict)

            # Update pre_embed state to "ready"
            await asyncio.to_thread(
                store.update_experiment,
                experiment_id,
                {"pre_embed": {"state": "ready"}},
            )

            schedule_sweep(run_sweep, experiment_id, config)
        except Exception as e:
            logger.error("doubleword_watcher failed to trigger sweep for %s: %s", experiment_id, e)


async def _supervised_watcher(watcher: DoubleWordWatcher) -> None:
    """Supervisor: restart watcher on unexpected error with backoff."""
    global _watcher_status

    backoff = 1.0
    while True:
        try:
            _watcher_status = WatcherStatus.RUNNING
            await watcher.run()
        except asyncio.CancelledError:
            _watcher_status = WatcherStatus.DISABLED
            raise
        except Exception as e:
            _watcher_status = WatcherStatus.RESTARTING
            logger.error("doubleword_watcher crashed, restarting in %.1fs: %s", backoff, e)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60.0)


def start_watcher(watcher: DoubleWordWatcher | None = None) -> asyncio.Task | None:
    """Start the supervised watcher task. Returns None if key not set."""
    global _watcher_task, _watcher_status

    if settings.doubleword_api_key is None:
        logger.info("DOUBLEWORD_API_KEY not set — watcher disabled")
        _watcher_status = WatcherStatus.DISABLED
        return None

    if watcher is None:
        watcher = DoubleWordWatcher()

    _watcher_task = asyncio.ensure_future(_supervised_watcher(watcher))
    _watcher_status = WatcherStatus.RUNNING
    logger.info("doubleword_watcher started")
    return _watcher_task


def stop_watcher() -> None:
    """Cancel the watcher task. Does NOT cancel remote batches."""
    global _watcher_task, _watcher_status
    if _watcher_task and not _watcher_task.done():
        _watcher_task.cancel()
    _watcher_task = None
    _watcher_status = WatcherStatus.DISABLED


def get_watcher_status() -> str:
    """Return 'running', 'restarting', or 'disabled'."""
    return _watcher_status.value


async def cancel_experiment_batches(experiment_id: str) -> None:
    """Cancel all DoubleWord batches for an experiment, clean checkpoints."""
    store = CheckpointStore()
    entries = await asyncio.to_thread(store.get_for_experiment, experiment_id)

    if not entries:
        return

    client = create_async_client()
    for entry in entries:
        batch_id = entry.get("batch_id")
        if batch_id:
            try:
                await cancel_batch(client, batch_id)
            except Exception as e:
                logger.warning("doubleword_watcher cancel failed for batch_id=%s: %s", batch_id, e)

    await asyncio.to_thread(store.remove_for_experiment, experiment_id)
