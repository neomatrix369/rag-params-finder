import type { Experiment, ExperimentDbStatsSummary, VectorDbStatsGroup } from '../../../types';
import { completionReasonLabel } from '../../../utils/completionReason';

export function statusBadgeClass(status: Experiment['status']): string {
  if (status === 'complete') return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  if (status === 'running') return 'border-blue-200 bg-blue-50 text-blue-800';
  if (status === 'partial') return 'border-amber-200 bg-amber-50 text-amber-900';
  if (status === 'failed') return 'border-red-200 bg-red-50 text-red-800';
  if (status === 'cancelled') return 'border-slate-300 bg-slate-100 text-slate-800';
  if (status === 'paused') return 'border-violet-200 bg-violet-50 text-violet-800';
  return 'border-line bg-canvas text-ink';
}

export function statusEdgeClass(status: Experiment['status']): string {
  if (status === 'complete') return 'border-l-emerald-500';
  if (status === 'running') return 'border-l-blue-500';
  if (status === 'partial') return 'border-l-amber-500';
  if (status === 'failed') return 'border-l-red-500';
  if (status === 'paused') return 'border-l-violet-500';
  return 'border-l-slate-400';
}

export function resolveSearchStrategy(experiment: Experiment): 'grid' | 'bayesian' {
  const configExecution = (experiment.config as { execution?: Record<string, unknown> } | undefined)?.execution;
  if (!configExecution || typeof configExecution !== 'object') {
    return 'grid';
  }
  const searchStrategy = configExecution['search_strategy'];
  if (searchStrategy === 'bayesian' || searchStrategy === 'grid') {
    return searchStrategy;
  }
  return 'grid';
}

export function experimentOutcomeLabel(experiment: Experiment): string {
  const bayesianSummary = experiment.bayesian_summary;
  const configuredRuns = experiment.run_count == null
    ? 'Run count pending'
    : `${experiment.run_count} run${experiment.run_count === 1 ? '' : 's'} configured`;
  const isBayesianStrategy = resolveSearchStrategy(experiment) === 'bayesian';
  const plannedTrials = bayesianSummary?.planned_trials;
  const attemptedTrials = bayesianSummary?.attempted_trials;
  const discardedTrials = bayesianSummary?.discarded_trials;
  const notStartedTrials = bayesianSummary?.not_started;
  const reasonSuffix = experiment.completion_reason
    ? ` · ${completionReasonLabel(experiment.completion_reason)}`
    : '';
  const hasBayesianIncomplete =
    isBayesianStrategy && plannedTrials != null && attemptedTrials != null && attemptedTrials < plannedTrials;
  if (experiment.status === 'running') return `${configuredRuns} · sweep in progress`;
  if (experiment.status === 'paused') return `${configuredRuns} · waiting to resume`;
  if (experiment.status === 'complete') {
    if (hasBayesianIncomplete) {
      const notStarted = Math.max(
        0,
        (notStartedTrials ?? plannedTrials ?? 0) - (attemptedTrials ?? 0) - (discardedTrials ?? 0),
      );
      const notStartedSuffix = notStarted > 0 ? ` · ${notStarted} not started` : '';
      return `${configuredRuns} · Bayesian: ${attemptedTrials} attempted · ${discardedTrials ?? 0} discarded`
        + notStartedSuffix
        + reasonSuffix;
    }
    if (experiment.completion_reason && experiment.completion_reason !== 'all_planned_trials_completed') {
      return `${configuredRuns} · sweep complete · ${completionReasonLabel(experiment.completion_reason)}`;
    }
    return `${configuredRuns} · sweep complete`;
  }
  if (experiment.status === 'partial' && resolveSearchStrategy(experiment) === 'bayesian') {
    const discarded = bayesianSummary?.discarded_trials ?? 0;
    const attempted = bayesianSummary?.attempted_trials;
    if (attempted == null) {
      return `${configuredRuns} · Bayesian sampling incomplete${reasonSuffix}`;
    }
    const notStarted = Math.max(0, (notStartedTrials ?? plannedTrials ?? 0) - attempted - discarded);
    const notStartedSuffix = notStarted > 0 ? ` · ${notStarted} not started` : '';
    return `${configuredRuns} · Bayesian: ${attempted} attempted · ${discarded} discarded${notStartedSuffix}${reasonSuffix}`;
  }
  if (experiment.status === 'partial') return `${configuredRuns} · incomplete outcome${reasonSuffix}`;
  if (experiment.status === 'cancelled') return `${configuredRuns} · collection stopped`;
  if (experiment.failed_count) return `${configuredRuns} · ${experiment.failed_count} failed`;
  return `${configuredRuns} · sweep failed`;
}

export function experimentStatsMap(groups: VectorDbStatsGroup[]): Map<string, ExperimentDbStatsSummary> {
  const map = new Map<string, ExperimentDbStatsSummary>();
  for (const group of groups) {
    for (const exp of group.experiments) {
      map.set(exp.experiment_id, exp);
    }
  }
  return map;
}

/** True only for the first experiment-list load — not for background polls. */
export function shouldShowLoadingPanel(
  initialLoadDone: boolean,
  loading: boolean,
  error: string | null,
): boolean {
  if (error !== null) return false;
  return !initialLoadDone || loading;
}
