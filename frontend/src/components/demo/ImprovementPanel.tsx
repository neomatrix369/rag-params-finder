/**
 * Improvement story (Slice 56 Part C2, step 3): best / median / worst similarity scores and their
 * spread, the chosen Fed Loan (Pell Grant) question, and the best and worst runs' top chunks side
 * by side. Props-driven and offline; every number comes from the exported story, never retyped.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part C2 - the improvement panel.
 */
import type { DemoStory, DemoStoryChunk } from '../../demo/demoResults';

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-paper px-3 py-2">
      <dt className="text-xs uppercase tracking-wider text-muted">{label}</dt>
      <dd className="text-lg font-semibold text-ink">{value}</dd>
    </div>
  );
}

function ChunkColumn({ heading, chunks }: { heading: string; chunks: DemoStoryChunk[] }) {
  return (
    <div className="flex-1 space-y-2">
      <h4 className="text-sm font-bold text-ink">{heading}</h4>
      {chunks.length === 0 ? (
        <p className="text-sm text-muted">No chunks were exported for this run.</p>
      ) : (
        chunks.map((chunk) => (
          <div key={`${chunk.run_id}-${chunk.position}`} className="rounded-lg border border-line bg-canvas p-3">
            <p className="text-xs font-semibold text-muted">
              #{chunk.position} · similarity score {chunk.score.toFixed(1)}
            </p>
            <p className="mt-1 text-sm text-ink">{chunk.chunk_text}</p>
          </div>
        ))
      )}
    </div>
  );
}

export default function ImprovementPanel({ story }: { story: DemoStory }) {
  const avgMovesTheOtherWay = story.best.query_avg_score < story.worst.query_avg_score;

  return (
    <section aria-label="Improvement story" className="space-y-4">
      <div>
        <h3 className="font-display text-lg font-semibold text-ink">What the best settings changed</h3>
        <p className="text-sm text-muted">
          Similarity scores across {story.run_count} runs, normalised across this export. A higher score means a
          chunk sits closer to the question in embedding space; it does not prove the chunk is the right answer.
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <StatTile label="Best top-chunk score" value={story.best.max_score.toFixed(1)} />
        <StatTile label="Median top-chunk score" value={story.median.max_score.toFixed(1)} />
        <StatTile label="Worst top-chunk score" value={story.worst.max_score.toFixed(1)} />
        <StatTile label="Top-chunk spread" value={story.spread.max_score.toFixed(1)} />
      </dl>

      <p className="text-sm text-muted">
        Query average across all questions — best {story.best.query_avg_score.toFixed(1)}, worst{' '}
        {story.worst.query_avg_score.toFixed(1)}.
      </p>

      {avgMovesTheOtherWay ? (
        <p role="note" className="rounded-lg border border-line bg-canvas p-3 text-sm text-ink">
          Runs are ranked by their top single-chunk similarity first; the average across all queries can move the
          other way, as it does here.
        </p>
      ) : null}

      <div className="rounded-lg border border-line bg-canvas p-3">
        <p className="text-xs uppercase tracking-wider text-muted">Question ({story.question.focus})</p>
        <p className="mt-1 text-sm font-medium text-ink">{story.question.text}</p>
        <p className="mt-1 text-xs text-muted">
          Top-1 similarity score {story.question.worst_top1.toFixed(1)} → {story.question.best_top1.toFixed(1)}
          {' '}(gap {story.question.gap.toFixed(1)}).
        </p>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row">
        <ChunkColumn heading="Best run — top chunks" chunks={story.best_top_chunks} />
        <ChunkColumn heading="Worst run — top chunks" chunks={story.worst_top_chunks} />
      </div>
    </section>
  );
}
