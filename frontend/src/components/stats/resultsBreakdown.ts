/**
 * Pure builders for the Query Results breakdown (Slice 67E).
 *
 * A golden record is one record of the golden dataset (one evaluation query). Each run answers
 * every golden query once, so results = runs x golden queries. top-k only sets how many chunks
 * each row holds; it never changes the row count.
 *
 * Deterministic: fixed templates plus the numbers passed in. No clock, randomness, I/O, or
 * arithmetic in JSX. Numbers are formatted with the fixed 'en-US' locale.
 */
import type { ExperimentDbStats, VectorDbGroupTotals } from '../../types';
import type { FormulaTerm } from '../../utils/sweepFormula';

export const RESULTS_ROW_NOTE =
  'One result row per query per run; top-k only sets how many chunks each row holds.';

export const INFERRED_MARKER = '(inferred)';

export const INFERRED_NOTE = `${INFERRED_MARKER} Golden count taken from the run with the most results, not read from the dataset.`;

export function formatCount(count: number): string {
  return count.toLocaleString('en-US');
}

export interface ResultsFormula {
  terms: FormulaTerm[];
  unit: 'result';
  observedTotal: number;
  /** Set when the golden count was inferred rather than read from the dataset. */
  sourceNote: string | null;
}

export type GroupResultsBreakdown =
  | ({ kind: 'uniform' } & Omit<ResultsFormula, 'sourceNote'>)
  | { kind: 'mixed'; observedTotal: number; summary: string }
  | { kind: 'unavailable' };

const isCount = (value: number | null | undefined): value is number =>
  typeof value === 'number' && Number.isFinite(value);

export function experimentResultsFormula(
  stats: Pick<
    ExperimentDbStats,
    'result_runs' | 'golden_queries' | 'golden_queries_source' | 'total_results'
  >,
): ResultsFormula | null {
  const { result_runs: runs, golden_queries: golden } = stats;
  if (!isCount(runs) || !isCount(golden)) return null;
  return {
    terms: [
      { count: runs, label: 'run' },
      { count: golden, label: 'golden query' },
    ],
    unit: 'result',
    observedTotal: stats.total_results,
    sourceNote: stats.golden_queries_source === 'max_per_run' ? INFERRED_NOTE : null,
  };
}

/** Runs below the golden count; "so far" unless the experiment is terminal. Null when nothing to say. */
export function partialRunsNote(
  stats: Pick<ExperimentDbStats, 'partial_runs'>,
  isTerminal: boolean,
): string | null {
  const partial = stats.partial_runs;
  if (!isCount(partial) || partial <= 0) return null;
  const noun = partial === 1 ? 'run' : 'runs';
  return isTerminal
    ? `${formatCount(partial)} ${noun} returned fewer results than the golden count.`
    : `${formatCount(partial)} ${noun} below the golden count so far (still running or incomplete).`;
}

export function groupResultsBreakdown(
  totals: Pick<
    VectorDbGroupTotals,
    'total_results' | 'total_result_runs' | 'golden_queries_min' | 'golden_queries_max'
  >,
): GroupResultsBreakdown {
  const { golden_queries_min: min, golden_queries_max: max, total_result_runs: runs } = totals;
  if (!isCount(min) || !isCount(max)) return { kind: 'unavailable' };
  if (min === max) {
    if (!isCount(runs)) return { kind: 'unavailable' };
    return {
      kind: 'uniform',
      terms: [
        { count: runs, label: 'run' },
        { count: min, label: 'golden query' },
      ],
      unit: 'result',
      observedTotal: totals.total_results,
    };
  }
  return {
    kind: 'mixed',
    observedTotal: totals.total_results,
    summary: `${formatCount(totals.total_results)} results (observed); experiments have ${formatCount(min)} to ${formatCount(max)} golden queries.`,
  };
}
