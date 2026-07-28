const COMPLETION_REASONS: Record<string, string> = {
  all_planned_trials_completed: 'all planned trials completed',
  completed_with_sampling_shortfall: 'completed with sampling shortfall',
  all_trials_failed: 'all trials failed',
  partial_failures: 'partial with failures',
  interrupted_before_completion: 'interrupted before completion',
  cancelled_by_user: 'cancelled by user',
  paused_by_user: 'paused by user',
  incomplete_before_completion: 'incomplete before completion',
  incomplete_with_zero_runs: 'incomplete before completion',
  incomplete_without_runs: 'incomplete before completion',
  reconciled_from_orphaned_run: 'reconciled from orphaned run',
  partial_with_failures: 'partial with failures',
  partial_outcomes: 'partial outcomes',
  mixed_outcomes: 'mixed outcomes',
  mixed_failures: 'mixed failures',
  infrastructure_error: 'infrastructure error',
  paused_or_interrupted_before_completion: 'interrupted before completion',
  completed_with_shortfall: 'completed with sampling shortfall',
  resolved_stale_running: 'reconciled from stale running state',
  incomplete_by_partial_outcomes: 'incomplete outcome',
  cancelled_before_attempt: 'cancelled before attempts',
};

/** Human-readable label for experiment `completion_reason` codes. */
export function completionReasonLabel(reason?: string | null): string {
  if (!reason) return 'completion state recorded';
  // reason is a typed string from our API catalog — safe keyed lookup.
  // eslint-disable-next-line security/detect-object-injection -- keyed by known completion_reason codes
  const mapped = COMPLETION_REASONS[reason];
  if (mapped !== undefined) return mapped;
  return reason.replace(/_/g, ' ');
}
