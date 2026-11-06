/**
 * Pure explanation sentences for the experiments list (Slice 67G).
 *
 * Deterministic: fixed templates plus the numbers passed in. No clock, randomness, I/O, or
 * arithmetic in JSX; the screen renders what these functions return through InfoTip.
 */
import type { Experiment } from '../../../types';
import { bayesianNotStartedCount, bayesianTotalsLine } from '../../../utils/experimentStatus';
import { plannedRunCount, resolveSearchStrategy } from './labels';

const plural = (count: number, one: string, many: string): string => (count === 1 ? one : many);

export function experimentsCountExplain(total: number): string {
  return `${total} ${plural(total, 'experiment is', 'experiments are')} stored on the server. Each experiment is one submitted config and expands into many runs, so this is not a count of runs.`;
}

export function pageRange(page: number, perPage: number, total: number): { start: number; end: number } {
  return { start: (page - 1) * perPage + 1, end: Math.min(page * perPage, total) };
}

export function paginationExplain(page: number, perPage: number, total: number): string {
  const { start, end } = pageRange(page, perPage, total);
  return `Showing ${start}–${end} of ${total} experiments, ${perPage} per page. Pagination counts experiments, not runs.`;
}

export function plannedRunsExplain(experiment: Experiment): string {
  const planned = plannedRunCount(experiment);
  if (planned == null) return 'The server has not reported how many runs this experiment plans yet.';
  if (resolveSearchStrategy(experiment) === 'bayesian') {
    return `${planned} Bayesian ${plural(planned, 'trial is', 'trials are')} planned: the sampler tries up to this many configurations instead of the full grid. Attempted, discarded and not started trials are counted separately.`;
  }
  return `${planned} ${plural(planned, 'run is', 'runs are')} planned: the product of the sweep's configuration dimensions. This is the plan, not how many have run.`;
}

export function failedRunsExplain(failed: number, runCount: number | null | undefined): string {
  if (runCount == null) return `${failed} ${plural(failed, 'run ended', 'runs ended')} in failure.`;
  return `${failed} of the ${runCount} planned runs ended in failure.`;
}

export function bayesianCountsExplain(planned: number, attempted: number, discarded: number): string {
  return bayesianTotalsLine({
    planned,
    attempted,
    discarded,
    notStarted: bayesianNotStartedCount(planned, attempted, discarded),
  });
}

/** Bayesian trial split for a list row; null when the row is not Bayesian or the counts are not reported yet. */
export function experimentBayesianExplain(experiment: Experiment): string | null {
  const summary = experiment.bayesian_summary;
  if (resolveSearchStrategy(experiment) !== 'bayesian') return null;
  if (summary?.planned_trials == null || summary.attempted_trials == null) return null;
  return bayesianCountsExplain(summary.planned_trials, summary.attempted_trials, summary.discarded_trials ?? 0);
}

export const RUNNING_DELETE_EXPLAIN =
  'A running experiment cannot be selected for deletion. Wait for it to finish or stop it first.';
