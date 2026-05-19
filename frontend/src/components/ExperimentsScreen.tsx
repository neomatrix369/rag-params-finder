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
import { devDebugThrottled, devWarn } from '../utils/devLog';
import { isPausedExperimentStatus, isRunningExperimentStatus } from '../utils/experimentStatus';

let feedSeq = 0;

function appendFeed(prev: FeedEntry[], text: string, variant: FeedEntry['variant']): FeedEntry[] {
  feedSeq += 1;
  return [...prev, { id: `${Date.now()}-${feedSeq}`, text, variant }];
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
    <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-t border-slate-200">
      <div className="flex items-center gap-4">
        <span className="text-sm text-slate-600">
          Showing <span className="font-medium">{startItem}</span> to{' '}
          <span className="font-medium">{endItem}</span> of{' '}
          <span className="font-medium">{totalItems}</span>
        </span>
        <div className="flex items-center gap-2">
          <label htmlFor="experiments-per-page" className="text-sm text-slate-600">
            Per page:
          </label>
          <select
            id="experiments-per-page"
            value={itemsPerPage}
            onChange={(e) => onItemsPerPageChange(Number(e.target.value))}
            className="rounded border border-slate-300 bg-white px-2 py-1 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          >
            <option value={10}>10</option>
            <option value={15}>15</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-white"
        >
          Previous
        </button>
        <span className="text-sm text-slate-600">
          Page <span className="font-medium">{currentPage}</span> of{' '}
          <span className="font-medium">{totalPages}</span>
        </span>
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-white"
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
        <div className="text-sm font-semibold text-slate-200">Sidebar</div>
        <div className="mt-0.5 text-[11px] uppercase tracking-wider text-slate-500">Experiment list</div>
      </div>
      <div className="rounded-lg border border-slate-600/50 bg-slate-700/40 px-3 py-3 text-xs leading-relaxed text-slate-300 ring-1 ring-slate-600/35">
        Running sweeps show Pause and Cancel on each row. Paused sweeps show Resume. Open an experiment for the same controls in the page header.
      </div>
    </>
  );
}

