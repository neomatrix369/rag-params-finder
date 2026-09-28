import type { ReactNode } from 'react';
import type { ExperimentDbStats } from '../../types';

type ExperimentStoredFootprintProps = {
  stats?: ExperimentDbStats;
  loading?: boolean;
};

const RUN_PREVIEW = 4;

function hasStoredData(stats: ExperimentDbStats): boolean {
  return stats.total_chunks > 0 || stats.run_breakdown.length > 0 || stats.embedding_models.length > 0;
}

export default function ExperimentStoredFootprint({
  stats,
  loading = false,
}: ExperimentStoredFootprintProps) {
  return (
    <section className="mt-8 border-t border-line pt-6" aria-labelledby="stored-footprint-title">
      <p className="text-xs font-bold uppercase tracking-widest text-accent-strong">This experiment</p>
      <h2 id="stored-footprint-title" className="mt-1 font-display text-xl font-semibold text-ink">
        Stored footprint
      </h2>
      <FootprintBody stats={stats} loading={loading} />
    </section>
  );
}

function FootprintBody({ stats, loading }: ExperimentStoredFootprintProps) {
  if (loading && !stats) {
    return <p className="mt-2 text-sm text-muted">Loading stored footprint…</p>;
  }
  if (!stats || !hasStoredData(stats)) {
    return <p className="mt-2 text-sm text-muted">Stored footprint appears after chunks are stored.</p>;
  }

  const runPreview = stats.run_breakdown.slice(0, RUN_PREVIEW);
  const hiddenRuns = stats.run_breakdown.length - runPreview.length;
  const chunkingRows = Object.entries(stats.chunking_breakdown);

  return (
    <div className="mt-3 space-y-3 rounded-lg border border-indigo-100 bg-indigo-50/60 px-4 py-3">
      <p className="text-sm font-semibold text-indigo-800">
        {stats.total_chunks.toLocaleString()} chunks · {stats.estimated_storage_mb} MB
      </p>
      <FootprintList title="Models" empty={stats.embedding_models.length === 0}>
        {stats.embedding_models.map((model) => (
          <span key={model} className="font-mono text-xs text-slate-800">
            {model}
          </span>
        ))}
      </FootprintList>
      <FootprintList title="Chunking" empty={chunkingRows.length === 0}>
        {chunkingRows.map(([method, count]) => (
          <span key={method} className="text-xs text-slate-800">
            {method} {count.toLocaleString()}
          </span>
        ))}
      </FootprintList>
      <div>
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Per run</p>
        {runPreview.length === 0 ? (
          <p className="mt-1 text-xs text-slate-500">—</p>
        ) : (
          <ul className="mt-1 space-y-1">
            {runPreview.map((run) => (
              <li key={run.run_id} className="flex justify-between gap-3 text-xs">
                <span className="truncate font-mono text-slate-600">{run.run_id.slice(0, 8)}…</span>
                <span className="shrink-0 text-slate-800">
                  {run.chunks.toLocaleString()} chunks · {run.results.toLocaleString()} results
                </span>
              </li>
            ))}
          </ul>
        )}
        {hiddenRuns > 0 ? (
          <p className="mt-1 text-[11px] text-slate-500">
            + {hiddenRuns} more run{hiddenRuns === 1 ? '' : 's'}
          </p>
        ) : null}
      </div>
    </div>
  );
}

function FootprintList({
  title,
  empty,
  children,
}: {
  title: string;
  empty: boolean;
  children: ReactNode;
}) {
  return (
    <div>
      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{title}</p>
      {empty ? (
        <p className="mt-1 text-xs text-slate-500">—</p>
      ) : (
        <div className="mt-1 flex flex-wrap gap-2">{children}</div>
      )}
    </div>
  );
}
