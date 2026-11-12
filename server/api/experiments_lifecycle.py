"""Experiment list/detail lifecycle helpers (Bayesian summary + stale status).

Extracted from ``server.api.experiments`` (Slice 45 fat-surface slim).
"""

from __future__ import annotations

import warnings
from datetime import UTC, datetime
from typing import SupportsInt, cast

from server.core.pipeline.experiment_control import is_sweep_in_flight
from server.core.pipeline.outcome import CompletionReason, RunTally, tally_runs
from server.db.ports.storage import StorageBackend
from server.db.ports.store_factory import get_storage_backend
from server.models.config import (
    ExperimentConfig,
    expand_sweep,
    resolve_bayesian_n_trials,
    retriever_labels,
    sweep_plan,
)
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
        return resolve_bayesian_n_trials(config)
    return len(expand_sweep(config))


_plan_failures_logged: set[str] = set()


def attach_sweep_plan(experiment: dict) -> None:
    """Decorate ``experiment`` in place with ``sweep_plan`` and ``sweep_summary.retrievers``.

    Computed on read from ``experiment["config"]`` so experiments stored before
    Slice 67B are covered. Purely additive: any failure (unparseable or
    registry-stale config, sweep-history docs) leaves the doc untouched and never
    raises, because GET /experiments/{id} is polled every 2 s. The failure is
    logged once per experiment per process; that permanent suppression is intentional
    (polling must not spam). The broad ``except Exception`` also covers programming
    errors, which is why the single warning keeps ``exc_info``. Only the pure
    ``sweep_plan`` is used here (never ``resolve_bayesian_n_trials``, which logs).
    """
    raw = experiment.get("config")
    if not isinstance(raw, dict):
        return
    try:
        with warnings.catch_warnings():
            # Validators re-emit config warnings; sweep_plan["warnings"] carries them.
            warnings.simplefilter("ignore")
            config = ExperimentConfig.model_validate(raw)
        plan = sweep_plan(config)
        labels = retriever_labels(config)
    except Exception as exc:
        key = str(experiment.get("experiment_id") or experiment.get("_id"))
        if key not in _plan_failures_logged:
            _plan_failures_logged.add(key)
            logger.warning(
                "sweep_plan skipped — %s: %s",
                key,
                str(exc).splitlines()[0] if str(exc) else type(exc).__name__,
                exc_info=True,
            )
        return
    experiment["sweep_plan"] = plan
    summary = experiment.get("sweep_summary")
    if isinstance(summary, dict):
        summary.setdefault("retrievers", labels)


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

    discarded_trials = _to_non_negative_int(existing_summary.get("discarded_trials", 0)) or 0

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


def _classify_without_failures(expected: int, tally: RunTally) -> tuple[ExperimentStatus, str]:
    """Pure: outcome when no run failed. ``tally.failed`` is 0."""
    complete, interrupted = tally.complete, tally.interrupted
    if complete == expected:
        return ExperimentStatus.COMPLETE, CompletionReason.ALL_PLANNED_TRIALS_COMPLETED.value
    if interrupted == 0 and complete < expected and complete > 0:
        return ExperimentStatus.COMPLETE, CompletionReason.COMPLETED_WITH_SAMPLING_SHORTFALL.value
    if expected == 0:
        # Preserves the historic ``failed == expected`` arm, which with no
        # failures can only fire for an experiment that planned 0 runs.
        return ExperimentStatus.FAILED, CompletionReason.ALL_TRIALS_FAILED.value
    if interrupted > 0 and complete > 0:
        return ExperimentStatus.PARTIAL, CompletionReason.INTERRUPTED_BEFORE_COMPLETION.value
    # Owned by startup_reconciliation's vocabulary, not CompletionReason.
    return ExperimentStatus.PARTIAL, "incomplete_before_completion"


def _classify_with_failures(
    expected: int,
    total_runs: int,
    tally: RunTally,
) -> tuple[ExperimentStatus, str]:
    """Pure: outcome when at least one run failed."""
    if tally.failed == expected or (tally.complete == 0 and tally.failed == total_runs):
        return ExperimentStatus.FAILED, CompletionReason.ALL_TRIALS_FAILED.value
    return ExperimentStatus.PARTIAL, CompletionReason.PARTIAL_FAILURES.value


def _classify_stale_outcome(
    expected: int,
    total_runs: int,
    tally: RunTally,
) -> tuple[ExperimentStatus, str]:
    """Pure: resolved status + ``completion_reason`` for an all-terminal run set."""
    if tally.failed == 0:
        return _classify_without_failures(expected, tally)
    return _classify_with_failures(expected, total_runs, tally)


def _stale_outcome(
    experiment: dict,
    runs: list[dict],
) -> tuple[ExperimentStatus, str, int] | None:
    """Pure query: ``(status, completion_reason, failed_count)``, or None if unresolvable.

    Unresolvable means there are no runs at all, or at least one run has not
    reached a terminal phase.
    """
    if not runs:
        return None
    if any(run.get("phase") not in _TERMINAL_PHASES for run in runs):
        return None
    tally = tally_runs(runs)
    expected = int(experiment.get("run_count") or 0)
    status, reason = _classify_stale_outcome(expected, len(runs), tally)
    return status, reason, tally.failed


def _persist_stale_outcome(
    experiment: dict,
    experiment_id: str,
    outcome: tuple[ExperimentStatus, str, int],
    storage: StorageBackend | None = None,
) -> None:
    """Command: write the resolved fields to storage and onto ``experiment`` in place."""
    status, completion_reason, failed_count = outcome
    resolved = {
        "status": status,
        "failed_count": failed_count,
        "completion_reason": completion_reason,
        "completed_at": datetime.now(UTC),
    }
    if storage is None:
        storage = get_storage_backend()
    storage.update_experiment(experiment_id, resolved)
    experiment.update(resolved)


def _normalize_stale_running_status(experiment: dict) -> dict:
    """If status is still RUNNING but no active sweep exists, reconcile from run status.

    Mutates ``experiment`` in place (both callers in ``server.api.experiments``
    ignore the return value) and also returns it.
    """
    runs = experiment.get("runs")
    if not isinstance(runs, list):
        runs = []
    experiment_id = cast(str, experiment.get("experiment_id") or experiment.get("_id"))
    # A sweep still in flight keeps its RUNNING status; expose Bayesian progress
    # only and never touch storage.
    stale = bool(
        experiment.get("status") == ExperimentStatus.RUNNING
        and experiment_id
        and not is_sweep_in_flight(experiment_id)
    )

    storage = None
    if stale:
        runs = list(runs)
        if not runs:
            storage = get_storage_backend()
            runs = storage.find_run_statuses(experiment_id)

    _ensure_bayesian_summary(experiment, runs=runs)

    outcome = _stale_outcome(experiment, runs) if stale else None
    if outcome is not None:
        _persist_stale_outcome(experiment, experiment_id, outcome, storage)
    return experiment