function statusBadgeClass(status: Experiment['status']): string {
  if (status === 'complete') return 'bg-green-100 text-green-700';
  if (status === 'running') return 'bg-blue-100 text-blue-700';
  if (status === 'partial') return 'bg-yellow-100 text-yellow-700';
  if (status === 'failed') return 'bg-red-100 text-red-700';
  if (status === 'cancelled') return 'bg-orange-100 text-orange-700';
  if (status === 'paused') return 'bg-violet-100 text-violet-700';
  return 'bg-slate-100 text-slate-700';
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

/** True when we should show the full-page loading overlay (experiment list fetch only). */
function shouldShowLoadingPanel(
  initialLoadDone: boolean,
  loading: boolean,
  isPolling: boolean,
  experimentsCount: number,
  error: string | null,
): boolean {
  if (error !== null) return false;
  if (!initialLoadDone || loading) return true;
  if (experimentsCount === 0 && isPolling) return true;
  return false;
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete experiments');
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
      if (!options?.silent) setVectorDbLoading(true);
      try {
        const payload = await getVectorDbStatsGrouped();
        if (!aliveRef.current) return;
        setVectorDbGroups(payload.groups);
        setVectorDbError(null);
      } catch (err) {
        if (!aliveRef.current) return;
        setVectorDbError(err instanceof Error ? err.message : 'Failed to load vector DB stats');
      } finally {
        vectorDbStatsInFlightRef.current = null;
        if (aliveRef.current && !options?.silent) setVectorDbLoading(false);
      }
    })();

    vectorDbStatsInFlightRef.current = request;
    return request;
  }, []);

  useEffect(() => {
    if (!initialLoadDone) return;
    onCacheUpdate?.({ experiments, vectorDbGroups });
  }, [experiments, vectorDbGroups, initialLoadDone, onCacheUpdate]);

  useEffect(() => {
    aliveRef.current = true;
    const abortInitial = new AbortController();

    const stall = createStallWatcher({
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
          devDebugThrottled(
            'poll:experiments',
            DEV_POLL_LOG_INTERVAL_MS,
            `Poll OK — ${rows.length} experiment(s)`,
            pollDevLogAtRef.current,
          );
        } catch (pollErr) {
          if (!aliveRef.current) return;
          const pollMsg =
            pollErr instanceof Error ? pollErr.message : 'Polling failed — check server connectivity.';
          devWarn('Experiments poll failed:', pollMsg);
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
      startPollTimers();
      void loadVectorDbStats({ silent: (cachedVectorDbGroups?.length ?? 0) > 0 });
      void getExperiments()
        .then((rows) => {
          if (!aliveRef.current) return;
          setExperiments(rows);
          setError(null);
        })
        .catch(() => undefined);
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
        void loadVectorDbStats();
        if (!aliveRef.current) return;
        setFeed((f) => appendFeed(f, 'Experiments loaded — vector DB stats loading above.', 'default'));
      } catch (err) {
        stall.stop();
        if (!aliveRef.current) return;
        if (err instanceof DOMException && err.name === 'AbortError') return;
        const msg = err instanceof Error ? err.message : 'Failed to load experiments';
        devWarn('Initial experiments load failed:', msg);
        setError(msg);
        setFeed((f) => appendFeed(f, `Failed: ${msg}`, 'warning'));
      } finally {
        stall.stop();
        if (!aliveRef.current) return;
        setLoading(false);
        setInitialLoadDone(true);
        startPollTimers();
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
  }, [cacheReady, loadVectorDbStats]);

  const showLoadingPanel = shouldShowLoadingPanel(
    initialLoadDone,
    loading,
    isPolling,
    experiments.length,
    error,
  );
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
    ? 'Loading experiment list and vector database stats from your server.'
    : `History and live status for every sweep. This table refreshes every ${EXPERIMENTS_POLL_MS / 1000}s while you keep the page open.`;

  return (
    <DashboardShell
      asideWidthClass="w-56 lg:w-60"
      header={
        <AppPageChrome
          tone="darkFrame"
          pageTitle="Experiments"
          pageHint={pageHint}
        />
      }
      sidebar={experimentsRailHelp()}
    >
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
      )}

      <VectorDbStatsPanel
        groups={vectorDbGroups}
        loading={vectorDbLoading}
        error={vectorDbError}
      />

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
          <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-sm">
            <div className="mb-2 text-lg text-slate-400">No experiments yet</div>
            <div className="text-sm text-slate-500">
              The server is connected and returned an empty list. Submit your first experiment using the CLI:
              <code className="mt-2 block rounded bg-slate-100 p-2 text-xs">
                rag-params-finder run --config configs/example.yaml
              </code>
            </div>
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
                <div className="mb-4 flex items-center justify-between rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-blue-900">
                      {selectedExperiments.size} experiment{selectedExperiments.size > 1 ? 's' : ''} selected
                    </span>
                    <button
                      onClick={() => setSelectedExperiments(new Set())}
                      className="text-xs text-blue-600 hover:text-blue-800 underline"
                    >
                      Clear selection
                    </button>
                  </div>
                  <button
                    onClick={() => setShowDeleteModal(true)}
                    className="rounded-lg border border-red-300 bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
                  >
                    🗑 Delete {selectedExperiments.size}
                  </button>
                </div>
              )}
              <div className="mb-3 flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                <input
                  type="checkbox"
                  checked={allSelectableSelected}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
                  Select all deletable experiments
                </span>
              </div>
              <div className="space-y-3">
                {paginatedExperiments.map((exp) => {
                  const isSelected = selectedExperiments.has(exp.experiment_id);
                  const isRunning = isRunningExperimentStatus(exp.status);
                  const isPaused = isPausedExperimentStatus(exp.status);
                  const isCollapsed = collapsedExperiments.has(exp.experiment_id);
                  const dbStats = statsByExperimentId.get(exp.experiment_id);
                  const showRowControls = isRunning || isPaused;
                  return (
                    <div
                      key={exp.experiment_id}
                      className={`overflow-hidden rounded-xl border bg-white shadow-sm transition-colors ${
                        isSelected ? 'border-blue-300 ring-1 ring-blue-200' : 'border-slate-200'
                      }`}
                    >
                      <div className="flex items-center gap-3 px-4 py-4">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          disabled={isRunning}
                          onChange={(e) => handleSelectExperiment(exp.experiment_id, e.target.checked)}
                          className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
                          title={isRunning ? 'Cannot delete running experiment' : ''}
                        />
                        <button
                          type="button"
                          onClick={() => toggleCollapse(exp.experiment_id)}
                          className="rounded p-1 transition-colors hover:bg-slate-100"
                          title={isCollapsed ? 'Expand details' : 'Collapse details'}
                        >
                          <svg
                            className={`h-4 w-4 text-slate-600 transition-transform ${isCollapsed ? '' : 'rotate-90'}`}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          onClick={() => onSelect?.(exp)}
                          className="min-w-0 flex-1 text-left"
                        >
                          <div className="truncate text-sm font-semibold text-slate-900">{exp.experiment_name}</div>
                          {isCollapsed && (
                            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                              <span className={`inline-flex rounded px-2 py-0.5 font-bold ${statusBadgeClass(exp.status)}`}>
                                {exp.status}
                              </span>
                              <span>{exp.run_count ?? '—'} runs</span>
                              {exp.failed_count ? <span className="text-red-500">({exp.failed_count} failed)</span> : null}
                              {dbStats ? (
                                <>
                                  <span>{dbStats.total_chunks.toLocaleString()} chunks</span>
                                  <span>{dbStats.total_results.toLocaleString()} results</span>
                                  <span>{dbStats.estimated_storage_mb} MB</span>
                                </>
                              ) : null}
                              <span>{new Date(exp.created_at).toLocaleString()}</span>
                            </div>
                          )}
                        </button>
                        <div className="flex shrink-0 flex-col items-end gap-2 sm:flex-row sm:items-center">
                          {showRowControls && (
                            <ExperimentControlButtons
                              experimentId={exp.experiment_id}
                              status={exp.status}
                              size="sm"
                              onStatusChange={refreshExperimentList}
                              onError={(message) => setError(message)}
                            />
                          )}
                          <span
                            className={`inline-flex rounded px-2 py-1 text-xs font-bold ${statusBadgeClass(exp.status)}`}
                          >
                            {exp.status}
                          </span>
                        </div>
                      </div>
                      {!isCollapsed && (
                        <div className="space-y-4 border-t border-slate-100 bg-slate-50/60 px-4 py-4">
                          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                            <div>
                              <div className="text-xs uppercase tracking-wider text-slate-500">Experiment ID</div>
                              <button
                                type="button"
                                onClick={() => onSelect?.(exp)}
                                className="font-mono text-sm text-blue-700 hover:underline"
                              >
                                {exp.experiment_id.slice(0, 8)}...
                              </button>
                            </div>
                            <div>
                              <div className="text-xs uppercase tracking-wider text-slate-500">Runs</div>
                              <div className="text-sm text-slate-800">
                                {exp.run_count ?? '—'}
                                {exp.failed_count ? (
                                  <span className="ml-1 text-red-500">({exp.failed_count} failed)</span>
                                ) : null}
                              </div>
                            </div>
                            <div>
                              <div className="text-xs uppercase tracking-wider text-slate-500">Git Commit</div>
                              <div className="font-mono text-sm text-slate-700">{exp.git_commit?.slice(0, 8) ?? '—'}</div>
                            </div>
                            <div>
                              <div className="text-xs uppercase tracking-wider text-slate-500">Created</div>
                              <div className="text-sm text-slate-700">{new Date(exp.created_at).toLocaleString()}</div>
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
              <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
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
        <div className="mt-4 flex items-center justify-center gap-3 text-xs text-slate-500">
          <span>Auto-refresh every {EXPERIMENTS_POLL_MS / 1000}s</span>
          <PollingIndicator active={isPolling} />
        </div>
      )}

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
