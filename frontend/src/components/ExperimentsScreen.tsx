import { useEffect, useState } from 'react';
import { getExperiments } from '../services/apiClient';
import { Experiment } from '../types';

export default function ExperimentsScreen({ onSelect }: { onSelect?: (id: string) => void }) {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Initial load
    loadExperiments();

    // Poll every 500ms (0.5Hz)
    const interval = setInterval(loadExperiments, 500);

    return () => clearInterval(interval);
  }, []);

  async function loadExperiments() {
    try {
      const data = await getExperiments();
      setExperiments(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load experiments');
    } finally {
      setLoading(false);
    }
  }

  if (loading && experiments.length === 0) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="text-slate-600">Loading experiments...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Experiments</h1>
          <p className="text-slate-600">
            RAG parameter sweep experiment history and live runs
          </p>
        </div>

        {/* Error state */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Empty state */}
        {experiments.length === 0 && !error && (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center border border-slate-200">
            <div className="text-slate-400 text-lg mb-2">No experiments yet</div>
            <div className="text-slate-500 text-sm">
              Submit your first experiment using the CLI:
              <code className="block mt-2 bg-slate-100 p-2 rounded text-xs">
                rag-params-finder run --config configs/example.yaml
              </code>
            </div>
          </div>
        )}

        {/* Experiments table */}
        {experiments.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">
                    Experiment Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">
                    Experiment ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">
                    Runs
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">
                    Git Commit
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {experiments.map((exp) => (
                  <tr
                    key={exp.experiment_id}
                    className="hover:bg-slate-50 transition-colors cursor-pointer"
                    onClick={() => onSelect?.(exp.experiment_id)}
                  >
                    <td className="px-6 py-4 text-sm font-medium text-slate-900">
                      {exp.experiment_name}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600 font-mono">
                      {exp.experiment_id.slice(0, 8)}...
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600 font-mono">
                      {exp.run_count ?? '—'}
                      {exp.failed_count ? (
                        <span className="text-red-500 ml-1">({exp.failed_count} failed)</span>
                      ) : null}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex px-2 py-1 text-xs font-bold rounded ${
                            exp.status === 'complete'
                              ? 'bg-green-100 text-green-700'
                              : exp.status === 'running'
                              ? 'bg-blue-100 text-blue-700'
                              : exp.status === 'partial'
                              ? 'bg-yellow-100 text-yellow-700'
                              : exp.status === 'failed'
                              ? 'bg-red-100 text-red-700'
                              : exp.status === 'cancelled'
                              ? 'bg-orange-100 text-orange-700'
                              : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {exp.status}
                        </span>
                        {(exp.status === 'failed' || exp.status === 'partial') && (
                          <span className="text-xs text-red-400">click for details</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-500 font-mono">
                      {exp.git_commit ?? '—'}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">
                      {new Date(exp.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Polling indicator */}
        <div className="mt-4 text-xs text-slate-500 text-center">
          Polling every 0.5s {loading && <span className="animate-pulse">●</span>}
        </div>
      </div>
    </div>
  );
}
