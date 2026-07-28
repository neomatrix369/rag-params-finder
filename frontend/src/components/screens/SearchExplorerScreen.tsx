import { useCallback, useEffect, useRef, useState } from 'react';
import {
  DEV_POLL_LOG_INTERVAL_MS,
  EXPLORE_POLL_MS,
  LOADING_STALL_AFTER_MS,
  LOADING_STALL_REPEAT_MS,
} from '../../constants';
import AppPageChrome from '../chrome/AppPageChrome';
import DashboardShell from '../chrome/DashboardShell';
import LoadingFeedbackPanel from '../chrome/LoadingFeedbackPanel';
import PollingIndicator from '../chrome/PollingIndicator';
import type { FeedEntry } from '../chrome/LoadingFeedbackPanel';
import {
  getExperiment,
  getExperimentExplore,
  getExperimentExploreWithProgress,
  type ExperimentProgressCallback,
} from '../../services/apiClient';
import { createStallWatcher, formatBytes, type FetchProgressUpdate } from '../../services/fetchWithProgress';
import type { ExploreResponse } from '../../types';
import { appendFeedEntry } from '../../utils/feedEntries';
import { devInfo, devInfoThrottled, devWarn } from '../../utils/devLog';
import {
  explorerFetchFeedText,
  explorerPayloadHint,
} from '../../utils/storageLabels';
import {
  ConfigSidebar,
  DetailedResultsTab,
  HyperparametersTab,
} from '../explore/ExplorePanels';

type Tab = 'hyperparameters' | 'detailed';

