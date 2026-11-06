/**
 * Live "Compare sweeps" screen (Slice 66): fetches `GET /api/v1/compare` once when it mounts
 * (only reachable via the Experiments button) and shows the result in the cross-store leaderboard.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-66 dashboard - compare screen with loading, error + retry, empty and populated states.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { getCompare } from '../../services/apiClient';
import type { CompareResponse } from '../../types';
import { compareToLeaderboard } from '../../walkthru/leaderboard';
import AppPageChrome from '../chrome/AppPageChrome';
import CrossStoreLeaderboard from '../walkthru/CrossStoreLeaderboard';

const LIVE_DESCRIPTION =
  'Completed sweeps grouped by identical config. Scores are normalised within each group (similarity only, not accuracy), so compare rows inside a group.';

type State = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; data: CompareResponse };

export default function CompareScreen({ onBack }: { onBack: () => void }) {
  const [state, setState] = useState<State>({ kind: 'loading' });
  const [attempt, setAttempt] = useState(0);
  const [selectedRunId, setSelectedRunId] = useState<string | undefined>(undefined);

  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: 'loading' });
    getCompare(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ kind: 'ready', data });
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setState({ kind: 'error', message: err instanceof Error ? err.message : 'Failed to load sweep comparison' });
      });
    return () => controller.abort();
  }, [attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  const results = useMemo(() => (state.kind === 'ready' ? compareToLeaderboard(state.data) : null), [state]);

  return (
    <AppPageChrome
      pageEyebrow="Sweep workspace"
      pageTitle="Compare sweeps"
      pageHint="Live results from your completed sweeps, grouped by config."
      showDashboardFootnote={false}
      topRight={
        <button
          type="button"
          onClick={onBack}
          className="min-h-11 rounded-lg border border-line bg-paper px-3 text-sm font-semibold text-ink hover:border-accent"
        >
          Back to experiments
        </button>
      }
    >
      <main className="mx-auto max-w-7xl space-y-5 px-4 py-6 sm:px-6">
        {state.kind === 'loading' ? (
          <p role="status" className="text-sm text-muted">Loading sweep comparison…</p>
        ) : null}
        {state.kind === 'error' ? (
          <div role="alert" className="space-y-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            <p>{state.message}</p>
            <button
              type="button"
              onClick={retry}
              className="min-h-11 rounded-lg border border-line bg-paper px-3 text-sm font-semibold text-ink hover:border-accent"
            >
              Retry
            </button>
          </div>
        ) : null}
        {state.kind === 'ready' && state.data.run_count === 0 ? (
          <p role="note" className="rounded-lg border border-line bg-canvas p-3 text-sm text-ink">
            No completed sweeps to compare yet
          </p>
        ) : null}
        {results && state.kind === 'ready' && state.data.run_count > 0 ? (
          <section className="rounded-panel border border-line bg-paper p-4 sm:p-5">
            <CrossStoreLeaderboard
              results={results}
              selectedRunId={selectedRunId}
              onSelectRun={setSelectedRunId}
              suggest={false}
              description={LIVE_DESCRIPTION}
              collapsedDuplicates={state.data.duplicates_collapsed}
              rankScope="group"
            />
          </section>
        ) : null}
      </main>
    </AppPageChrome>
  );
}
