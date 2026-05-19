import CollapsibleCard from './CollapsibleCard';
import type { VectorDbStatsGroup } from '../types';

function groupLabel(group: VectorDbStatsGroup): string {
  if (group.cluster_host) return group.cluster_host;
  return `${group.database_provider} (local)`;
}

type VectorDbStatsPanelProps = {
  groups: VectorDbStatsGroup[];
  loading?: boolean;
  error?: string | null;
};

function formatStorageSummary(group: VectorDbStatsGroup): string {
  const parts = [`${group.totals.total_chunks.toLocaleString()} chunks`];
  if (group.totals.database_free_mb != null && group.totals.database_storage_limit_mb != null) {
    parts.push(`${group.totals.database_free_mb} MB free`);
  } else if (group.totals.database_used_mb != null) {
    parts.push(`${group.totals.database_used_mb} MB used`);
  } else {
    parts.push(`${group.totals.estimated_storage_mb} MB est.`);
  }
  return parts.join(' · ');
}

function storageUsagePercent(group: VectorDbStatsGroup): number | null {
  const used = group.totals.database_used_mb;
  const limit = group.totals.database_storage_limit_mb;
  if (used == null || limit == null || limit <= 0) return null;
  return Math.min(100, Math.round((used / limit) * 100));
}

export default function VectorDbStatsPanel({
  groups,
  loading = false,
  error = null,
}: VectorDbStatsPanelProps) {
  if (loading && groups.length === 0) {
    return (
      <div className="mb-6 rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-blue-50 p-6 text-sm text-slate-600">
        Loading vector database stats…
      </div>
    );
  }

  if (error && groups.length === 0) {
    return (
      <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-semibold">Could not load vector database stats</p>
        <p className="mt-1">{error}</p>
      </div>
    );
  }

  if (groups.length === 0 && !loading && !error) {
    return (
      <div className="mb-6 rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-blue-50 p-6 text-sm text-slate-600">
        Vector database stats will appear after your first experiment stores chunks.
      </div>
    );
  }

  if (groups.length === 0) return null;

  return (
    <div className="mb-6 space-y-4">
      {groups.map((group) => (
        <div
          key={group.vector_db_id}
          className="rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-blue-50 p-6 shadow-sm"
        >
          <CollapsibleCard
            title="Vector Database"
            defaultOpen
            storageKey={`vectordb-group-${group.vector_db_id}`}
            headerExtra={
              <span className="text-sm font-semibold text-indigo-700">
                {groupLabel(group)} · {formatStorageSummary(group)}
              </span>
            }
          >
            <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <StatTile label="Experiments" value={group.totals.experiment_count} />
              <StatTile label="Total Chunks" value={group.totals.total_chunks.toLocaleString()} />
              <StatTile label="Query Results" value={group.totals.total_results.toLocaleString()} />
              <StatTile
                label="DB Used"
                value={
                  group.totals.database_used_mb != null
                    ? `${group.totals.database_used_mb} MB`
                    : '—'
                }
                hint={
                  group.totals.database_data_mb != null
                    ? `${group.totals.database_data_mb} MB data · ${group.totals.database_index_mb} MB indexes`
                    : undefined
                }
              />
              <StatTile
                label="Free Storage"
                value={
                  group.totals.database_free_mb != null &&
                  group.totals.database_storage_limit_mb != null
                    ? `${group.totals.database_free_mb} MB`
                    : '—'
                }
                hint={
                  group.totals.database_storage_limit_mb != null
                    ? `of ${group.totals.database_storage_limit_mb} MB cluster quota`
                    : 'Set ATLAS_* API keys or MONGODB_STORAGE_LIMIT_MB to show quota'
                }
              />
              <StatTile
                label="Chunks (Est.)"
                value={`${group.totals.estimated_storage_mb} MB`}
                hint={`${group.totals.estimated_embedding_mb} MB vectors · ${group.totals.estimated_metadata_mb} MB meta`}
              />
            </div>

            {storageUsagePercent(group) != null && (
              <div className="mb-4 rounded-lg border border-indigo-200 bg-white p-4">
                <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-wider text-slate-500">
                  <span>Cluster storage</span>
                  <span className="font-mono text-slate-700">
                    {group.totals.database_used_mb} / {group.totals.database_storage_limit_mb} MB
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-indigo-100">
                  <div
                    className={`h-full rounded-full ${
                      (storageUsagePercent(group) ?? 0) >= 85 ? 'bg-amber-500' : 'bg-indigo-500'
                    }`}
                    style={{ width: `${storageUsagePercent(group)}%` }}
                  />
                </div>
              </div>
            )}

            <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-indigo-200 bg-white p-4">
                <div className="mb-2 text-xs uppercase tracking-wider text-slate-500">Cluster & Collection</div>
                <div className="space-y-1 text-sm">
                  <Row label="Provider" value={group.database_provider} />
                  <Row label="Collection" value={group.collection_name} mono />
                  <Row label="Atlas host" value={group.cluster_host ?? '—'} mono />
                  {group.totals.database_storage_limit_mb != null && (
                    <Row
                      label="Cluster quota"
                      value={`${group.totals.database_storage_limit_mb} MB`}
                    />
                  )}
                </div>
              </div>
              <div className="rounded-lg border border-indigo-200 bg-white p-4">
                <div className="mb-2 text-xs uppercase tracking-wider text-slate-500">Indexes & Dimensions</div>
                <div className="mb-2 flex flex-wrap gap-1">
                  {group.index_names.map((idx) => (
                    <span key={idx} className="rounded-md bg-purple-100 px-2 py-1 font-mono text-xs text-purple-800">
                      {idx}
                    </span>
                  ))}
                </div>
                <div className="flex flex-wrap gap-1">
                  {group.embedding_dimensions.map((dim) => (
                    <span key={dim} className="rounded-md bg-blue-100 px-2 py-1 text-xs font-medium text-blue-800">
                      {dim}d
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </CollapsibleCard>
        </div>
      ))}
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
    <div className="rounded-lg border border-indigo-200 bg-white p-4">
      <div className="mb-1 text-xs uppercase tracking-wider text-slate-500">{label}</div>
      <div className="text-2xl font-bold text-indigo-600">{value}</div>
      {hint ? <div className="mt-1 text-xs text-slate-500">{hint}</div> : null}
    </div>
  );
}

function Row({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-slate-600">{label}</span>
      <span className={`font-medium text-slate-900 ${mono ? 'font-mono text-xs' : ''}`}>{value}</span>
    </div>
  );
}
