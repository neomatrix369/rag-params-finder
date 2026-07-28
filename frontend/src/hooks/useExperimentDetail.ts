/**
 * Hydrate + poll + db-stats controller for ExperimentDetailScreen.
 * API client functions are injected for testability.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  DETAIL_POLL_MS,
  DEV_POLL_LOG_INTERVAL_MS,
  LOADING_STALL_AFTER_MS,
  LOADING_STALL_REPEAT_MS,
  VECTOR_DB_STATS_POLL_MS,
} from '../constants';
import type { FeedEntry } from '../components/LoadingFeedbackPanel';
import type { ExperimentDetail } from '../components/experimentDetail/types';
import {
  deleteExperiment,
  getExperiment,
  getExperimentDbStats,
  getExperimentWithProgress,
  type ExperimentProgressCallback,
} from '../services/apiClient';
import { createStallWatcher, type FetchProgressUpdate } from '../services/fetchWithProgress';
import type { Experiment, ExperimentDbStatsSummary, ExperimentStatus } from '../types';
import { appendFeedEntry } from '../utils/feedEntries';
import { toExperimentDbStatsSummary } from '../utils/experimentDbStats';
import { devInfo, devInfoThrottled, devWarn } from '../utils/devLog';
import {
  isRunningExperimentStatus,
  isTerminalExperimentStatus,
} from '../utils/experimentStatus';

export type UseExperimentDetailArgs = {
  experimentId: string;
  initialExperiment?: Experiment;
  initialDbStats?: ExperimentDbStatsSummary;
  onDeleted?: () => void;
};

export function useExperimentDetail({
  experimentId,
  initialExperiment,
  initialDbStats,
  onDeleted,
}: UseExperimentDetailArgs) {
  const seededDetail =
    initialExperiment?.experiment_id === experimentId
      ? (initialExperiment as unknown as ExperimentDetail)
      : null;

  const [detail, setDetail] = useState<ExperimentDetail | null>(seededDetail);
  const [error, setError] = useState<string | null>(null);
  const [hydrating, setHydrating] = useState(seededDetail === null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [loadFeed, setLoadFeed] = useState<FeedEntry[]>([]);
  const [receivedBytes, setReceivedBytes] = useState<number | null>(null);
  const [totalBytes, setTotalBytes] = useState<number | null>(null);

  const [dbStats, setDbStats] = useState<ExperimentDbStatsSummary | null>(initialDbStats ?? null);
  const [dbStatsLoading, setDbStatsLoading] = useState(initialDbStats === undefined);

  const [runsCurrentPage, setRunsCurrentPage] = useState(1);
  const [runsItemsPerPage, setRunsItemsPerPage] = useState(15);

  const handleRunsItemsPerPageChange = useCallback((items: number) => {
    setRunsItemsPerPage(items);
    setRunsCurrentPage(1);
  }, []);

  const aliveRef = useRef(true);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollDevLogAtRef = useRef(new Map<string, number>());
  const dbStatsInFlightRef = useRef<Promise<void> | null>(null);

  const experimentMeta = useCallback((): Pick<Experiment, 'experiment_id' | 'experiment_name' | 'status' | 'created_at'> | null => {
    if (detail) {
      return {
        experiment_id: detail.experiment_id,
        experiment_name: detail.experiment_name,
        status: detail.status,
        created_at: detail.created_at ?? initialExperiment?.created_at ?? new Date(0).toISOString(),
      };
    }
    if (initialExperiment?.experiment_id === experimentId) return initialExperiment;
    return null;
  }, [detail, initialExperiment, experimentId]);

  const loadDbStats = useCallback(
    async (options?: { showLoading?: boolean }) => {
      if (dbStatsInFlightRef.current !== null) {
        return dbStatsInFlightRef.current;
      }

      const request = (async () => {
        const meta = experimentMeta();
        if (!meta) return;
        if (options?.showLoading) setDbStatsLoading(true);
        try {
          const response = await getExperimentDbStats(experimentId);
          setDbStats(toExperimentDbStatsSummary(meta, response.db_stats));
        } catch (err) {
          devWarn('ExperimentDetailScreen', `db stats load failed — ${experimentId.slice(0, 8)}…`, err);
        } finally {
          dbStatsInFlightRef.current = null;
          setDbStatsLoading(false);
        }
      })();

      dbStatsInFlightRef.current = request;
      return request;
    },
    [experimentId, experimentMeta],
  );

  useEffect(() => {
    if (!initialDbStats) {
      void loadDbStats({ showLoading: true });
    }

    const statsTimer = window.setInterval(() => {
      void loadDbStats();
    }, VECTOR_DB_STATS_POLL_MS);

    return () => window.clearInterval(statsTimer);
  }, [experimentId, initialDbStats, loadDbStats]);

  const stopDetailPoll = useCallback(() => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startDetailPollIfRunning = useCallback(
    (status: ExperimentStatus | undefined, completedAt?: string | null) => {
      stopDetailPoll();
      if (!isRunningExperimentStatus(status, completedAt)) return;

      devInfo('ExperimentDetailScreen', `detail poll started — ${experimentId.slice(0, 8)}… every ${DETAIL_POLL_MS}ms`);

      pollRef.current = window.setInterval(async () => {
        if (!aliveRef.current) return;
        try {
          const next = await getExperiment(experimentId);
          if (!aliveRef.current) return;
          setDetail(next as unknown as ExperimentDetail);
          setError(null);
          devInfoThrottled(
            'ExperimentDetailScreen',
            `poll:detail:${experimentId}`,
            DEV_POLL_LOG_INTERVAL_MS,
            `detail poll OK — ${experimentId.slice(0, 8)}… status=${next.status}`,
            pollDevLogAtRef.current,
          );
          if (isTerminalExperimentStatus(next.status, next.completed_at)) {
            stopDetailPoll();
          }
        } catch (pollErr) {
          if (!aliveRef.current) return;
          const pollMsg =
            pollErr instanceof Error ? pollErr.message : 'Could not refresh experiment';
          devWarn('ExperimentDetailScreen', `detail poll failed — ${experimentId.slice(0, 8)}… — ${pollMsg}`);
          setError('Could not refresh experiment — transient network or server error.');
        }
      }, DETAIL_POLL_MS);
    },
    [experimentId, stopDetailPoll],
  );

  useEffect(() => {
    aliveRef.current = true;
    const abortHydrate = new AbortController();

    const stall = createStallWatcher({
      scope: 'ExperimentDetailScreen',
      operation: 'detail hydrate',
      alive: () => aliveRef.current,
      afterMs: LOADING_STALL_AFTER_MS,
      repeatMs: LOADING_STALL_REPEAT_MS,
      onWarning: (text) => setLoadFeed((f) => appendFeedEntry(f, text, 'warning')),
    });

    const applyProg: ExperimentProgressCallback = (u: FetchProgressUpdate) => {
      if (!aliveRef.current) return;
      if (u.type === 'downloading') {
        setReceivedBytes(u.receivedBytes);
        setTotalBytes(u.totalBytes);
        return;
      }
      setLoadFeed((f) =>
        appendFeedEntry(f, u.text, u.variant === 'warning' ? 'warning' : 'default'),
      );
    };

    async function hydrate() {
      const hasSeed = initialExperiment?.experiment_id === experimentId;
      devInfo(
        'ExperimentDetailScreen',
        hasSeed
          ? `hydrate started — refreshing ${experimentId.slice(0, 8)}… (seed from list)`
          : `hydrate started — loading ${experimentId.slice(0, 8)}…`,
      );
      setHydrating(true);
      setError(null);
      if (!hasSeed) {
        setDetail(null);
      }
      setLoadFeed([
        {
          id: 'h0',
          text: hasSeed
            ? 'Refreshing run rows and live status…'
            : 'Fetching experiment and run rows…',
          variant: 'default',
        },
      ]);
      setReceivedBytes(null);
      setTotalBytes(null);
      stall.start();

      stopDetailPoll();

      let loadedStatus: ExperimentStatus | undefined;
      let loadedCompletedAt: string | null | undefined;

      try {
        const loaded = hasSeed
          ? await getExperiment(experimentId, abortHydrate.signal)
          : await getExperimentWithProgress(experimentId, applyProg, abortHydrate.signal);
        stall.stop();
        if (!aliveRef.current) return;
        loadedStatus = loaded.status;
        loadedCompletedAt = loaded.completed_at;
        setDetail(loaded as unknown as ExperimentDetail);
        const runs = (loaded as { runs?: unknown[] }).runs;
        const runRows = Array.isArray(runs) ? runs.length : 0;
        devInfo(
          'ExperimentDetailScreen',
          `hydrate OK — ${experimentId.slice(0, 8)}… status=${loaded.status}, ${runRows} run row(s)`,
        );
        setLoadFeed((f) =>
          appendFeedEntry(
            f,
            isRunningExperimentStatus(loaded.status, loadedCompletedAt)
              ? 'Run rows loaded — live polling while experiment is running.'
              : 'Run rows loaded.',
            'default',
          ),
        );
      } catch (err) {
        stall.stop();
        if (!aliveRef.current) return;
        if (err instanceof DOMException && err.name === 'AbortError') return;
        const msg =
          err instanceof Error ? err.message : 'Failed to load experiment';
        devWarn('ExperimentDetailScreen', `hydrate failed — ${experimentId.slice(0, 8)}… — ${msg}`);
        setError(msg);
        setLoadFeed((f) => appendFeedEntry(f, `Failed: ${msg}`, 'warning'));
      } finally {
        stall.stop();
        if (aliveRef.current) {
          setHydrating(false);
          startDetailPollIfRunning(loadedStatus, loadedCompletedAt);
        }
      }
    }

    void hydrate();

    return () => {
      aliveRef.current = false;
      abortHydrate.abort();
      stall.stop();
      stopDetailPoll();
    };
  }, [experimentId, initialExperiment, startDetailPollIfRunning, stopDetailPoll]);

  const refreshDetailAfterControl = useCallback(async () => {
    const refreshed = await getExperiment(experimentId);
    setDetail(refreshed as unknown as ExperimentDetail);
    const refreshedCompletedAt = refreshed.completed_at;
    if (isRunningExperimentStatus(refreshed.status, refreshedCompletedAt)) {
      startDetailPollIfRunning(refreshed.status, refreshedCompletedAt);
    } else {
      stopDetailPoll();
    }
    setError(null);
  }, [experimentId, startDetailPollIfRunning, stopDetailPoll]);

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteExperiment(experimentId);
      devInfo('ExperimentDetailScreen', `delete OK — experiment ${experimentId.slice(0, 8)}…`);
      setShowDeleteModal(false);
      onDeleted?.();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to delete experiment';
      devWarn('ExperimentDetailScreen', `delete failed — ${experimentId.slice(0, 8)}… — ${msg}`);
      setError(msg);
      setShowDeleteModal(false);
    } finally {
      setDeleting(false);
    }
  }

  return {
    detail,
    error,
    setError,
    hydrating,
    showDeleteModal,
    setShowDeleteModal,
    deleting,
    loadFeed,
    receivedBytes,
    totalBytes,
    dbStats,
    dbStatsLoading,
    runsCurrentPage,
    setRunsCurrentPage,
    runsItemsPerPage,
    handleRunsItemsPerPageChange,
    refreshDetailAfterControl,
    handleDelete,
  };
}
