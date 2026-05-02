import { useEffect, useState } from 'react';
import { cancelExperiment, getExperiment } from '../services/apiClient';
import { RunStatus, Phase, EnvParams, SweepSummary } from '../types';

interface ExperimentDetail {
  experiment_id: string;
  experiment_name: string;
  status: string;
  run_count?: number;
  failed_count?: number;
  runs?: RunStatus[];
  started_at?: string;
  completed_at?: string | null;
  git_commit?: string;
  git_branch?: string;
  git_dirty?: boolean;
  python_version?: string;
  app_version?: string;
  env_params?: EnvParams;
  data_paths?: string[];
  queries_file?: string;
  rerank_model?: string | null;
  top_k_initial?: number;
  top_k_final?: number;
  parallelism?: number;
  on_error?: string;
  sweep_summary?: SweepSummary;
}

const PHASE_ORDER: Phase[] = [
  Phase.QUEUED, Phase.PARSING, Phase.CHUNKING, Phase.EMBEDDING,
  Phase.STORING, Phase.QUERYING, Phase.RERANKING, Phase.COMPLETE,
];

function PhaseIndicator({ current }: { current: Phase }) {
  const currentIdx = PHASE_ORDER.indexOf(current);
  const isFailed = current === Phase.FAILED || current === Phase.INTERRUPTED;

  return (
    <div className="relative group flex gap-1 items-center">
      {PHASE_ORDER.map((phase, i) => {
        const isCurrent = phase === current;
        const isPast = i < currentIdx;

        let bg = 'bg-slate-200';
        if (isFailed) bg = 'bg-red-300';
        else if (isCurrent) bg = 'bg-blue-500 animate-pulse';
        else if (isPast) bg = 'bg-green-400';

        return (
          <div
            key={phase}
            className={`w-3 h-3 rounded-full ${bg}`}
          />
        );
      })}
      <span className="ml-2 text-xs text-slate-500">{current}</span>

      {/* Tooltip on hover */}
      <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block z-50 pointer-events-none">
        <div className="bg-slate-800 text-white text-xs rounded-lg shadow-lg px-3 py-2 whitespace-nowrap">
          {PHASE_ORDER.map((p, i) => {
            let icon = '○';
            let color = 'text-slate-400';
            let label = '';
            if (isFailed) {
              icon = '✗';
              color = 'text-red-300';
            } else if (i < currentIdx) {
              icon = '✓';
              color = 'text-green-300';
            } else if (i === currentIdx) {
              icon = '●';
              color = 'text-blue-300';
              label = ' ← current';
            }

            return (
              <div key={p} className={`${color} leading-5`}>
                {icon} {p}{label}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function formatDuration(startedAt?: string, completedAt?: string | null): string {
  if (!startedAt || !completedAt) return '—';
  const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime();
  if (ms < 1000) return `${ms}ms`;
  const secs = ms / 1000;
  if (secs < 60) return `${secs.toFixed(1)}s`;
  const mins = Math.floor(secs / 60);
  const remSecs = (secs % 60).toFixed(0);
  return `${mins}m ${remSecs}s`;
}

function MetadataItem({ label, value }: { label: string; value: string | number | boolean | undefined }) {
  if (value === undefined || value === null) return null;
  return (
    <div className="flex flex-col">
      <span className="text-xs text-slate-400 uppercase tracking-wider">{label}</span>
      <span className="text-sm text-slate-700 font-mono">{String(value)}</span>
    </div>
  );
}

export default function ExperimentDetailScreen({
  experimentId,
  onBack,
}: {
  experimentId: string;
  onBack: () => void;
}) {
  const [detail, setDetail] = useState<ExperimentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    loadDetail();
    const interval = setInterval(loadDetail, 2000);
    return () => clearInterval(interval);
  }, [experimentId]);

  async function loadDetail() {
    try {
      const data = await getExperiment(experimentId) as unknown as ExperimentDetail;
      setDetail(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    }
  }

  async function handleCancel() {
    if (!confirm('Cancel this experiment? Runs in progress will stop after the current phase.')) {
      return;
    }
    setCancelling(true);
    try {
      await cancelExperiment(experimentId);
      await loadDetail();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel');
    } finally {
      setCancelling(false);
    }
  }

  const isTerminal = detail && ['complete', 'failed', 'partial', 'cancelled'].includes(detail.status);
  const isRunning = detail?.status === 'running';

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-7xl mx-auto">
        <button
          onClick={onBack}
          className="mb-4 text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
        >
          ← Back to experiments
        </button>

        <div className="mb-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">
                {detail?.experiment_name ?? 'Loading...'}
              </h1>
              <p className="text-sm text-slate-500 font-mono mt-1">{experimentId}</p>
              {detail && (
                <div className="flex gap-4 mt-2 text-sm text-slate-600">
                  <span>Status: <strong>{detail.status}</strong></span>
                  {detail.run_count != null && <span>Runs: {detail.run_count}</span>}
                  {detail.failed_count ? (
                    <span className="text-red-600">{detail.failed_count} failed</span>
                  ) : null}
                </div>
              )}
            </div>
            {isRunning && (
              <button
                onClick={handleCancel}
                disabled={cancelling}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-300 text-white text-sm font-medium rounded-lg transition-colors"
              >
                {cancelling ? 'Cancelling...' : 'Cancel Experiment'}
              </button>
            )}
          </div>
        </div>

        {/* Metadata panel */}
        {detail && (
          <div className="mb-6 bg-white rounded-xl shadow-sm border border-slate-200 p-5">
            <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
              Experiment Metadata
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              <MetadataItem
                label="Git Commit"
                value={detail.git_commit
                  ? `${detail.git_commit}${detail.git_dirty ? ' (dirty)' : ''}`
                  : undefined}
              />
              <MetadataItem label="Git Branch" value={detail.git_branch} />
              <MetadataItem
                label="Started"
                value={detail.started_at ? new Date(detail.started_at).toLocaleString() : undefined}
              />
              <MetadataItem
                label="Completed"
                value={detail.completed_at ? new Date(detail.completed_at).toLocaleString() : undefined}
              />
              <MetadataItem
                label="Duration"
                value={formatDuration(detail.started_at, detail.completed_at)}
              />
              <MetadataItem label="Status" value={detail.status} />
              <MetadataItem label="App Version" value={detail.app_version} />
              <MetadataItem label="Python" value={detail.python_version} />
            </div>

            {/* Sweep config */}
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mt-4 mb-2">
              Sweep Configuration
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              <MetadataItem label="Rerank Model" value={detail.rerank_model ?? 'none'} />
              <MetadataItem label="Top-K Initial" value={detail.top_k_initial} />
              <MetadataItem label="Top-K Final" value={detail.top_k_final} />
              <MetadataItem label="Parallelism" value={detail.parallelism} />
              <MetadataItem label="On Error" value={detail.on_error} />
              <MetadataItem label="Queries" value={detail.queries_file} />
            </div>
            {detail.data_paths && detail.data_paths.length > 0 && (
              <div className="mt-2">
                <span className="text-xs text-slate-400 uppercase tracking-wider">Data Paths</span>
                <div className="mt-1 flex flex-wrap gap-1">
                  {detail.data_paths.map((p) => (
                    <span key={p} className="text-xs font-mono bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                      {p}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {detail.sweep_summary && (
              <div className="mt-3">
                <span className="text-xs text-slate-400 uppercase tracking-wider">Sweep Dimensions</span>
                <div className="mt-1 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                  <MetadataItem label="Models" value={detail.sweep_summary.models.join(', ')} />
                  <MetadataItem label="Chunkers" value={detail.sweep_summary.chunking_methods.join(', ')} />
                  <MetadataItem label="Chunk Sizes" value={detail.sweep_summary.chunk_sizes.join(', ')} />
                  <MetadataItem label="Overlaps" value={detail.sweep_summary.overlaps.join(', ')} />
                  <MetadataItem label="Retrieval" value={detail.sweep_summary.retrieval_methods.join(', ')} />
                </div>
              </div>
            )}

            {detail.env_params && (
              <>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mt-4 mb-2">
                  Environment
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                  <MetadataItem label="Server URL" value={detail.env_params.server_url} />
                  <MetadataItem label="Voyage RPM" value={detail.env_params.voyage_rpm_limit} />
                  <MetadataItem label="Voyage TPM" value={detail.env_params.voyage_tpm_limit} />
                  <MetadataItem label="Recover on Boot" value={String(detail.env_params.recover_on_boot)} />
                </div>
              </>
            )}
          </div>
        )}

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {detail?.runs && detail.runs.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-visible">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Run ID</th>
                  <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Model</th>
                  <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Chunker</th>
                  <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Size/Overlap</th>
                  <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Retrieval</th>
                  <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Phase</th>
                  <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Elapsed</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {detail.runs.map((run) => (
                  <tr key={run.run_id} className={`hover:bg-slate-50 transition-colors ${run.phase === Phase.FAILED ? 'bg-red-50/50' : ''}`}>
                    <td className="px-4 py-3 text-sm font-mono text-slate-600">
                      {run.run_id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-3 text-sm">{run.embedding_model}</td>
                    <td className="px-4 py-3 text-sm">{run.chunking_method}</td>
                    <td className="px-4 py-3 text-sm font-mono">{run.chunk_size}/{run.overlap}</td>
                    <td className="px-4 py-3 text-sm">{run.retrieval_method}</td>
                    <td className="px-4 py-3"><PhaseIndicator current={run.phase} /></td>
                    <td className="px-4 py-3 text-sm text-slate-500">
                      {run.elapsed_ms > 0 ? `${(run.elapsed_ms / 1000).toFixed(1)}s` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Failed runs detail */}
        {detail?.runs && detail.runs.filter(r => r.phase === Phase.FAILED).length > 0 && (
          <div className="mt-6 bg-red-50 border border-red-200 rounded-xl p-5">
            <h2 className="text-sm font-bold text-red-800 mb-3">
              Failed Runs ({detail.runs.filter(r => r.phase === Phase.FAILED).length})
            </h2>
            <div className="space-y-3">
              {detail.runs.filter(r => r.phase === Phase.FAILED).map(run => (
                <div key={run.run_id} className="bg-white border border-red-100 rounded-lg p-3">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-xs font-mono text-slate-500">{run.run_id.slice(0, 8)}</span>
                    <span className="text-xs text-slate-600">
                      {run.embedding_model} / {run.chunking_method} / {run.chunk_size}+{run.overlap}
                    </span>
                    {run.elapsed_ms > 0 && (
                      <span className="text-xs text-slate-400">
                        after {(run.elapsed_ms / 1000).toFixed(1)}s
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-red-700 font-mono whitespace-pre-wrap">
                    {run.error_message || 'No error message recorded'}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Success summary */}
        {isTerminal && detail?.runs && detail.runs.filter(r => r.phase === Phase.FAILED).length === 0 && (
          <div className="mt-6 bg-green-50 border border-green-200 rounded-xl p-5">
            <p className="text-sm text-green-800 font-medium">
              All {detail.runs.length} run(s) completed successfully.
            </p>
          </div>
        )}

        {!isTerminal && (
          <div className="mt-4 text-xs text-slate-500 text-center">
            Polling every 2s <span className="animate-pulse">●</span>
          </div>
        )}
      </div>
    </div>
  );
}
