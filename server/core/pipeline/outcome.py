"""Shared vocabulary for sweep outcome derivation.

Owns two things the orchestrator used to re-express inline:

* ``CompletionReason`` — the closed set of ``completion_reason`` strings that
  ``orchestrator.py`` persists on an experiment. Values are the exact strings
  already emitted; the dashboard maps them in
  ``frontend/src/utils/completionReason.ts``.
* ``RunTally`` / ``tally_runs`` — one counting pass over run-status documents,
  replacing the repeated ``sum(1 for run in runs if run.get("phase") == ...)``
  expressions.

The *decision rules* stay with their call sites in ``orchestrator.py``: the
grid finaliser, the Bayesian finaliser and the startup reconciler apply
different rules over the same tally, and merging them would change behaviour.
``server/core/pipeline/startup_reconciliation.py`` owns its own additional
reason strings (``mixed_failures``, ``incomplete_before_completion``,
``reconciled_from_orphaned_run``, ``pre_embed_batches_cannot_be_resumed``,
``doubleword_api_key_removed``) and is not covered by this enum.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from server.models.enums import Phase


class CompletionReason(StrEnum):
    """Every ``completion_reason`` value ``orchestrator.py`` writes."""

    ALL_PLANNED_TRIALS_COMPLETED = "all_planned_trials_completed"
    ALL_TRIALS_FAILED = "all_trials_failed"
    CANCELLED_BEFORE_ATTEMPT = "cancelled_before_attempt"
    CANCELLED_BY_USER = "cancelled_by_user"
    COMPLETED_WITH_SAMPLING_SHORTFALL = "completed_with_sampling_shortfall"
    INFRASTRUCTURE_ERROR = "infrastructure_error"
    INTERRUPTED_BEFORE_COMPLETION = "interrupted_before_completion"
    MIXED_OUTCOMES = "mixed_outcomes"
    PARTIAL_COMPLETION = "partial_completion"
    PARTIAL_FAILURES = "partial_failures"
    PARTIAL_OUTCOMES = "partial_outcomes"
    PAUSED_BY_USER = "paused_by_user"
    PAUSED_OR_INTERRUPTED_BEFORE_COMPLETION = "paused_or_interrupted_before_completion"


@dataclass(frozen=True, slots=True)
class RunTally:
    """Phase counts for one experiment's run-status documents."""

    complete: int = 0
    failed: int = 0
    interrupted: int = 0


def tally_runs(runs: Iterable[Mapping[str, Any]]) -> RunTally:
    """Count COMPLETE / FAILED / INTERRUPTED runs in a single pass.

    Reads ``run.get("phase")`` against the stored phase value, exactly as the
    inline comprehensions it replaces did.
    """
    complete = failed = interrupted = 0
    for run in runs:
        phase = run.get("phase")
        if phase == Phase.COMPLETE.value:
            complete += 1
        elif phase == Phase.FAILED.value:
            failed += 1
        elif phase == Phase.INTERRUPTED.value:
            interrupted += 1
    return RunTally(complete=complete, failed=failed, interrupted=interrupted)
