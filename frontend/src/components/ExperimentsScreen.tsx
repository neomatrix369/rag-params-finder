import { useCallback, useEffect, useRef, useState } from 'react';
import {
  EXPERIMENTS_POLL_MS,
  LOADING_STALL_AFTER_MS,
  LOADING_STALL_REPEAT_MS,
} from '../constants';
import AppPageChrome from './AppPageChrome';
import DashboardShell from './DashboardShell';
import LoadingFeedbackPanel, { type FeedEntry } from './LoadingFeedbackPanel';
import PollingIndicator from './PollingIndicator';
import ConfirmDeleteModal from './ConfirmDeleteModal';
import { createStallWatcher, type FetchProgressUpdate } from '../services/fetchWithProgress';
import { deleteExperiment, getExperiments, getExperimentsWithProgress } from '../services/apiClient';
import { Experiment } from '../types';

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
        This table polls the experiments API continuously so you never miss a sweep finishing.
      </div>
    </>
  );
}

export default function ExperimentsScreen({ onSelect }: { onSelect?: (id: string) => void }) {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(false);
  const [initialLoadDone, setInitialLoadDone] = useState(false);
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
          setIsPolling(true);
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
          } finally {
            if (aliveRef.current) setIsPolling(false);
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

        {experiments.length > 0 && (() => {
          const startIndex = (currentPage - 1) * itemsPerPage;
          const endIndex = startIndex + itemsPerPage;
          const paginatedExperiments = experiments.slice(startIndex, endIndex);
          const selectableCount = experiments.filter(exp => exp.status !== 'running').length;
          const allSelectableSelected = selectableCount > 0 && selectedExperiments.size === selectableCount;

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
              <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                <table className="w-full">
                  <thead className="border-b border-slate-200 bg-slate-50">
                    <tr>
                      <th className="px-4 py-3 text-left w-12">
                        <input
                          type="checkbox"
                          checked={allSelectableSelected}
                          onChange={(e) => handleSelectAll(e.target.checked)}
                          className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
                        />
                      </th>
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
                    {paginatedExperiments.map((exp) => {
                      const isSelected = selectedExperiments.has(exp.experiment_id);
                      const isRunning = exp.status === 'running';
                      return (
                        <tr
                          key={exp.experiment_id}
                          className={`transition-colors ${isSelected ? 'bg-blue-50' : 'hover:bg-slate-50'}`}
                        >
                          <td className="px-4 py-4" onClick={(e) => e.stopPropagation()}>
                            <input
                              type="checkbox"
                              checked={isSelected}
                              disabled={isRunning}
                              onChange={(e) => handleSelectExperiment(exp.experiment_id, e.target.checked)}
                              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
                              title={isRunning ? 'Cannot delete running experiment' : ''}
                            />
                          </td>
                          <td
                            className="px-6 py-4 text-sm font-medium text-slate-900 cursor-pointer"
                            onClick={() => onSelect?.(exp.experiment_id)}
                          >
                            {exp.experiment_name}
                          </td>
                          <td
                            className="px-6 py-4 font-mono text-sm text-slate-600 cursor-pointer"
                            onClick={() => onSelect?.(exp.experiment_id)}
                          >
                            {exp.experiment_id.slice(0, 8)}...
                          </td>
                          <td
                            className="px-6 py-4 font-mono text-sm text-slate-600 cursor-pointer"
                            onClick={() => onSelect?.(exp.experiment_id)}
                          >
                            {exp.run_count ?? '—'}
                            {exp.failed_count ? (
                              <span className="ml-1 text-red-500">({exp.failed_count} failed)</span>
                            ) : null}
                          </td>
                          <td
                            className="px-6 py-4 cursor-pointer"
                            onClick={() => onSelect?.(exp.experiment_id)}
                          >
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
                          <td
                            className="px-6 py-4 font-mono text-sm text-slate-500 cursor-pointer"
                            onClick={() => onSelect?.(exp.experiment_id)}
                          >
                            {exp.git_commit ?? '—'}
                          </td>
                          <td
                            className="px-6 py-4 text-sm text-slate-600 cursor-pointer"
                            onClick={() => onSelect?.(exp.experiment_id)}
                          >
                            {new Date(exp.created_at).toLocaleString()}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
              </table>
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

      <div className="mt-4 flex items-center justify-center gap-3 text-xs text-slate-500">
        <span>Polling every {EXPERIMENTS_POLL_MS / 1000}s</span>
        <PollingIndicator active={isPolling && !loading} />
      </div>

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
