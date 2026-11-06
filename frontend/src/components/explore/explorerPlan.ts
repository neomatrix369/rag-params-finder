/**
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67G-B - the Explorer's planned total and sweep formula, derived from the server's
 * sweep_plan (pure: no clock, I/O or DOM). Reuses the Detail screen's denominator helper so both agree.
 */
import type { Experiment } from '../../types';
import { detailDenominator } from '../../utils/experimentStatus';
import { sweepFormulaFromSummary, sweepNote, type SweepFormula } from '../../utils/sweepFormula';

export type ExplorerPlanSource = Partial<
  Pick<Experiment, 'sweep_plan' | 'sweep_summary' | 'run_count' | 'bayesian_summary' | 'config'>
>;

export interface ExplorerPlan {
  /** M in "N of M planned have results"; null when the response carries no plan or run count. */
  plannedTotal: number | null;
  isBayesian: boolean;
  /** Planned dimensions as terms; null when the response has no sweep_summary. */
  formula: SweepFormula | null;
  /** Fixed note that qualifies the formula for a Bayesian sweep. */
  note: string | null;
}

type Strategy = 'grid' | 'bayesian' | undefined;

/** Same precedence as the Detail screen: the plan, then config.execution. */
function searchStrategy(source: ExplorerPlanSource): Strategy {
  const execution = source.config?.execution as { search_strategy?: Strategy } | undefined;
  return source.sweep_plan?.search_strategy ?? execution?.search_strategy;
}

export function explorerPlan(source: ExplorerPlanSource | null): ExplorerPlan {
  const known = source ?? {};
  const strategy = searchStrategy(known);
  const isBayesian = strategy === 'bayesian';
  const plannedTrials = known.sweep_plan?.planned_runs ?? known.bayesian_summary?.planned_trials ?? known.run_count;
  const expectedRuns = known.sweep_plan?.full_grid_count ?? known.run_count;
  const plannedTotal =
    plannedTrials === undefined || expectedRuns === undefined
      ? null
      : detailDenominator({ isBayesian, plannedTrials, expectedRuns });
  return {
    plannedTotal,
    isBayesian,
    formula: known.sweep_summary ? sweepFormulaFromSummary(known.sweep_summary) : null,
    note: sweepNote(strategy),
  };
}
