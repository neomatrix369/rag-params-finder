"""Reconcile experiments left in RUNNING after server restart or crash."""

from datetime import UTC, datetime

from server.db.atlas import EXPERIMENTS_COLLECTION, RUN_STATUS_COLLECTION, get_collection
from server.models.enums import ExperimentStatus, Phase
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

    Returns the number of experiments reconciled.
    """
    exp_coll = get_collection(EXPERIMENTS_COLLECTION)
    running = list(exp_coll.find({"status": ExperimentStatus.RUNNING}))
    if not running:
        return 0

    run_coll = get_collection(RUN_STATUS_COLLECTION)
    reconciled = 0
    for experiment in running:
        experiment_id = str(experiment["_id"])
        _reconcile_one(experiment_id, experiment, run_coll, exp_coll)
        reconciled += 1

    logger.info("Reconciled %s orphaned experiment(s) left in RUNNING", reconciled)
    return reconciled


def _reconcile_one(
    experiment_id: str,
    experiment: dict,
    run_coll,
    exp_coll,
) -> None:
    runs = list(run_coll.find({"experiment_id": experiment_id}))
    in_flight = [run for run in runs if run.get("phase") not in _TERMINAL_RUN_PHASES]
    now = datetime.now(UTC)

    for run in in_flight:
        run_coll.update_one(
            {"run_id": run["run_id"]},
            {
                "$set": {
                    "phase": Phase.INTERRUPTED.value,
                    "updated_at": now,
                    "error_message": _ORPHAN_ERROR,
                }
            },
        )
        logger.warning(
            "Marked run %s interrupted (was %s) for experiment %s",
            run["run_id"],
            run.get("phase"),
            experiment_id,
        )

    runs = list(run_coll.find({"experiment_id": experiment_id}))
    status, failed_count = _derive_experiment_status(experiment, runs)
    complete_count = sum(1 for run in runs if run.get("phase") == Phase.COMPLETE.value)
    expected = int(experiment.get("run_count") or 0)

    exp_coll.update_one(
        {"_id": experiment_id},
        {
            "$set": {
                "status": status,
                "failed_count": failed_count,
                "completed_at": now,
            }
        },
    )
    logger.info(
        "Experiment %s reconciled → %s (%s/%s runs complete, %s interrupted in-flight, "
        "%s never started)",
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
