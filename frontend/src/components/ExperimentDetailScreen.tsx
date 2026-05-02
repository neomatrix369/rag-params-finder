import { useEffect, useState } from 'react';
import { getExperiment } from '../services/apiClient';
import { RunStatus, Phase } from '../types';

interface ExperimentDetail {
  experiment_id: string;
  experiment_name: string;
  status: string;
  run_count?: number;
  failed_count?: number;
  runs?: RunStatus[];
}

const PHASE_ORDER: Phase[] = [
  Phase.QUEUED, Phase.PARSING, Phase.CHUNKING, Phase.EMBEDDING,
  Phase.STORING, Phase.QUERYING, Phase.RERANKING, Phase.COMPLETE,
];

function PhaseIndicator({ current }: { current: Phase }) {
  return (
    <div className="flex gap-1 items-center">
      {PHASE_ORDER.map((phase) => {
        const isCurrent = phase === current;
        const isPast = PHASE_ORDER.indexOf(phase) < PHASE_ORDER.indexOf(current);
        const isFailed = current === Phase.FAILED;

        let bg = 'bg-slate-200';
        if (isFailed) bg = 'bg-red-300';
        else if (isCurrent) bg = 'bg-blue-500 animate-pulse';
        else if (isPast) bg = 'bg-green-400';

        return (
          <div
            key={phase}
            className={`w-3 h-3 rounded-full ${bg}`}
            title={phase}
          />
        );
      })}
      <span className="ml-2 text-xs text-slate-500">{current}</span>
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

  const isTerminal = detail && ['complete', 'failed', 'partial'].includes(detail.status);

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

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {detail?.runs && detail.runs.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
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
                  <tr key={run.run_id} className="hover:bg-slate-50 transition-colors">
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

        {!isTerminal && (
          <div className="mt-4 text-xs text-slate-500 text-center">
            Polling every 2s <span className="animate-pulse">●</span>
          </div>
        )}
      </div>
    </div>
  );
}
