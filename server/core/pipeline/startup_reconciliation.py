"""Reconcile experiments left in RUNNING after server restart or crash."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from server.core.pipeline.outcome import CompletionReason, RunTally, tally_runs
from server.core.pipeline.pre_embed import CheckpointStore
from server.db.ports.storage import ExperimentStore, RunStore
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

# ── completion_reason strings owned by this module (not in CompletionReason) ──
_REASON_PRE_EMBED_BATCHES_CANNOT_BE_RESUMED = "pre_embed_batches_cannot_be_resumed"
_REASON_DOUBLEWORD_API_KEY_REMOVED = "doubleword_api_key_removed"
_REASON_MIXED_FAILURES = "mixed_failures"
_REASON_INCOMPLETE_BEFORE_COMPLETION = "incomplete_before_completion"
_REASON_RECONCILED_FROM_ORPHANED_RUN = "reconciled_from_orphaned_run"

_LOG_NO_BATCHES = "startup reconcile — marking failed: waiting state but no batches: id=%s"
_LOG_API_KEY_REMOVED = "startup reconcile — marking failed: DOUBLEWORD_API_KEY removed: id=%s"
_LOG_EXEMPT = "startup reconcile — exempting RUNNING experiment with active batches: id=%s"


class ReconciliationStore(ExperimentStore, RunStore, Protocol):
    """The two narrow ports boot reconciliation actually calls."""


@dataclass(frozen=True, slots=True)
class NotWaiting:
    """The experiment is not waiting on pre-embed batches."""


@dataclass(frozen=True, slots=True)
class ExemptFromReconciliation:
    """Waiting with live batches — leave it RUNNING for the watcher."""

    log_message: str = _LOG_EXEMPT


@dataclass(frozen=True, slots=True)
class MarkWaitingFailed:
    """Waiting but unresumable — fail it with this exact reason."""

    completion_reason: str
    log_message: str


WaitingDecision = NotWaiting | ExemptFromReconciliation | MarkWaitingFailed

_NOT_WAITING = NotWaiting()
_EXEMPT = ExemptFromReconciliation()


def _classify_waiting(
    pre_embed: Any,
    experiment_id: str,
    checkpoint_experiment_ids: frozenset[Any],
    doubleword_api_key: object | None,
) -> WaitingDecision:
    """Decide how a RUNNING experiment's ``pre_embed`` state should be handled.

    Pure: the three former inline guards in their original order.

    * waiting with an active checkpoint → exempt, the watcher resumes it;
    * waiting without any checkpoint → failed, batches cannot be resumed;
    * waiting with no DoubleWord API key → failed, key removed;
    * anything else → not waiting, the orphan path applies.
    """
    if not pre_embed or pre_embed.get("state") != "waiting":
        return _NOT_WAITING
    if experiment_id in checkpoint_experiment_ids:
        return _EXEMPT
    if experiment_id not in checkpoint_experiment_ids:
        return MarkWaitingFailed(
            completion_reason=_REASON_PRE_EMBED_BATCHES_CANNOT_BE_RESUMED,
            log_message=_LOG_NO_BATCHES,
        )
    if doubleword_api_key is None:
        return MarkWaitingFailed(
            completion_reason=_REASON_DOUBLEWORD_API_KEY_REMOVED,
            log_message=_LOG_API_KEY_REMOVED,
        )
    return _NOT_WAITING


def reconcile_orphaned_experiments() -> int:
    """Mark stale RUNNING experiments after process restart.

    Sweep tasks run in FastAPI BackgroundTasks and live only in memory.
    Any experiment still RUNNING when the server starts cannot be executing.

    Experiments waiting for DoubleWord batches (pre_embed.state == "waiting")
    are NOT marked as stale — the watcher will resume them.

    Returns the number of experiments reconciled.
    """
    storage: ReconciliationStore = get_storage_backend()
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
        decision = _classify_waiting(
            experiment.get("pre_embed"),
            experiment_id,
            checkpoint_experiment_ids,
            settings.doubleword_api_key,
        )

        if isinstance(decision, ExemptFromReconciliation):
            logger.info(decision.log_message, experiment_id)
            continue

        if isinstance(decision, MarkWaitingFailed):
            logger.warning(decision.log_message, experiment_id)
            storage.update_experiment_reconciled(
                experiment_id,
                status="failed",
                failed_count=0,
                completion_reason=decision.completion_reason,
                completed_at=datetime.now(UTC),
            )
            reconciled += 1
            continue

        _reconcile_one(experiment_id, experiment, storage)
        reconciled += 1

    logger.info("startup reconcile — %s orphaned experiment(s) in RUNNING", reconciled)
    return reconciled


def _interrupt_in_flight_runs(
    experiment_id: str,
    runs: list[dict],
    storage: RunStore,
    now: datetime,
) -> list[dict]:
    """Mark every non-terminal run of this experiment INTERRUPTED; return them."""
    in_flight = [run for run in runs if run.get("phase") not in _TERMINAL_RUN_PHASES]
    if not in_flight:
        return in_flight

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
    return in_flight


def _partial_completion_reason(tally: RunTally, failed_count: int) -> str:
    if failed_count == 0 and tally.interrupted > 0:
        return CompletionReason.INTERRUPTED_BEFORE_COMPLETION.value
    if failed_count > 0:
        return _REASON_MIXED_FAILURES
    return _REASON_INCOMPLETE_BEFORE_COMPLETION


def _other_completion_reason(status: ExperimentStatus, expected: int, attempted: int) -> str:
    if status == ExperimentStatus.CANCELLED:
        return CompletionReason.CANCELLED_BY_USER.value
    if status == ExperimentStatus.PAUSED:
        return CompletionReason.PAUSED_BY_USER.value
    if attempted > 0 or expected > 0:
        return _REASON_RECONCILED_FROM_ORPHANED_RUN
    return _REASON_INCOMPLETE_BEFORE_COMPLETION


def _completion_reason(
    status: ExperimentStatus,
    tally: RunTally,
    failed_count: int,
    expected: int,
    attempted: int,
) -> str:
    """The reconciled ``completion_reason`` for a derived experiment status."""
    if status == ExperimentStatus.COMPLETE:
        if tally.complete < expected:
            return CompletionReason.COMPLETED_WITH_SAMPLING_SHORTFALL.value
        return CompletionReason.ALL_PLANNED_TRIALS_COMPLETED.value
    if status == ExperimentStatus.FAILED:
        if failed_count == expected:
            return CompletionReason.ALL_TRIALS_FAILED.value
        return _REASON_MIXED_FAILURES
    if status == ExperimentStatus.PARTIAL:
        return _partial_completion_reason(tally, failed_count)
    return _other_completion_reason(status, expected, attempted)


def _reconcile_one(experiment_id: str, experiment: dict, storage: ReconciliationStore) -> None:
    now = datetime.now(UTC)
    in_flight = _interrupt_in_flight_runs(
        experiment_id,
        storage.find_run_statuses(experiment_id),
        storage,
        now,
    )

    runs = storage.find_run_statuses(experiment_id)
    status, failed_count = _derive_experiment_status(experiment, runs)
    tally = tally_runs(runs)
    expected = int(experiment.get("run_count") or 0)

    storage.update_experiment_reconciled(
        experiment_id,
        status=status,
        failed_count=failed_count,
        completion_reason=_completion_reason(status, tally, failed_count, expected, len(runs)),
        completed_at=now,
    )
    logger.info(
        "experiment status reconciled — id=%s status=%s "
        "complete=%s/%s in_flight=%s never_started=%s",
        experiment_id,
        status.value,
        tally.complete,
        expected,
        len(in_flight),
        max(0, expected - len(runs)),
    )


def _derive_experiment_status(
    experiment: dict,
    runs: list[dict],
) -> tuple[ExperimentStatus, int]:
    expected = int(experiment.get("run_count") or 0)
    tally = tally_runs(runs)
    failed = tally.failed

    if tally.complete == expected and failed == 0:
        return ExperimentStatus.COMPLETE, failed
    if failed == expected or (failed > 0 and tally.complete == 0 and failed == len(runs)):
        return ExperimentStatus.FAILED, failed
    return ExperimentStatus.PARTIAL, failed
