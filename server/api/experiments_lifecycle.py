"""Experiment list/detail lifecycle helpers (Bayesian summary + stale status).

Extracted from ``server.api.experiments`` (Slice 45 fat-surface slim).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import SupportsInt, cast

from server.core.pipeline.experiment_control import is_sweep_in_flight
from server.db.ports.store_factory import get_storage_backend
from server.models.config import ExperimentConfig, expand_sweep
from server.models.enums import ExperimentStatus, Phase
from server.utils.logger import get_logger

logger = get_logger(__name__)

_TERMINAL_PHASES = frozenset(
    {
        Phase.COMPLETE.value,
        Phase.FAILED.value,
        Phase.INTERRUPTED.value,
    }
)


def _planned_run_count(config: ExperimentConfig) -> int:
    if config.execution.search_strategy == "bayesian":
        return _resolve_bayesian_n_trials(config)
    return len(expand_sweep(config))


def _resolve_bayesian_n_trials(config: ExperimentConfig) -> int:
    grid_equivalent = len(config.chunking.params.chunk_sizes) * len(config.chunking.params.overlaps)
    configured = config.execution.bayesian.n_trials
    if configured is None:
        logger.info(
            "bayesian n_trials not set; defaulting to grid-equivalent %s",
            grid_equivalent,
        )
        return grid_equivalent
    if configured > grid_equivalent:
        logger.warning(
            "requested bayesian n_trials=%s exceeds grid-equivalent=%s, capping at grid-equivalent",
            configured,
            grid_equivalent,
        )
        return grid_equivalent
    return configured


def _to_non_negative_int(value: object) -> int | None:
    try:
        as_int = int(cast(SupportsInt, value))
    except (TypeError, ValueError):
        return None
    return max(0, int(as_int))


def _is_bayesian_experiment(experiment: dict) -> bool:
    config = experiment.get("config")
    if not isinstance(config, dict):
        return False
    execution = config.get("execution")
    if not isinstance(execution, dict):
        return False
    return execution.get("search_strategy") == "bayesian"


def _ensure_bayesian_summary(
    experiment: dict,
    runs: list[dict] | None = None,
) -> None:
    if not _is_bayesian_experiment(experiment):
        return

    planned_trials = _to_non_negative_int(experiment.get("run_count"))
    if planned_trials is None:
        return

    existing_summary = experiment.get("bayesian_summary")
    if not isinstance(existing_summary, dict):
        existing_summary = {}

    planned_trials = int(planned_trials)
    attempted_trials = existing_summary.get("attempted_trials")
    if isinstance(attempted_trials, int):
        attempted_trials = _to_non_negative_int(attempted_trials) or 0
    elif isinstance(runs, list):
        attempted_trials = len(runs)
    else:
        attempted_trials = 0

    if "discarded_trials" in existing_summary:
        discarded_trials = _to_non_negative_int(existing_summary["discarded_trials"]) or 0
    else:
        discarded_trials = existing_summary.get("discarded_trials", 0)
        discarded_trials = _to_non_negative_int(discarded_trials) or 0

    not_started = max(
        0,
        planned_trials - attempted_trials - discarded_trials,
    )

    existing_summary.update(
        {
            "planned_trials": planned_trials,
            "attempted_trials": attempted_trials,
            "discarded_trials": discarded_trials,
            "grid_equivalent_count": _to_non_negative_int(
                existing_summary.get("grid_equivalent_count")
            )
            or _to_non_negative_int(experiment.get("grid_equivalent_count"))
            or planned_trials,
            "not_started": not_started,
        }
    )
    experiment["bayesian_summary"] = existing_summary


def _normalize_stale_running_status(experiment: dict) -> dict:
    """If status is still RUNNING but no active sweep exists, reconcile from run status."""
    runs = experiment.get("runs")
    if not isinstance(runs, list):
        runs = []
    if experiment.get("status") != ExperimentStatus.RUNNING:
        _ensure_bayesian_summary(experiment, runs=runs)
        return experiment

    experiment_id = experiment.get("experiment_id") or experiment.get("_id")
    if not experiment_id or is_sweep_in_flight(experiment_id):
        # Still expose Bayesian progress while a sweep is in flight; do not touch storage.
        _ensure_bayesian_summary(experiment, runs=runs)
        return experiment

    runs = list(runs)
    storage = None
    if not runs:
        storage = get_storage_backend()
        runs = storage.find_run_statuses(experiment_id)
    _ensure_bayesian_summary(experiment, runs=runs)
    if not runs:
        return experiment

    if any(run.get("phase") not in _TERMINAL_PHASES for run in runs):
        return experiment

    expected = int(experiment.get("run_count") or 0)
    complete = sum(1 for run in runs if run.get("phase") == Phase.COMPLETE.value)
    failed = sum(1 for run in runs if run.get("phase") == Phase.FAILED.value)
    interrupted = sum(1 for run in runs if run.get("phase") == Phase.INTERRUPTED.value)

    if complete == expected and failed == 0:
        resolved_status = ExperimentStatus.COMPLETE
        completion_reason = "all_planned_trials_completed"
    elif failed == 0 and interrupted == 0 and complete < expected and complete > 0:
        resolved_status = ExperimentStatus.COMPLETE
        completion_reason = "completed_with_sampling_shortfall"
    elif failed == expected or (failed > 0 and complete == 0 and failed == len(runs)):
        resolved_status = ExperimentStatus.FAILED
        completion_reason = "all_trials_failed"
    elif failed == 0 and interrupted > 0 and complete > 0:
        resolved_status = ExperimentStatus.PARTIAL
        completion_reason = "interrupted_before_completion"
    elif failed > 0:
        resolved_status = ExperimentStatus.PARTIAL
        completion_reason = "partial_failures"
    else:
        resolved_status = ExperimentStatus.PARTIAL
        completion_reason = "incomplete_before_completion"

    now = datetime.now(UTC)
    resolved = {
        "status": resolved_status,
        "failed_count": failed,
        "completion_reason": completion_reason,
        "completed_at": now,
    }
    if storage is None:
        storage = get_storage_backend()
    storage.update_experiment(experiment_id, resolved)
    experiment.update(resolved)
    _ensure_bayesian_summary(experiment, runs=runs)
    return experiment
