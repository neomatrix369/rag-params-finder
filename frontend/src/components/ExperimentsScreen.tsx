import { useEffect, useRef, useState } from 'react';
import { EXPERIMENTS_POLL_MS } from '../constants';
import {
  formatBytes,
  getExperiments,
  getExperimentsWithProgress,
  type ExperimentsListProgressUpdate,
} from '../services/apiClient';
import { Experiment } from '../types';

type FeedEntry = { id: string; ts: number; text: string; variant: 'default' | 'warning' };

const STALL_AFTER_MS = 1800;
const STALL_REPEAT_MS = 2400;

let feedIdSeq = 0;

function appendFeed(prev: FeedEntry[], text: string, variant: 'default' | 'warning'): FeedEntry[] {
  feedIdSeq += 1;
  return [...prev, { id: `${Date.now()}-${feedIdSeq}`, ts: Date.now(), text, variant }];
}

export default function ExperimentsScreen({ onSelect }: { onSelect?: (id: string) => void }) {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feed, setFeed] = useState<FeedEntry[]>([]);
  const [receivedBytes, setReceivedBytes] = useState<number | null>(null);
  const [totalBytes, setTotalBytes] = useState<number | null>(null);

  const aliveRef = useRef(true);
  const stallTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function clearStallWatch() {
    if (stallTimerRef.current !== null) {
      clearInterval(stallTimerRef.current);
      stallTimerRef.current = null;
    }
  }

  function startStallWatch(requestStartedAt: number) {
    clearStallWatch();
    stallTimerRef.current = setInterval(() => {
      const elapsedMs = Math.round(performance.now() - requestStartedAt);
      if (elapsedMs < STALL_AFTER_MS) return;
      if (!aliveRef.current) return;
      const s = (elapsedMs / 1000).toFixed(1);
      setFeed((f) =>
        appendFeed(f, `No response yet (${s}s) — server or network may be slow.`, 'warning'),
      );
    }, STALL_REPEAT_MS);
  }

  function applyProgressUpdate(u: ExperimentsListProgressUpdate) {
    if (!aliveRef.current) return;
    if (u.type === 'downloading') {
      setReceivedBytes(u.receivedBytes);
      setTotalBytes(u.totalBytes);
      return;
    }
    setFeed((f) => appendFeed(f, u.text, u.variant ?? 'default'));
  }

  useEffect(() => {
    aliveRef.current = true;
    const ac = new AbortController();

    async function loadInitial() {
      setLoading(true);
      setReceivedBytes(null);
      setTotalBytes(null);
      setFeed((f) => appendFeed(f, 'Starting experiments list load…', 'default'));
      const t0 = performance.now();
      startStallWatch(t0);
      try {
        const data = await getExperimentsWithProgress(applyProgressUpdate, ac.signal);
        clearStallWatch();
        if (!aliveRef.current) return;
        setFeed((f) => appendFeed(f, 'Ready.', 'default'));
        setExperiments(data);
        setError(null);
      } catch (err) {
        clearStallWatch();
        if (!aliveRef.current) return;
        if (err instanceof DOMException && err.name === 'AbortError') return;
        const msg = err instanceof Error ? err.message : 'Failed to load experiments';
        setError(msg);
        setFeed((f) => appendFeed(f, `Failed: ${msg}`, 'warning'));
      } finally {
        if (aliveRef.current) setLoading(false);
      }
    }

    async function pollQuietly() {
      try {
        const data = await getExperiments();
        if (!aliveRef.current) return;
        setExperiments(data);
        setError(null);
      } catch (err) {
        if (!aliveRef.current) return;
        const msg = err instanceof Error ? err.message : 'Failed to load experiments';
        setError(msg);
      }
    }

    void loadInitial();

    const interval = setInterval(() => {
      void pollQuietly();
    }, EXPERIMENTS_POLL_MS);

    return () => {
      aliveRef.current = false;
      ac.abort();
      clearStallWatch();
      clearInterval(interval);
    };
  }, []);

  const pct =
    receivedBytes !== null &&
    totalBytes !== null &&
    totalBytes > 0 &&
    receivedBytes <= totalBytes
      ? Math.min(100, Math.round((100 * receivedBytes) / totalBytes))
      : null;

  const downloadSummary =
    receivedBytes !== null
      ? totalBytes !== null
        ? `${formatBytes(receivedBytes)} / ${formatBytes(totalBytes)}${
            pct !== null ? ` (${pct}%)` : ''
          }`
        : `${formatBytes(receivedBytes)} received (total length unknown until complete)`
      : null;

  if (loading && experiments.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50 p-6">
        <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h1 className="text-lg font-semibold text-slate-900">Loading experiments</h1>
          <p className="mt-1 text-sm text-slate-600">
            Streaming status from the API (download + parse steps).
          </p>

          {downloadSummary !== null && (
            <div className="mt-5">
              <div className="flex justify-between text-xs font-medium text-slate-600">
                <span>Payload</span>
                {pct !== null ? <span>{pct}%</span> : null}
              </div>
              <div
                className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"
                role="progressbar"
                aria-valuenow={pct ?? undefined}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div
                  className="h-full rounded-full bg-sky-500 transition-[width] duration-150"
                  style={{ width: pct !== null ? `${pct}%` : '40%' }}
                />
              </div>
              <div className="mt-2 font-mono text-xs text-slate-700">{downloadSummary}</div>
            </div>
          )}

          <div className="mt-5 rounded-lg border border-slate-200 bg-slate-950 px-3 py-2 shadow-inner">
            <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              Activity
            </div>
            <ul
              className="max-h-48 overflow-y-auto font-mono text-[11px] leading-relaxed text-slate-100"
              aria-live="polite"
            >
              {feed.map((entry) => (
                <li
                  key={entry.id}
                  className={
                    entry.variant === 'warning' ? 'text-amber-200' : 'text-slate-200'
                  }
                >
                  — {entry.text}
                </li>
              ))}
            </ul>
          </div>

          <p className="mt-4 text-xs text-slate-500">
            After this screen, the list refreshes silently every{' '}
            {(EXPERIMENTS_POLL_MS / 1000).toFixed(1)}s.
          </p>
        </div>
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
          Polling every {EXPERIMENTS_POLL_MS / 1000}s {loading && <span className="animate-pulse">●</span>}
        </div>
      </div>
    </div>
  );
}
