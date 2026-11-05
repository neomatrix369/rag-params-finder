/**
 * Demo screen (Slice 56 Part C2): the one place that hosts the cross-store leaderboard, the run
 * replay, the improvement story and the best-settings card. It is the screen the Walkthru drives,
 * and it is reachable directly from the About box's "Open the demo" button.
 *
 * Each panel carries a `data-tour` anchor so the Walkthru can spotlight it. The improvement panel
 * sits in a CollapsibleCard that starts collapsed; when the Walkthru highlights it, the `open`
 * override forces it open, and dropping the override on exit restores it to collapsed.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part C2 - demo screen + wiring.
 */
import { useState } from 'react';
import type { WalkthruResults } from '../../walkthru/walkthruResults';
import { primaryStore, suggestedRunId } from '../../walkthru/leaderboard';
import { resolveRun, toRankedConfig } from '../../walkthru/replayAdapter';
import AppPageChrome from '../chrome/AppPageChrome';
import CollapsibleCard from '../chrome/CollapsibleCard';
import { BestParamsCard } from '../explore/ExplorePanels';
import CrossStoreLeaderboard from './CrossStoreLeaderboard';
import ImprovementPanel from './ImprovementPanel';
import RunReplay from './RunReplay';

export interface WalkthruScreenProps {
  results: WalkthruResults;
  /** `data-tour` anchor the Walkthru is spotlighting, or null; drives the improvement card's open override. */
  activeHighlight?: string | null;
  /** When true (Walkthru Autoplay on) the leaderboard takes its suggested pick. */
  autoplay?: boolean;
  /** Store whose best run is suggested; defaults to the primary (Redis 8) store. */
  suggestedStore?: string;
  onBack: () => void;
}

function Panel({ tour, children }: { tour: string; children: React.ReactNode }) {
  return (
    <section data-tour={tour} className="rounded-panel border border-line bg-paper p-4 sm:p-5">
      {children}
    </section>
  );
}

export default function WalkthruScreen({ results, activeHighlight, autoplay = false, suggestedStore, onBack }: WalkthruScreenProps) {
  const [selectedRunId, setSelectedRunId] = useState<string | undefined>(undefined);
  const suggested = suggestedStore ?? primaryStore(results);
  const bestRun = resolveRun(results, suggestedRunId(results, suggested));

  return (
    <AppPageChrome
      pageEyebrow="Meetup demo"
      pageTitle="RAG settings, store by store"
      pageHint="Offline from bundled runs on the Fed Loan (Pell Grant) corpus. Scores are similarity scores, not accuracy."
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
        <Panel tour="leaderboard">
          <CrossStoreLeaderboard
            results={results}
            selectedRunId={selectedRunId}
            onSelectRun={setSelectedRunId}
            suggestedStore={suggested}
            autoplay={autoplay}
          />
        </Panel>

        <Panel tour="replay">
          <h3 className="mb-3 font-display text-lg font-semibold text-ink">Replay the chosen run</h3>
          <RunReplay results={results} runId={selectedRunId} onSelectRun={setSelectedRunId} />
        </Panel>

        <Panel tour="improvement">
          <CollapsibleCard
            title="The improvement story"
            defaultOpen={false}
            open={activeHighlight === 'improvement' ? true : undefined}
          >
            <ImprovementPanel story={results.story} />
          </CollapsibleCard>
        </Panel>

        <Panel tour="best-settings">
          <h3 className="mb-3 font-display text-lg font-semibold text-ink">The best settings</h3>
          {bestRun ? (
            <BestParamsCard
              config={toRankedConfig(bestRun)}
              scoreLabel="Similarity score"
              heading={`Best parameters on ${bestRun.store}`}
            />
          ) : (
            <p className="text-sm text-muted">No runs are bundled with this build.</p>
          )}
        </Panel>
      </main>
    </AppPageChrome>
  );
}
