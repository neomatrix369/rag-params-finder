import CollapsibleCard from './CollapsibleCard';
import type { ReactNode } from 'react';
import type { ExperimentDbStatsSummary } from '../types';

type ExperimentVectorDbStatsCardProps = {
  experimentId: string;
  stats?: ExperimentDbStatsSummary;
  loading?: boolean;
};

const RUN_BREAKDOWN_PREVIEW = 8;

export default function ExperimentVectorDbStatsCard({
  experimentId,
  stats,
  loading = false,
}: ExperimentVectorDbStatsCardProps) {
  if (loading && !stats) {
    return (
      <div className="rounded-lg border border-indigo-100 bg-indigo-50/50 px-4 py-3 text-sm text-slate-600">
        Loading vector database stats…
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
        No vector database stats yet — stats appear after chunks are stored.
      </div>
    );
  }

  const runPreview = stats.run_breakdown.slice(0, RUN_BREAKDOWN_PREVIEW);
  const hiddenRuns = stats.run_breakdown.length - runPreview.length;

  return (
    <div className="rounded-lg border border-indigo-100 bg-gradient-to-br from-indigo-50/80 to-blue-50/50 px-4 py-3">
      <CollapsibleCard
        title="Vector Database"
        compact
        defaultOpen={false}
        storageKey={`exp-vdb-stats-${experimentId}`}
        headerExtra={
          <span className="text-xs font-semibold text-indigo-700">
            {stats.total_chunks.toLocaleString()} chunks · {stats.estimated_storage_mb} MB
          </span>
        }
      >
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile label="Chunks" value={stats.total_chunks.toLocaleString()} />
          <StatTile label="Query Results" value={stats.total_results.toLocaleString()} />
          <StatTile
            label="Storage (Est.)"
            value={`${stats.estimated_storage_mb} MB`}
            hint={`${stats.estimated_embedding_mb} MB vectors · ${stats.estimated_metadata_mb} MB meta`}
          />
          <StatTile label="Runs with Data" value={stats.runs_with_data} />
        </div>

        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <InfoPanel title="Cluster & Collection">
            <Row label="Provider" value={stats.database_provider} />
            <Row label="Collection" value={stats.collection_name} mono />
            <Row label="Atlas host" value={stats.cluster_host ?? '—'} mono />
            <Row label="Source documents" value={String(stats.unique_documents)} />
            <Row label="Unique queries" value={String(stats.unique_queries)} />
            <Row label="Avg chunks / run" value={String(stats.avg_chunks_per_run)} />
          </InfoPanel>

          <InfoPanel title="Embeddings & Indexes">
            <div className="mb-2 flex flex-wrap gap-1">
              {stats.embedding_models.length > 0 ? (
                stats.embedding_models.map((model) => (
                  <span
                    key={model}
                    className="rounded-md bg-blue-100 px-2 py-0.5 font-mono text-[11px] text-blue-800"
                  >
                    {model}
                  </span>
                ))
              ) : (
                <span className="text-xs text-slate-500">—</span>
              )}
            </div>
            <div className="mb-2 flex flex-wrap gap-1">
              {stats.embedding_dimensions.map((dim) => (
                <span
                  key={dim}
                  className="rounded-md bg-indigo-100 px-2 py-0.5 text-[11px] font-medium text-indigo-800"
                >
                  {dim}d
                </span>
              ))}
            </div>
            <div className="flex flex-wrap gap-1">
              {stats.index_names.map((idx) => (
                <span
                  key={idx}
                  className="rounded-md bg-purple-100 px-2 py-0.5 font-mono text-[11px] text-purple-800"
                >
                  {idx}
                </span>
              ))}
            </div>
          </InfoPanel>
        </div>

        {(stats.retrieval_methods.length > 0 || stats.chunking_methods.length > 0) && (
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {stats.retrieval_methods.length > 0 && (
              <InfoPanel title="Retrieval Methods">
                <div className="flex flex-wrap gap-1">
                  {stats.retrieval_methods.map((method) => (
                    <span
                      key={method}
                      className="rounded-md bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-800"
                    >
                      {method}
                    </span>
                  ))}
                </div>
              </InfoPanel>
            )}
            {stats.chunking_methods.length > 0 && (
              <InfoPanel title="Chunking Breakdown">
                <div className="space-y-1">
                  {Object.entries(stats.chunking_breakdown).map(([method, count]) => (
                    <div key={method} className="flex justify-between gap-3 text-xs">
                      <span className="font-medium text-slate-700">{method}</span>
                      <span className="font-mono text-slate-900">{count.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </InfoPanel>
            )}
          </div>
        )}

        {runPreview.length > 0 && (
          <div className="mt-3 rounded-lg border border-indigo-100 bg-white/80 p-3">
            <div className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">
              Per-run storage
            </div>
            <div className="space-y-1">
              {runPreview.map((run) => (
                <div key={run.run_id} className="flex justify-between gap-3 text-xs">
                  <span className="truncate font-mono text-slate-600">{run.run_id.slice(0, 8)}…</span>
                  <span className="shrink-0 text-slate-800">
                    {run.chunks.toLocaleString()} chunks · {run.results.toLocaleString()} results
                  </span>
                </div>
              ))}
            </div>
            {hiddenRuns > 0 && (
              <p className="mt-2 text-[11px] text-slate-500">
                + {hiddenRuns} more run{hiddenRuns === 1 ? '' : 's'} — open experiment detail for full list
              </p>
            )}
          </div>
        )}
      </CollapsibleCard>
    </div>
  );
}

function StatTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="rounded-md border border-indigo-100 bg-white/90 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="text-lg font-bold text-indigo-600">{value}</div>
      {hint ? <div className="mt-0.5 text-[10px] leading-snug text-slate-500">{hint}</div> : null}
    </div>
  );
}

function InfoPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-md border border-indigo-100 bg-white/90 p-3">
      <div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">{title}</div>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function Row({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-3 text-xs">
      <span className="text-slate-600">{label}</span>
      <span className={`font-medium text-slate-900 ${mono ? 'font-mono text-[11px]' : ''}`}>{value}</span>
    </div>
  );
}
