import { useEffect, useRef, useState } from 'react';
import {
  EXPERIMENTS_POLL_MS,
  LOADING_STALL_AFTER_MS,
  LOADING_STALL_REPEAT_MS,
} from '../constants';
import AppPageChrome from './AppPageChrome';
import DashboardShell from './DashboardShell';
import LoadingFeedbackPanel, { type FeedEntry } from './LoadingFeedbackPanel';
import { createStallWatcher, type FetchProgressUpdate } from '../services/fetchWithProgress';
import { getExperiments, getExperimentsWithProgress } from '../services/apiClient';
import { Experiment } from '../types';

let feedSeq = 0;

function appendFeed(prev: FeedEntry[], text: string, variant: FeedEntry['variant']): FeedEntry[] {
  feedSeq += 1;
  return [...prev, { id: `${Date.now()}-${feedSeq}`, text, variant }];
}

function experimentsRailHelp() {
  return (
    <>
      <div className="mb-6">
        <div className="text-sm font-semibold text-slate-200">Sidebar</div>
        <div className="mt-0.5 text-[11px] uppercase tracking-wider text-slate-500">Experiment list</div>
      </div>
      <div className="rounded-lg border border-slate-600/50 bg-slate-700/40 px-3 py-3 text-xs leading-relaxed text-slate-300 ring-1 ring-slate-600/35">
        This table polls the experiments API continuously so you never miss a sweep finishing.
      </div>
    </>
  );
}

export default function ExperimentsScreen({ onSelect }: { onSelect?: (id: string) => void }) {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(false);
  const [initialLoadDone, setInitialLoadDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feed, setFeed] = useState<FeedEntry[]>([]);
  const [receivedBytes, setReceivedBytes] = useState<number | null>(null);
  const [totalBytes, setTotalBytes] = useState<number | null>(null);

  const aliveRef = useRef(true);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    aliveRef.current = true;
    const abortInitial = new AbortController();

    const stall = createStallWatcher({
      alive: () => aliveRef.current,
      afterMs: LOADING_STALL_AFTER_MS,
      repeatMs: LOADING_STALL_REPEAT_MS,
      onWarning: (text) => setFeed((f) => appendFeed(f, text, 'warning')),
    });

    async function bootstrap() {
      setFeed([{ id: 'start', text: 'Starting experiments list load…', variant: 'default' }]);
      setReceivedBytes(null);
      setTotalBytes(null);
      setLoading(true);
      stall.start();

      const applyProg = (u: FetchProgressUpdate) => {
        if (!aliveRef.current) return;
        if (u.type === 'downloading') {
          setReceivedBytes(u.receivedBytes);
          setTotalBytes(u.totalBytes);
          return;
        }
        const variant = u.variant === 'warning' ? 'warning' : 'default';
        setFeed((f) => appendFeed(f, u.text, variant));
      };

      try {
        const data = await getExperimentsWithProgress(applyProg, abortInitial.signal);
        stall.stop();
        if (!aliveRef.current) return;
        setFeed((f) => appendFeed(f, 'Ready.', 'default'));
        setExperiments(data);
        setError(null);
      } catch (err) {
        stall.stop();
        if (!aliveRef.current) return;
        if (err instanceof DOMException && err.name === 'AbortError') return;
        const msg = err instanceof Error ? err.message : 'Failed to load experiments';
        setError(msg);
        setFeed((f) => appendFeed(f, `Failed: ${msg}`, 'warning'));
      } finally {
        stall.stop();
        if (!aliveRef.current) return;
        setLoading(false);
        setInitialLoadDone(true);

        async function silentPoll() {
          if (!aliveRef.current) return;
          try {
            const rows = await getExperiments();
            if (!aliveRef.current) return;
            setExperiments(rows);
            setError(null);
          } catch (pollErr) {
            if (!aliveRef.current) return;
            const pollMsg =
              pollErr instanceof Error ? pollErr.message : 'Polling failed — check server connectivity.';
            setError(pollMsg);
          }
        }

        if (pollTimerRef.current !== null) window.clearInterval(pollTimerRef.current);
        pollTimerRef.current = setInterval(silentPoll, EXPERIMENTS_POLL_MS);
        void silentPoll();
      }
    }

    void bootstrap();

    return () => {
      aliveRef.current = false;
      abortInitial.abort();
      stall.stop();
      if (pollTimerRef.current !== null) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, []);

  if (!initialLoadDone && experiments.length === 0) {
    return (
      <DashboardShell
        asideWidthClass="w-56 lg:w-60"
        header={
          <AppPageChrome
            tone="darkFrame"
            pageTitle="Experiments"
            pageHint="Loading experiment list and run summaries from your server."
          />
        }
        sidebar={experimentsRailHelp()}
      >
        <div className="flex justify-center py-8">
          <LoadingFeedbackPanel
            title="Loading experiments"
            subtitle="Transfer + parse milestones (server does not stream row counts yet)."
            feed={feed}
            receivedBytes={receivedBytes}
            totalBytes={totalBytes}
            footer={`After load, list refreshes every ${EXPERIMENTS_POLL_MS / 1000}s without reopening this panel.`}
            theme="light"
          />
        </div>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell
      asideWidthClass="w-56 lg:w-60"
      header={
        <AppPageChrome
          tone="darkFrame"
          pageTitle="Experiments"
          pageHint={`History and live status for every sweep. This table refreshes every ${EXPERIMENTS_POLL_MS / 1000}s while you keep the page open.`}
        />
      }
      sidebar={experimentsRailHelp()}
    >
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
      )}

        {experiments.length === 0 && !error && (
          <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-sm">
            <div className="mb-2 text-lg text-slate-400">No experiments yet</div>
            <div className="text-sm text-slate-500">
              Submit your first experiment using the CLI:
              <code className="mt-2 block rounded bg-slate-100 p-2 text-xs">
                rag-params-finder run --config configs/example.yaml
              </code>
            </div>
          </div>
        )}

        {experiments.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-600">
                    Experiment Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-600">
                    Experiment ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-600">
                    Runs
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-600">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-600">
                    Git Commit
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-600">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {experiments.map((exp) => (
                  <tr
                    key={exp.experiment_id}
                    className="cursor-pointer transition-colors hover:bg-slate-50"
                    onClick={() => onSelect?.(exp.experiment_id)}
                  >
                    <td className="px-6 py-4 text-sm font-medium text-slate-900">{exp.experiment_name}</td>
                    <td className="px-6 py-4 font-mono text-sm text-slate-600">
                      {exp.experiment_id.slice(0, 8)}...
                    </td>
                    <td className="px-6 py-4 font-mono text-sm text-slate-600">
                      {exp.run_count ?? '—'}
                      {exp.failed_count ? (
                        <span className="ml-1 text-red-500">({exp.failed_count} failed)</span>
                      ) : null}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex rounded px-2 py-1 text-xs font-bold ${
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
                    <td className="px-6 py-4 font-mono text-sm text-slate-500">{exp.git_commit ?? '—'}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">
                      {new Date(exp.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

      <div className="mt-4 text-center text-xs text-slate-500">
        Polling every {EXPERIMENTS_POLL_MS / 1000}s{' '}
        {loading ? <span className="animate-pulse">●</span> : null}
      </div>
    </DashboardShell>
  );
}
