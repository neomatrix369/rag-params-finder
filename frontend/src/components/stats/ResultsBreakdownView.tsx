import FormulaLine from '../chrome/FormulaLine';
import type { ExperimentDbStats, VectorDbGroupTotals } from '../../types';
import {
  RESULTS_ROW_NOTE,
  experimentResultsFormula,
  formatCount,
  groupResultsBreakdown,
  partialRunsNote,
} from './resultsBreakdown';

/** Experiment-level breakdown; renders nothing when the golden facts are unknown. */
export function ExperimentResultsBreakdown({
  stats,
  isTerminal,
}: {
  stats: ExperimentDbStats;
  isTerminal: boolean;
}) {
  const formula = experimentResultsFormula(stats);
  if (!formula) return null;
  const partial = partialRunsNote(stats, isTerminal);
  return (
    <div data-testid="results-breakdown" className="space-y-1 break-words text-xs text-slate-800">
      <p data-testid="results-formula" className="font-semibold">
        <FormulaLine
          terms={formula.terms}
          unit={formula.unit}
          observedTotal={formula.observedTotal}
          formatCount={formatCount}
        />
      </p>
      <p className="text-[11px] text-slate-500">{RESULTS_ROW_NOTE}</p>
      {formula.sourceNote ? (
        <p data-testid="results-source-note" className="text-[11px] text-slate-500">{formula.sourceNote}</p>
      ) : null}
      {partial ? (
        <p data-testid="results-partial-note" className="text-[11px] text-amber-700">{partial}</p>
      ) : null}
    </div>
  );
}

/** Group-level hint for the Query Results tile; undefined when the golden facts are unavailable. */
export function GroupResultsHint({ totals }: { totals: VectorDbGroupTotals }) {
  const breakdown = groupResultsBreakdown(totals);
  if (breakdown.kind === 'unavailable') return null;
  return (
    <span data-testid="results-group-hint" className="block space-y-1 break-words">
      <span className="block">
        {breakdown.kind === 'uniform' ? (
          <FormulaLine
            terms={breakdown.terms}
            unit={breakdown.unit}
            observedTotal={breakdown.observedTotal}
            formatCount={formatCount}
          />
        ) : (
          breakdown.summary
        )}
      </span>
      <span className="block">{RESULTS_ROW_NOTE}</span>
    </span>
  );
}
