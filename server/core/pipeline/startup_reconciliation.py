"""Reconcile experiments left in RUNNING after server restart or crash."""

from datetime import UTC, datetime

from server.core.pipeline.pre_embed import CheckpointStore
from server.db.ports.store_factory import get_storage_backend
from server.models.enums import ExperimentStatus, Phase
from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

_TERMINAL_RUN_PHASES = frozenset(
    {
        Phase.COMPLETE.value,
        Phase.FAILED.value,
        Phase.INTERRUPTED.value,
    }
)

_ORPHAN_ERROR = "Interrupted — server restarted while run was in progress"


def reconcile_orphaned_experiments() -> int:
    """Mark stale RUNNING experiments after process restart.

    Sweep tasks run in FastAPI BackgroundTasks and live only in memory.
    Any experiment still RUNNING when the server starts cannot be executing.

    Experiments waiting for DoubleWord batches (pre_embed.state == "waiting")
    are NOT marked as stale — the watcher will resume them.

    Returns the number of experiments reconciled.
    """
    storage = get_storage_backend()
    running = storage.find_running_experiments()
    if not running:
        return 0

    checkpoint_store = CheckpointStore()
    all_checkpoint_entries = checkpoint_store.load()
    checkpoint_experiment_ids = frozenset(
        e.get("experiment_id") for e in all_checkpoint_entries if e.get("experiment_id")
    )

    reconciled = 0
    for experiment in running:
        experiment_id = str(experiment["_id"])
        pre_embed = experiment.get("pre_embed")

        # Case 1: experiment is waiting for DoubleWord batches — exempt from reconciliation
        if (
            pre_embed
            and pre_embed.get("state") == "waiting"
            and experiment_id in checkpoint_experiment_ids
        ):
            logger.info(
                "startup reconcile — exempting RUNNING experiment with active batches: id=%s",
                experiment_id,
            )
            continue

        # Case 2: experiment claims to be waiting but has no checkpoints — mark failed
        if (
            pre_embed
            and pre_embed.get("state") == "waiting"
            and experiment_id not in checkpoint_experiment_ids
        ):
            logger.warning(
                "startup reconcile — marking failed: waiting state but no batches: id=%s",
                experiment_id,
            )
            now = datetime.now(UTC)
            storage.update_experiment_reconciled(
                experiment_id,
                status="failed",
                failed_count=0,
                completion_reason="pre_embed_batches_cannot_be_resumed",
                completed_at=now,
            )
            reconciled += 1
            continue

        # Case 3: waiting but DOUBLEWORD_API_KEY removed — mark failed, keep checkpoints
        if pre_embed and pre_embed.get("state") == "waiting":
            if settings.doubleword_api_key is None:
                logger.warning(
                    "startup reconcile — marking failed: DOUBLEWORD_API_KEY removed: id=%s",
                    experiment_id,
                )
                now = datetime.now(UTC)
                storage.update_experiment_reconciled(
                    experiment_id,
                    status="failed",
                    failed_count=0,
                    completion_reason="doubleword_api_key_removed",
                    completed_at=now,
                )
                reconciled += 1
                continue

        # Default: mark as orphaned
        _reconcile_one(experiment_id, experiment, storage)
        reconciled += 1

    logger.info("startup reconcile — %s orphaned experiment(s) in RUNNING", reconciled)
    return reconciled


def _reconcile_one(experiment_id: str, experiment: dict, storage) -> None:
    runs = storage.find_run_statuses(experiment_id)
    in_flight = [run for run in runs if run.get("phase") not in _TERMINAL_RUN_PHASES]
    now = datetime.now(UTC)

    if in_flight:
        storage.mark_runs_interrupted(
            [run["run_id"] for run in in_flight],
            updated_at=now,
            error_message=_ORPHAN_ERROR,
        )
        for run in in_flight:
            logger.warning(
                "run orphaned interrupt — experiment=%s run=%s was_phase=%s",
                experiment_id,
                run["run_id"],
                run.get("phase"),
            )

    runs = storage.find_run_statuses(experiment_id)
    status, failed_count = _derive_experiment_status(experiment, runs)
    complete_count = sum(1 for run in runs if run.get("phase") == Phase.COMPLETE.value)
    interrupted_count = sum(1 for run in runs if run.get("phase") == Phase.INTERRUPTED.value)
    expected = int(experiment.get("run_count") or 0)
    attempted = len(runs)

    if status == ExperimentStatus.COMPLETE:
        if complete_count < expected:
            completion_reason = "completed_with_sampling_shortfall"
        else:
            completion_reason = "all_planned_trials_completed"
    elif status == ExperimentStatus.FAILED:
        completion_reason = "all_trials_failed" if failed_count == expected else "mixed_failures"
    elif status == ExperimentStatus.PARTIAL:
        if failed_count == 0 and interrupted_count > 0:
            completion_reason = "interrupted_before_completion"
        elif failed_count > 0:
            completion_reason = "mixed_failures"
        else:
            completion_reason = "incomplete_before_completion"
    elif status == ExperimentStatus.CANCELLED:
        completion_reason = "cancelled_by_user"
    elif status == ExperimentStatus.PAUSED:
        completion_reason = "paused_by_user"
    else:
        completion_reason = (
            "reconciled_from_orphaned_run"
            if attempted > 0 or expected > 0
            else "incomplete_before_completion"
        )

    storage.update_experiment_reconciled(
        experiment_id,
        status=status,
        failed_count=failed_count,
        completion_reason=completion_reason,
        completed_at=now,
    )
    logger.info(
        "experiment status reconciled — id=%s status=%s "
        "complete=%s/%s in_flight=%s never_started=%s",
        experiment_id,
        status.value,
        complete_count,
        expected,
        len(in_flight),
        max(0, expected - len(runs)),
    )


def _derive_experiment_status(
    experiment: dict,
    runs: list[dict],
) -> tuple[ExperimentStatus, int]:
    expected = int(experiment.get("run_count") or 0)
    complete = sum(1 for run in runs if run.get("phase") == Phase.COMPLETE.value)
    failed = sum(1 for run in runs if run.get("phase") == Phase.FAILED.value)

    if complete == expected and failed == 0:
        return ExperimentStatus.COMPLETE, failed
    if failed == expected or (failed > 0 and complete == 0 and failed == len(runs)):
        return ExperimentStatus.FAILED, failed
    return ExperimentStatus.PARTIAL, failed
