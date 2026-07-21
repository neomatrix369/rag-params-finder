import { useCallback, useEffect, useRef, useState } from 'react';
import {
  DEV_POLL_LOG_INTERVAL_MS,
  EXPERIMENTS_POLL_MS,
  LOADING_STALL_AFTER_MS,
  LOADING_STALL_REPEAT_MS,
  VECTOR_DB_STATS_POLL_MS,
} from '../constants';
import AppPageChrome from './AppPageChrome';
import DashboardShell from './DashboardShell';
import LoadingFeedbackPanel, { type FeedEntry } from './LoadingFeedbackPanel';
import PollingIndicator from './PollingIndicator';
import ConfirmDeleteModal from './ConfirmDeleteModal';
import ExperimentControlButtons from './ExperimentControlButtons';
import VectorDbStatsPanel from './VectorDbStatsPanel';
import ExperimentVectorDbStatsCard from './ExperimentVectorDbStatsCard';
import { createStallWatcher, type FetchProgressUpdate } from '../services/fetchWithProgress';
import { deleteExperiment, getExperiments, getExperimentsWithProgress, getVectorDbStatsGrouped } from '../services/apiClient';
import { Experiment, ExperimentDbStatsSummary, VectorDbStatsGroup } from '../types';
import { devInfo, devInfoThrottled, devWarn } from '../utils/devLog';
import { isPausedExperimentStatus, isRunningExperimentStatus } from '../utils/experimentStatus';

let feedSeq = 0;

function appendFeed(prev: FeedEntry[], text: string, variant: FeedEntry['variant']): FeedEntry[] {
  feedSeq += 1;
  return [...prev, { id: `${Date.now()}-${feedSeq}`, text, variant }];
}

function ArrowRightIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M4 10h11M11 6l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M4.5 6h11M8 3.5h4M6.5 6l.6 10h5.8l.6-10M8.5 8.5v5M11.5 8.5v5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Pagination({
  currentPage,
  totalItems,
  itemsPerPage,
  onPageChange,
  onItemsPerPageChange,
}: {
  currentPage: number;
  totalItems: number;
  itemsPerPage: number;
  onPageChange: (page: number) => void;
  onItemsPerPageChange: (items: number) => void;
}) {
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  const startItem = (currentPage - 1) * itemsPerPage + 1;
  const endItem = Math.min(currentPage * itemsPerPage, totalItems);

  return (
    <div className="flex flex-col gap-3 border-t border-line bg-canvas px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap items-center gap-3 sm:gap-4">
        <span className="text-sm text-muted">
          Showing <span className="font-medium">{startItem}</span> to{' '}
          <span className="font-medium">{endItem}</span> of{' '}
          <span className="font-medium">{totalItems}</span>
        </span>
        <div className="flex items-center gap-2">
          <label htmlFor="experiments-per-page" className="text-sm text-muted">
            Per page:
          </label>
          <select
            id="experiments-per-page"
            value={itemsPerPage}
            onChange={(e) => onItemsPerPageChange(Number(e.target.value))}
            className="min-h-11 rounded-lg border border-line bg-paper px-3 text-sm text-ink"
          >
            <option value={10}>10</option>
            <option value={15}>15</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="min-h-11 rounded-lg border border-line bg-paper px-3 text-sm font-semibold text-ink hover:border-accent disabled:cursor-not-allowed disabled:opacity-50"
        >
          Previous
        </button>
        <span className="text-sm text-muted">
          Page <span className="font-medium">{currentPage}</span> of{' '}
          <span className="font-medium">{totalPages}</span>
        </span>
        <button
          type="button"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="min-h-11 rounded-lg border border-line bg-paper px-3 text-sm font-semibold text-ink hover:border-accent disabled:cursor-not-allowed disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}

function experimentsRailHelp() {
  return (
    <>
      <div className="mb-6">
        <div className="font-display text-lg font-semibold text-white">From sweep to results</div>
        <div className="mt-1 text-xs font-bold uppercase tracking-widest text-emerald-300">Experiment list</div>
      </div>
      <ol className="space-y-4 border-l border-white/15 pl-4 text-xs text-slate-300">
        <li><span className="block font-mono text-xs text-emerald-300">01 · OVERVIEW</span>Scan lifecycle state and sweep health.</li>
        <li><span className="block font-mono text-xs text-emerald-300">02 · EXPERIMENT</span>Open identity, controls, and configuration.</li>
        <li><span className="block font-mono text-xs text-emerald-300">03 · RESULTS</span>Trace completed runs into stored results.</li>
      </ol>
      <p className="mt-6 rounded-xl border border-white/10 bg-white/5 p-3 text-xs leading-relaxed text-slate-300">
        Running sweeps expose Pause and Cancel. Paused sweeps expose Resume. Controls keep their existing API behavior.
      </p>
    </>
  );
}

function statusBadgeClass(status: Experiment['status']): string {
  if (status === 'complete') return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  if (status === 'running') return 'border-blue-200 bg-blue-50 text-blue-800';
  if (status === 'partial') return 'border-amber-200 bg-amber-50 text-amber-900';
  if (status === 'failed') return 'border-red-200 bg-red-50 text-red-800';
  if (status === 'cancelled') return 'border-slate-300 bg-slate-100 text-slate-800';
  if (status === 'paused') return 'border-violet-200 bg-violet-50 text-violet-800';
  return 'border-line bg-canvas text-ink';
}

function statusEdgeClass(status: Experiment['status']): string {
  if (status === 'complete') return 'border-l-emerald-500';
  if (status === 'running') return 'border-l-blue-500';
  if (status === 'partial') return 'border-l-amber-500';
  if (status === 'failed') return 'border-l-red-500';
  if (status === 'paused') return 'border-l-violet-500';
  return 'border-l-slate-400';
}

function experimentOutcomeLabel(experiment: Experiment): string {
  const configuredRuns = experiment.run_count == null
    ? 'Run count pending'
    : `${experiment.run_count} run${experiment.run_count === 1 ? '' : 's'} configured`;
  if (experiment.status === 'running') return `${configuredRuns} · sweep in progress`;
  if (experiment.status === 'paused') return `${configuredRuns} · waiting to resume`;
  if (experiment.status === 'complete') return `${configuredRuns} · sweep complete`;
  if (experiment.status === 'partial') return `${configuredRuns} · incomplete outcome`;
  if (experiment.status === 'cancelled') return `${configuredRuns} · collection stopped`;
  if (experiment.failed_count) return `${configuredRuns} · ${experiment.failed_count} failed`;
  return `${configuredRuns} · sweep failed`;
}

function experimentStatsMap(groups: VectorDbStatsGroup[]): Map<string, ExperimentDbStatsSummary> {
  const map = new Map<string, ExperimentDbStatsSummary>();
  for (const group of groups) {
    for (const exp of group.experiments) {
      map.set(exp.experiment_id, exp);
    }
  }
  return map;
}

/** True only for the first experiment-list load — not for background polls. */
function shouldShowLoadingPanel(
  initialLoadDone: boolean,
  loading: boolean,
  error: string | null,
): boolean {
  if (error !== null) return false;
  return !initialLoadDone || loading;
}

export default function ExperimentsScreen({
  onSelect,
  cacheReady = false,
  cachedExperiments,
  cachedVectorDbGroups,
  onCacheUpdate,
}: {
  onSelect?: (experiment: Experiment) => void;
  cacheReady?: boolean;
  cachedExperiments?: Experiment[];
  cachedVectorDbGroups?: VectorDbStatsGroup[];
  onCacheUpdate?: (update: { experiments: Experiment[]; vectorDbGroups: VectorDbStatsGroup[] }) => void;
}) {
  const [experiments, setExperiments] = useState<Experiment[]>(() => cachedExperiments ?? []);
  const [loading, setLoading] = useState(() => !cacheReady);
  const [initialLoadDone, setInitialLoadDone] = useState(() => cacheReady);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feed, setFeed] = useState<FeedEntry[]>([]);
  const [receivedBytes, setReceivedBytes] = useState<number | null>(null);
  const [totalBytes, setTotalBytes] = useState<number | null>(null);

  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(15);

  const [selectedExperiments, setSelectedExperiments] = useState<Set<string>>(new Set());
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [collapsedExperiments, setCollapsedExperiments] = useState<Set<string>>(() => {
    const stored = localStorage.getItem('collapsedExperiments');
    return stored ? new Set(JSON.parse(stored)) : new Set();
  });
  const [vectorDbGroups, setVectorDbGroups] = useState<VectorDbStatsGroup[]>(() => cachedVectorDbGroups ?? []);
  const [vectorDbLoading, setVectorDbLoading] = useState(false);
  const [vectorDbError, setVectorDbError] = useState<string | null>(null);

  const handleItemsPerPageChange = useCallback((items: number) => {
    setItemsPerPage(items);
    setCurrentPage(1);
  }, []);

  const handleSelectExperiment = useCallback((experimentId: string, checked: boolean) => {
    setSelectedExperiments(prev => {
      const next = new Set(prev);
      if (checked) {
        next.add(experimentId);
      } else {
        next.delete(experimentId);
      }
      return next;
    });
  }, []);

  const handleSelectAll = useCallback((checked: boolean) => {
    if (checked) {
      const selectableIds = experiments
        .filter(exp => exp.status !== 'running')
        .map(exp => exp.experiment_id);
      setSelectedExperiments(new Set(selectableIds));
    } else {
      setSelectedExperiments(new Set());
    }
  }, [experiments]);

  const refreshExperimentList = useCallback(async () => {
    const refreshed = await getExperiments();
    setExperiments(refreshed);
    onCacheUpdate?.({ experiments: refreshed, vectorDbGroups });
    setError(null);
  }, [onCacheUpdate, vectorDbGroups]);

  const handleBulkDelete = useCallback(async () => {
    const deleteCount = selectedExperiments.size;
    setDeleting(true);
    try {
      await Promise.all(
        Array.from(selectedExperiments).map(id => deleteExperiment(id))
      );
      setSelectedExperiments(new Set());
      setShowDeleteModal(false);
      const refreshed = await getExperiments();
      setExperiments(refreshed);
      setError(null);
      devInfo('ExperimentsScreen', `bulk delete OK — removed ${deleteCount} experiment(s)`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to delete experiments';
      devWarn('ExperimentsScreen', `bulk delete failed — ${msg}`);
      setError(msg);
      setShowDeleteModal(false);
    } finally {
      setDeleting(false);
    }
  }, [selectedExperiments]);

  const toggleCollapse = useCallback((experimentId: string) => {
    setCollapsedExperiments(prev => {
      const next = new Set(prev);
      if (next.has(experimentId)) {
        next.delete(experimentId);
      } else {
        next.add(experimentId);
      }
      localStorage.setItem('collapsedExperiments', JSON.stringify(Array.from(next)));
      return next;
    });
  }, []);

  const aliveRef = useRef(true);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const statsPollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollDevLogAtRef = useRef(new Map<string, number>());
  const vectorDbStatsInFlightRef = useRef<Promise<void> | null>(null);

  const loadVectorDbStats = useCallback(async (options?: { silent?: boolean }) => {
    if (!aliveRef.current) return;
    if (vectorDbStatsInFlightRef.current !== null) {
      return vectorDbStatsInFlightRef.current;
    }

    const request = (async () => {
      const showSpinner = !options?.silent && vectorDbGroups.length === 0;
      if (showSpinner) setVectorDbLoading(true);
      try {
        const payload = await getVectorDbStatsGrouped();
        if (!aliveRef.current) return;
        setVectorDbGroups(payload.groups);
        setVectorDbError(null);
      } catch (err) {
        if (!aliveRef.current) return;
        const msg = err instanceof Error ? err.message : 'Failed to load vector DB stats';
        devWarn('ExperimentsScreen', `vector DB stats load failed — ${msg}`);
        setVectorDbError(msg);
      } finally {
        vectorDbStatsInFlightRef.current = null;
        if (aliveRef.current && showSpinner) setVectorDbLoading(false);
      }
    })();

    vectorDbStatsInFlightRef.current = request;
    return request;
  }, [vectorDbGroups.length]);

  useEffect(() => {
    if (!initialLoadDone) return;
    onCacheUpdate?.({ experiments, vectorDbGroups });
  }, [experiments, vectorDbGroups, initialLoadDone, onCacheUpdate]);

  useEffect(() => {
    aliveRef.current = true;
    const abortInitial = new AbortController();

    const stall = createStallWatcher({
      scope: 'ExperimentsScreen',
      operation: 'initial list load',
      alive: () => aliveRef.current,
      afterMs: LOADING_STALL_AFTER_MS,
      repeatMs: LOADING_STALL_REPEAT_MS,
      onWarning: (text) => setFeed((f) => appendFeed(f, text, 'warning')),
    });

    function startPollTimers() {
      async function silentPoll() {
        if (!aliveRef.current) return;
        setIsPolling(true);
        try {
          const rows = await getExperiments();
          if (!aliveRef.current) return;
          setExperiments(rows);
          setError(null);
          devInfoThrottled(
            'ExperimentsScreen',
            'poll:experiments',
            DEV_POLL_LOG_INTERVAL_MS,
            `List poll OK — ${rows.length} experiment(s)`,
            pollDevLogAtRef.current,
          );
        } catch (pollErr) {
          if (!aliveRef.current) return;
          const pollMsg =
            pollErr instanceof Error ? pollErr.message : 'Polling failed — check server connectivity.';
          devWarn('ExperimentsScreen', `list poll failed — ${pollMsg}`);
          setError(pollMsg);
        } finally {
          if (aliveRef.current) setIsPolling(false);
        }
      }

      async function silentStatsPoll() {
        if (!aliveRef.current) return;
        await loadVectorDbStats({ silent: true });
      }

      if (pollTimerRef.current !== null) window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = setInterval(silentPoll, EXPERIMENTS_POLL_MS);

      if (statsPollTimerRef.current !== null) window.clearInterval(statsPollTimerRef.current);
      statsPollTimerRef.current = setInterval(silentStatsPoll, VECTOR_DB_STATS_POLL_MS);
    }

    if (cacheReady) {
      devInfo(
        'ExperimentsScreen',
        `cache restore — ${cachedExperiments?.length ?? 0} experiment(s), polling every ${EXPERIMENTS_POLL_MS}ms`,
      );
      startPollTimers();
      void loadVectorDbStats({ silent: (cachedVectorDbGroups?.length ?? 0) > 0 });
      void getExperiments()
        .then((rows) => {
          if (!aliveRef.current) return;
          setExperiments(rows);
          setError(null);
        })
        .catch((err) => {
          devWarn('ExperimentsScreen', `background list refresh failed — ${String(err)}`);
        });
      return () => {
        aliveRef.current = false;
        if (pollTimerRef.current !== null) {
          clearInterval(pollTimerRef.current);
          pollTimerRef.current = null;
        }
        if (statsPollTimerRef.current !== null) {
          clearInterval(statsPollTimerRef.current);
          statsPollTimerRef.current = null;
        }
      };
    }

    async function bootstrap() {
      devInfo('ExperimentsScreen', 'list load started');
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
        setExperiments(data);
        setError(null);
        devInfo('ExperimentsScreen', `list load OK — ${data.length} experiment(s)`);
        void loadVectorDbStats();
        if (!aliveRef.current) return;
        setFeed((f) => appendFeed(f, 'Experiments loaded — vector DB stats loading above.', 'default'));
      } catch (err) {
        stall.stop();
        if (!aliveRef.current) return;
        if (err instanceof DOMException && err.name === 'AbortError') return;
        const msg = err instanceof Error ? err.message : 'Failed to load experiments';
        devWarn('ExperimentsScreen', `list load failed — ${msg}`);
        setError(msg);
        setFeed((f) => appendFeed(f, `Failed: ${msg}`, 'warning'));
      } finally {
        stall.stop();
        if (aliveRef.current) {
          setLoading(false);
          setInitialLoadDone(true);
          devInfo(
            'ExperimentsScreen',
            `poll started — list every ${EXPERIMENTS_POLL_MS}ms, vector DB stats every ${VECTOR_DB_STATS_POLL_MS}ms`,
          );
          startPollTimers();
        }
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
      if (statsPollTimerRef.current !== null) {
        clearInterval(statsPollTimerRef.current);
        statsPollTimerRef.current = null;
      }
    };
  }, [cacheReady, loadVectorDbStats, cachedExperiments?.length, cachedVectorDbGroups?.length]);

  const showLoadingPanel = shouldShowLoadingPanel(initialLoadDone, loading, error);
  const showEmptyConfirmed =
    initialLoadDone &&
    !loading &&
    !isPolling &&
    experiments.length === 0 &&
    error === null;

  const loadingPanelTitle = !initialLoadDone
    ? 'Connecting to server'
    : experiments.length === 0
      ? 'Checking for experiments'
      : 'Refreshing experiments';

  const loadingPanelSubtitle = !initialLoadDone
    ? 'Contacting the API, loading experiment list, then vector database stats.'
    : 'Waiting for the server to finish this refresh cycle.';

  const pageHint = showLoadingPanel
    ? 'Loading experiments from your server.'
    : `Compare sweep progress, then open an experiment to inspect its configuration and run results. Live state refreshes every ${EXPERIMENTS_POLL_MS / 1000}s.`;

  return (
    <DashboardShell
      asideWidthClass="w-full lg:w-60"
      hideSidebarOnCompact
      header={
        <AppPageChrome
          tone="darkFrame"
          pageEyebrow="Sweep workspace"
          pageTitle="Experiments"
          pageHint={pageHint}
        />
      }
      sidebar={experimentsRailHelp()}
    >
      <section
        className="mb-5 flex flex-col gap-4 rounded-panel border border-line bg-paper p-5 shadow-panel sm:flex-row sm:items-end sm:justify-between"
        aria-labelledby="decision-workspace-title"
      >
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-accent-strong">Decision workspace</p>
          <h2 id="decision-workspace-title" className="mt-1 font-display text-2xl font-semibold leading-tight text-ink">
            Compare sweep results to choose a RAG configuration.
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted">
            Start with lifecycle state and sweep health. Open an experiment to connect its identity and configuration to the runs and stored results already produced.
          </p>
        </div>
        <div className="shrink-0 rounded-xl border border-accent bg-accent-soft px-4 py-3 text-right">
          <div className="font-display text-2xl font-semibold text-accent-strong">
            {initialLoadDone ? experiments.length : '—'}
          </div>
          <div className="text-xs font-bold uppercase tracking-widest text-accent-strong">Experiments</div>
        </div>
      </section>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</div>
      )}

      {showLoadingPanel && (
        <div className="flex justify-center py-8">
          <LoadingFeedbackPanel
            title={loadingPanelTitle}
            subtitle={loadingPanelSubtitle}
            feed={feed}
            receivedBytes={receivedBytes}
            totalBytes={totalBytes}
            footer={
              initialLoadDone
                ? `List auto-refreshes every ${EXPERIMENTS_POLL_MS / 1000}s once connected.`
                : `After load, list refreshes every ${EXPERIMENTS_POLL_MS / 1000}s.`
            }
            theme="light"
            expectPayloadProgress={!initialLoadDone || receivedBytes !== null}
          />
        </div>
      )}

      {showEmptyConfirmed && (
        <div className="rounded-panel border border-line bg-paper p-8 text-center shadow-panel sm:p-12">
          <p className="text-xs font-bold uppercase tracking-widest text-accent-strong">Start with a sweep</p>
          <h2 className="mt-2 font-display text-2xl font-semibold text-ink">No experiments yet</h2>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-muted">
            The server is connected and returned an empty list. Submit the first sweep from the CLI, then return here to follow its lifecycle and inspect its results.
          </p>
          <code className="mx-auto mt-4 block max-w-xl overflow-x-auto rounded-xl border border-line bg-canvas p-3 text-left text-xs text-ink">
            rag-params-finder run --config configs/example-mongodb-local.yaml
          </code>
        </div>
      )}

      {!showLoadingPanel && experiments.length > 0 && (() => {
          const startIndex = (currentPage - 1) * itemsPerPage;
          const endIndex = startIndex + itemsPerPage;
          const paginatedExperiments = experiments.slice(startIndex, endIndex);
          const selectableCount = experiments.filter(exp => exp.status !== 'running').length;
          const allSelectableSelected = selectableCount > 0 && selectedExperiments.size === selectableCount;
          const statsByExperimentId = experimentStatsMap(vectorDbGroups);

          return (
            <>
              {selectedExperiments.size > 0 && (
                <div className="mb-4 flex flex-col gap-3 rounded-xl border border-accent bg-accent-soft px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="text-sm font-semibold text-ink">
                      {selectedExperiments.size} experiment{selectedExperiments.size > 1 ? 's' : ''} selected
                    </span>
                    <button
                      type="button"
                      onClick={() => setSelectedExperiments(new Set())}
                      className="min-h-11 rounded-lg px-2 text-xs font-semibold text-accent-strong underline underline-offset-4 hover:bg-white/50"
                    >
                      Clear selection
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowDeleteModal(true)}
                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-red-300 bg-red-50 px-4 text-sm font-semibold text-red-800 transition-colors hover:bg-red-100"
                  >
                    <TrashIcon />
                    Delete {selectedExperiments.size}
                  </button>
                </div>
              )}
              <label className="mb-3 flex min-h-11 w-fit cursor-pointer items-center gap-3 rounded-lg border border-line bg-paper px-3 text-xs font-bold uppercase tracking-wider text-muted shadow-panel">
                <input
                  type="checkbox"
                  checked={allSelectableSelected}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  className="h-5 w-5 rounded border-line text-accent"
                />
                Select all deletable experiments
              </label>
              <div className="space-y-3">
                {paginatedExperiments.map((exp) => {
                  const isSelected = selectedExperiments.has(exp.experiment_id);
                  const isRunning = isRunningExperimentStatus(exp.status, exp.completed_at);
                  const isPaused = isPausedExperimentStatus(exp.status, exp.completed_at);
                  const isCollapsed = collapsedExperiments.has(exp.experiment_id);
                  const dbStats = statsByExperimentId.get(exp.experiment_id);
                  const showRowControls = isRunning || isPaused;
                  const detailsRegionId = `experiment-details-${exp.experiment_id}`;
                  return (
                    <div
                      key={exp.experiment_id}
                      className={`overflow-hidden rounded-panel border border-l-4 bg-paper shadow-panel transition-all hover:-translate-y-0.5 hover:shadow-lift ${statusEdgeClass(exp.status)} ${
                        isSelected ? 'border-accent ring-2 ring-accent-soft' : 'border-y-line border-r-line'
                      }`}
                    >
                      <div className="flex flex-wrap items-start gap-2 p-4">
                        <label
                          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg ${isRunning ? 'cursor-not-allowed' : 'cursor-pointer hover:bg-canvas'}`}
                          title={isRunning ? 'Cannot delete running experiment' : 'Select experiment for deletion'}
                        >
                          <span className="sr-only">Select {exp.experiment_name}</span>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            disabled={isRunning}
                            onChange={(e) => handleSelectExperiment(exp.experiment_id, e.target.checked)}
                            className="h-5 w-5 rounded border-line text-accent disabled:cursor-not-allowed disabled:opacity-40"
                          />
                        </label>
                        <button
                          type="button"
                          onClick={() => toggleCollapse(exp.experiment_id)}
                          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-muted transition-colors hover:bg-canvas hover:text-ink"
                          aria-label={isCollapsed ? `Expand ${exp.experiment_name}` : `Collapse ${exp.experiment_name}`}
                          aria-expanded={!isCollapsed}
                          aria-controls={detailsRegionId}
                        >
                          <svg
                            className={`h-4 w-4 transition-transform ${isCollapsed ? '' : 'rotate-90'}`}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            aria-hidden="true"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          onClick={() => onSelect?.(exp)}
                          className="min-w-56 flex-1 rounded-lg px-2 py-1 text-left"
                        >
                          <span className="block text-xs font-bold uppercase tracking-widest text-accent-strong">Experiment</span>
                          <span className="mt-0.5 block truncate font-display text-lg font-semibold text-ink sm:text-xl">{exp.experiment_name}</span>
                          <span className="mt-1 block text-sm leading-snug text-muted">{experimentOutcomeLabel(exp)}</span>
                          <span className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                            <span className="font-mono">{exp.experiment_id.slice(0, 8)}…</span>
                            <span>{new Date(exp.created_at).toLocaleString()}</span>
                            {exp.failed_count ? <span className="font-semibold text-red-700">{exp.failed_count} failed</span> : null}
                            {isCollapsed && dbStats ? <span>{dbStats.total_results.toLocaleString()} stored results</span> : null}
                          </span>
                          <span className="mt-3 inline-flex items-center gap-1 text-xs font-bold uppercase tracking-widest text-accent-strong">
                            View experiment <ArrowRightIcon />
                          </span>
                        </button>
                        <div className="flex w-full shrink-0 flex-wrap items-center justify-between gap-2 sm:w-auto sm:flex-col sm:items-end">
                          <span
                            className={`inline-flex min-h-8 items-center rounded-full border px-3 text-xs font-bold uppercase tracking-wide ${statusBadgeClass(exp.status)}`}
                          >
                            {exp.status}
                          </span>
                          {showRowControls && (
                            <ExperimentControlButtons
                              experimentId={exp.experiment_id}
                              status={exp.status}
                              size="sm"
                              onStatusChange={refreshExperimentList}
                              onError={(message) => setError(message)}
                            />
                          )}
                        </div>
                      </div>
                      {!isCollapsed && (
                        <div id={detailsRegionId} className="space-y-4 border-t border-line bg-canvas px-4 py-4">
                          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                            <div>
                              <div className="text-xs font-bold uppercase tracking-wider text-muted">Experiment ID</div>
                              <button
                                type="button"
                                onClick={() => onSelect?.(exp)}
                                className="inline-flex min-h-11 items-center font-mono text-sm text-cobalt hover:underline"
                              >
                                {exp.experiment_id.slice(0, 8)}...
                              </button>
                            </div>
                            <div>
                              <div className="text-xs font-bold uppercase tracking-wider text-muted">Runs</div>
                              <div className="mt-2 text-sm text-ink">
                                {exp.run_count ?? '—'}
                                {exp.failed_count ? (
                                  <span className="ml-1 text-red-500">({exp.failed_count} failed)</span>
                                ) : null}
                              </div>
                            </div>
                            <div>
                              <div className="text-xs font-bold uppercase tracking-wider text-muted">Git Commit</div>
                              <div className="mt-2 font-mono text-sm text-ink">{exp.git_commit?.slice(0, 8) ?? '—'}</div>
                            </div>
                            <div>
                              <div className="text-xs font-bold uppercase tracking-wider text-muted">Created</div>
                              <div className="mt-2 text-sm text-ink">{new Date(exp.created_at).toLocaleString()}</div>
                            </div>
                          </div>
                          <ExperimentVectorDbStatsCard
                            experimentId={exp.experiment_id}
                            stats={dbStats}
                            loading={vectorDbLoading && !dbStats}
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              <div className="overflow-hidden rounded-panel border border-line bg-paper shadow-panel">
                <Pagination
                  currentPage={currentPage}
                  totalItems={experiments.length}
                  itemsPerPage={itemsPerPage}
                  onPageChange={setCurrentPage}
                  onItemsPerPageChange={handleItemsPerPageChange}
                />
              </div>
            </>
          );
      })()}

      {initialLoadDone && !showLoadingPanel && (
        <div className="mt-4 flex flex-wrap items-center justify-center gap-3 text-xs text-muted">
          <span>Auto-refresh every {EXPERIMENTS_POLL_MS / 1000}s</span>
          <PollingIndicator active={isPolling} />
        </div>
      )}

      <section className="mt-8 border-t border-line pt-6" aria-labelledby="operational-context-title">
        <p className="text-xs font-bold uppercase tracking-widest text-accent-strong">Progressive disclosure</p>
        <h2 id="operational-context-title" className="mt-1 font-display text-xl font-semibold text-ink">Operational storage context</h2>
        <p className="mb-4 mt-1 text-sm text-muted">Storage metrics stay available without competing with experiment lifecycle and run outcomes.</p>
        <VectorDbStatsPanel
          groups={vectorDbGroups}
          loading={vectorDbLoading}
          error={vectorDbError}
        />
      </section>

      <ConfirmDeleteModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleBulkDelete}
        experimentName={selectedExperiments.size === 1 ?
          experiments.find(e => e.experiment_id === Array.from(selectedExperiments)[0])?.experiment_name || ''
          : ''}
        experimentId={selectedExperiments.size === 1 ? Array.from(selectedExperiments)[0] : ''}
        isDeleting={deleting}
        isBulk={selectedExperiments.size > 1}
        bulkCount={selectedExperiments.size}
      />
    </DashboardShell>
  );
}