export default function SearchExplorerScreen({
  experimentId,
  onBack,
}: {
  experimentId: string;
  onBack: () => void;
}) {
  const [data, setData] = useState<ExploreResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  /** True on first paint so we never flash an empty canvas before the fetch effect runs */
  const [loading, setLoading] = useState(true);
  const [isPolling, setIsPolling] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('hyperparameters');
  const [selectedQuery, setSelectedQuery] = useState<string>('');
  const [selectedMethods, setSelectedMethods] = useState<Set<string>>(new Set());
  const [pollWhileRunning, setPollWhileRunning] = useState(true);
  const [feed, setFeed] = useState<FeedEntry[]>([]);
  const [receivedBytes, setReceivedBytes] = useState<number | null>(null);
  const [totalBytes, setTotalBytes] = useState<number | null>(null);

  const selectedQueryRef = useRef(selectedQuery);
  selectedQueryRef.current = selectedQuery;

  const prevExperimentRef = useRef('');
  const aliveRef = useRef(true);
  const pollDevLogAtRef = useRef(new Map<string, number>());

  useEffect(() => {
    setPollWhileRunning(true);
    setSelectedQuery('');
  }, [experimentId]);

  useEffect(() => {
    aliveRef.current = true;
    const abort = new AbortController();
    const switchedExperiment = prevExperimentRef.current !== experimentId;
    if (switchedExperiment) {
      prevExperimentRef.current = experimentId;
      setData(null);
    }

    const stall = createStallWatcher({
      scope: 'SearchExplorerScreen',
      operation: 'explore hydrate',
      alive: () => aliveRef.current,
      afterMs: LOADING_STALL_AFTER_MS,
      repeatMs: LOADING_STALL_REPEAT_MS,
      onWarning: (text) => setFeed((f) => appendFeedEntry(f, text, 'warning')),
    });

    const applyProg: ExperimentProgressCallback = (u: FetchProgressUpdate) => {
      if (!aliveRef.current) return;
      if (u.type === 'downloading') {
        setReceivedBytes(u.receivedBytes);
        setTotalBytes(u.totalBytes);
        return;
      }
      setFeed((f) => appendFeedEntry(f, u.text, u.variant === 'warning' ? 'warning' : 'default'));
    };

    async function fetchExplore() {
      devInfo(
        'SearchExplorerScreen',
        `hydrate started — ${experimentId.slice(0, 8)}…${selectedQuery ? ' (filtered query)' : ''}`,
      );
      setLoading(true);
      setReceivedBytes(null);
      setTotalBytes(null);
      if (switchedExperiment) {
        setFeed([{ id: 'x0', text: explorerFetchFeedText(), variant: 'default' }]);
      } else {
        setFeed((f) =>
          appendFeedEntry(
            f,
            `Refreshing explorer${selectedQuery ? ' (filtered query)' : ''}…`,
            'default',
          ),
        );
      }
      setError(null);
      stall.start();
      try {
        const payload = await getExperimentExploreWithProgress(
          experimentId,
          selectedQuery || undefined,
          applyProg,
          abort.signal,
        );
        stall.stop();
        if (!aliveRef.current) return;
        setFeed((f) => appendFeedEntry(f, 'Explorer snapshot ready.', 'default'));
        setData(payload);
        devInfo(
          'SearchExplorerScreen',
          `hydrate OK — ${payload.ranked_configs.length} configs, ${payload.query_count} quer${payload.query_count === 1 ? 'y' : 'ies'}`,
        );

        setSelectedMethods((prev) => {
          if (prev.size > 0) return prev;
          return new Set(payload.ranked_configs.map((c) => c.retrieval_method));
        });
      } catch (err) {
        stall.stop();
        if (!aliveRef.current) return;
        if (err instanceof DOMException && err.name === 'AbortError') return;
        const msg =
          err instanceof Error ? err.message : 'Failed to fetch experiment explore data';
        devWarn('SearchExplorerScreen', `hydrate failed — ${experimentId.slice(0, 8)}… — ${msg}`);
        setError(msg);
        setFeed((f) => appendFeedEntry(f, `Failed: ${msg}`, 'warning'));
      } finally {
        stall.stop();
        if (aliveRef.current) setLoading(false);
      }
    }

    void fetchExplore();

    return () => {
      aliveRef.current = false;
      abort.abort();
      stall.stop();
    };
  }, [experimentId, selectedQuery]);

  useEffect(() => {
    if (!pollWhileRunning) {
      return;
    }
    const id = window.setInterval(() => {
      void (async () => {
        setIsPolling(true);
        try {
          const exp = await getExperiment(experimentId);
          if (exp.status !== 'running') {
            setPollWhileRunning(false);
            return;
          }
          const response = await getExperimentExplore(
            experimentId,
            selectedQueryRef.current || undefined,
          );
          setData(response);
          setError(null);
          devInfoThrottled(
            'SearchExplorerScreen',
            `poll:explore:${experimentId}`,
            DEV_POLL_LOG_INTERVAL_MS,
            `explore poll OK — ${response.ranked_configs.length} configs`,
            pollDevLogAtRef.current,
          );
          setSelectedMethods((prev) => {
            if (prev.size > 0) {
              return prev;
            }
            return new Set(response.ranked_configs.map((c) => c.retrieval_method));
          });
        } catch (pollErr) {
          devWarn('SearchExplorerScreen', `explore poll failed — ${experimentId.slice(0, 8)}… — ${String(pollErr)}`);
        } finally {
          setIsPolling(false);
        }
      })();
    }, EXPLORE_POLL_MS);
    return () => window.clearInterval(id);
  }, [experimentId, pollWhileRunning]);

  const handleToggleMethod = useCallback((method: string) => {
    setSelectedMethods((prev) => {
      const next = new Set(prev);
      if (next.has(method)) {
        /** Never leave zero methods checked — avoids a blank explorer body */
        if (next.size <= 1) return prev;
        next.delete(method);
        return next;
      }
      next.add(method);
      return next;
    });
  }, []);

  const filteredResults = data
    ? data.detailed_results.filter((r) => selectedMethods.has(r.retrieval_method))
    : [];

  const filteredConfigs = data
    ? data.ranked_configs.filter((c) => selectedMethods.has(c.retrieval_method))
    : [];

  const filteredData = data
    ? { ...data, detailed_results: filteredResults, ranked_configs: filteredConfigs }
    : null;

  const explorerRail = (
    <>
      <div className="mb-6">
        <div className="text-sm font-semibold text-slate-200">Sidebar</div>
        <div className="mt-0.5 text-[11px] uppercase tracking-wider text-slate-500">Configs & retrieval filters</div>
      </div>

      <button
        onClick={onBack}
        className="mb-6 w-full rounded-lg px-3 py-2 text-left text-sm text-blue-400 hover:bg-slate-700/55 hover:text-blue-300 flex items-center gap-1"
      >
        &larr; Back to experiment
      </button>

      {data && (
        <ConfigSidebar
          data={data}
          selectedMethods={selectedMethods}
          onToggleMethod={handleToggleMethod}
        />
      )}
    </>
  );

  return (
    <DashboardShell
      asideWidthClass="w-full lg:w-72"
      contentMaxWidthClass="max-w-6xl"
      header={
        <AppPageChrome
          tone="darkFrame"
          pageTitle="Search explorer"
          pageHint={`Aggregates for experiment ${experimentId.slice(0, 8)}… — ranked configs, optional query filter, and per-hit scores. Sidebar controls retrieval-method visibility.`}
          topRight={
            pollWhileRunning ? (
              <PollingIndicator active={isPolling} showDelayMs={600} minVisibleMs={1000} tone="dark" />
            ) : undefined
          }
        />
      }
      sidebar={explorerRail}
    >

          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}

          {loading && (
            <div className="mb-8 flex justify-center">
              <LoadingFeedbackPanel
                title={data ? "Refreshing results…" : "Loading results…"}
                subtitle={
                  data
                    ? "Re-fetching explorer data (query filter changed or refresh triggered)."
                    : explorerPayloadHint()
                }
                footer="Shows byte progress once headers arrive (Content-Length yields a %) or an indeterminate bar until then."
                feed={feed}
                receivedBytes={receivedBytes}
                totalBytes={totalBytes}
                theme="light"
              />
            </div>
          )}

          {/* Query selector */}
          {data && data.queries.length > 0 && (
            <div className="mb-6 flex items-center gap-4">
              <div className="flex-1">
                <select
                  value={selectedQuery}
                  onChange={(e) => setSelectedQuery(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg border border-slate-300 bg-white text-sm text-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">All queries ({data.queries.length})</option>
                  {data.queries.map((q) => (
                    <option key={q} value={q}>
                      {q.length > 80 ? q.slice(0, 80) + '...' : q}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Tabs */}
          <div className="flex items-center gap-0 mb-6 border-b border-slate-200">
            <button
              onClick={() => setActiveTab('hyperparameters')}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'hyperparameters'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              Hyperparameters
            </button>
            <button
              onClick={() => setActiveTab('detailed')}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'detailed'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              Detailed Results
            </button>

            {data && (
              <span className="ml-auto text-xs text-slate-400">
                {filteredResults.length} MATCHES
              </span>
            )}
          </div>

          {loading && data && (
            <div className="mb-6 rounded-xl border border-blue-200 bg-blue-50/90 px-4 py-3 text-sm shadow-sm backdrop-blur">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-semibold text-blue-900">Refreshing explorer data…</span>
                <span aria-live="polite" className="font-mono text-xs text-slate-700">
                  {feed.length ? feed[feed.length - 1]?.text.replace(/^—?\s*/, '') : 'waiting…'}
                </span>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2 font-mono text-[11px] text-slate-600">
                <span>
                  {receivedBytes !== null
                    ? `${formatBytes(receivedBytes)}${
                        totalBytes !== null ? ` / ${formatBytes(totalBytes)}` : ' · size unknown'
                      }`
                    : 'Starting request…'}
                </span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-blue-100" role="progressbar">
                <div
                  className={`h-full rounded-full bg-sky-500 ${
                    receivedBytes !== null &&
                    totalBytes !== null &&
                    totalBytes > 0 &&
                    receivedBytes <= totalBytes
                      ? 'transition-[width] duration-150'
                      : 'w-2/5 animate-pulse'
                  }`}
                  style={
                    receivedBytes !== null &&
                    totalBytes !== null &&
                    totalBytes > 0 &&
                    receivedBytes <= totalBytes
                      ? {
                          width: `${Math.min(
                            100,
                            Math.max(2, Math.round((100 * receivedBytes) / totalBytes)),
                          )}%`,
                        }
                      : undefined
                  }
                />
              </div>
            </div>
          )}

          {/* Content */}
          {filteredData && activeTab === 'hyperparameters' && (
            <HyperparametersTab data={filteredData} />
          )}

          {filteredData && activeTab === 'detailed' && (
            <DetailedResultsTab results={filteredData.detailed_results} />
          )}

          {!loading && !data && !error && (
            <div className="text-center py-20">
              <div className="mb-4">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 mb-4">
                  <svg className="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
              </div>
              <div className="text-lg font-medium text-slate-700 mb-2">Waiting for results</div>
              <div className="text-sm text-slate-500 max-w-md mx-auto">
                {pollWhileRunning
                  ? "The experiment is still running. Results will appear as soon as they're available."
                  : "No explorer data available yet. Try refreshing the experiment detail page."}
              </div>
            </div>
          )}

          {data && data.total_matches === 0 && (
            <div className="text-center py-20 text-slate-400">
              <div className="text-lg mb-2">No results found</div>
              <div className="text-sm">This experiment has no query results stored yet.</div>
            </div>
          )}
    </DashboardShell>
  );
}
