/**
 * ExperimentDetailScreen
 *
 * Displays comprehensive experiment information with visual hierarchy:
 * - Status badges, metric cards, and progress indicators
 * - Themed metadata sections (Git, Config, Data, Sweep Dimensions)
 * - Enhanced runs table with color-coded badges
 * - Success/failure panels with large visual feedback
 *
 * Design Decisions:
 * - "Embedding Models" (not "Models") to distinguish from reranking models
 * - Voyage rate limit fields only shown when provider is "voyage"
 * - Failed count always visible (even when 0) for consistency
 * - Color system: Blue (primary), Green (success), Red (failure), Amber (warning), Purple (secondary)
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { DETAIL_POLL_MS, LOADING_STALL_AFTER_MS, LOADING_STALL_REPEAT_MS } from '../constants';
import AppPageChrome from './AppPageChrome';
import DashboardShell from './DashboardShell';
import LoadingFeedbackPanel from './LoadingFeedbackPanel';
import type { FeedEntry } from './LoadingFeedbackPanel';
import {
  cancelExperiment,
  getExperiment,
  getExperimentWithProgress,
  type ExperimentProgressCallback,
} from '../services/apiClient';
import { RunStatus, Phase, EnvParams, SweepSummary, ExperimentStatus } from '../types';
import { createStallWatcher, type FetchProgressUpdate } from '../services/fetchWithProgress';

let detailFeedSeq = 0;

function appendDetailFeed(prev: FeedEntry[], text: string, variant: FeedEntry['variant']): FeedEntry[] {
  detailFeedSeq += 1;
  return [...prev, { id: `${Date.now()}-${detailFeedSeq}`, text, variant }];
}

// Icon components (minimal SVG)
const icons = {
  clock: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  check: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
  x: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  play: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  code: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
    </svg>
  ),
  database: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
    </svg>
  ),
  settings: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  grid: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zM14 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
    </svg>
  ),
};

interface ExperimentDetail {
  experiment_id: string;
  experiment_name: string;
  status: ExperimentStatus;
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
  config?: {
    embedding?: {
      provider?: string;
    };
    retrieval?: {
      rerank_provider?: string;
    };
  };
}

const PHASE_ORDER: Phase[] = [
  Phase.QUEUED, Phase.PARSING, Phase.CHUNKING, Phase.EMBEDDING,
  Phase.STORING, Phase.QUERYING, Phase.RERANKING, Phase.COMPLETE,
];

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
          <label htmlFor="runs-per-page" className="text-sm text-slate-600">
            Per page:
          </label>
          <select
            id="runs-per-page"
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

// Status badge with color coding
function StatusBadge({ status }: { status: string }) {
  const config = {
    complete: { bg: 'bg-green-100', text: 'text-green-800', icon: icons.check, ring: 'ring-green-600' },
    running: { bg: 'bg-blue-100', text: 'text-blue-800', icon: icons.play, ring: 'ring-blue-600' },
    failed: { bg: 'bg-red-100', text: 'text-red-800', icon: icons.x, ring: 'ring-red-600' },
    partial: { bg: 'bg-yellow-100', text: 'text-yellow-800', icon: icons.x, ring: 'ring-yellow-600' },
    cancelled: { bg: 'bg-gray-100', text: 'text-gray-800', icon: icons.x, ring: 'ring-gray-600' },
  }[status] || { bg: 'bg-slate-100', text: 'text-slate-800', icon: icons.clock, ring: 'ring-slate-600' };

  return (
    <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full ${config.bg} ${config.text} font-semibold ring-2 ${config.ring}`}>
      {config.icon}
      <span className="uppercase text-sm tracking-wide">{status}</span>
    </div>
  );
}

// Stat card for key metrics
function StatCard({
  label,
  value,
  icon,
  trend,
  color = 'blue'
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: string;
  color?: 'blue' | 'green' | 'purple' | 'amber';
}) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    green: 'bg-green-50 text-green-600 border-green-200',
    purple: 'bg-purple-50 text-purple-600 border-purple-200',
    amber: 'bg-amber-50 text-amber-600 border-amber-200',
  };

  return (
    <div className={`${colors[color]} rounded-xl p-4 border-2 shadow-sm`}>
      <div className="flex items-start justify-between mb-2">
        <div className="p-2 rounded-lg bg-white/80">
          {icon}
        </div>
        {trend && <span className="text-xs font-medium opacity-75">{trend}</span>}
      </div>
      <div className="mt-2">
        <div className="text-2xl font-bold">{value}</div>
        <div className="text-xs font-medium uppercase tracking-wide mt-1 opacity-75">{label}</div>
      </div>
    </div>
  );
}

// Progress ring
function ProgressRing({ percent, size = 80 }: { percent: number; size?: number }) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth="4"
          fill="none"
          className="text-slate-200"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth="4"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="text-green-500 transition-all duration-500"
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute text-lg font-bold text-slate-700">{Math.round(percent)}%</span>
    </div>
  );
}

// Dimension badge for sweep params
function DimensionBadge({ label, values }: { label: string; values: (string | number)[] }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-3">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-2 h-2 rounded-full bg-blue-500"></div>
        <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">{label}</span>
      </div>
      <div className="flex flex-wrap gap-1">
        {values.map((v, i) => (
          <span key={i} className="inline-flex items-center px-2 py-1 rounded-md bg-slate-100 text-slate-700 text-xs font-medium">
            {String(v)}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function ExperimentDetailScreen({
  experimentId,
  onBack,
  onExplore,
}: {
  experimentId: string;
  onBack: () => void;
  onExplore?: () => void;
}) {
  const [detail, setDetail] = useState<ExperimentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hydrating, setHydrating] = useState(true);
  const [cancelling, setCancelling] = useState(false);

  const [loadFeed, setLoadFeed] = useState<FeedEntry[]>([]);
  const [receivedBytes, setReceivedBytes] = useState<number | null>(null);
  const [totalBytes, setTotalBytes] = useState<number | null>(null);

  const [runsCurrentPage, setRunsCurrentPage] = useState(1);
  const [runsItemsPerPage, setRunsItemsPerPage] = useState(15);

  const handleRunsItemsPerPageChange = useCallback((items: number) => {
    setRunsItemsPerPage(items);
    setRunsCurrentPage(1);
  }, []);

  const aliveRef = useRef(true);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    aliveRef.current = true;
    const abortHydrate = new AbortController();

    const stall = createStallWatcher({
      alive: () => aliveRef.current,
      afterMs: LOADING_STALL_AFTER_MS,
      repeatMs: LOADING_STALL_REPEAT_MS,
      onWarning: (text) => setLoadFeed((f) => appendDetailFeed(f, text, 'warning')),
    });

    const applyProg: ExperimentProgressCallback = (u: FetchProgressUpdate) => {
      if (!aliveRef.current) return;
      if (u.type === 'downloading') {
        setReceivedBytes(u.receivedBytes);
        setTotalBytes(u.totalBytes);
        return;
      }
      setLoadFeed((f) =>
        appendDetailFeed(f, u.text, u.variant === 'warning' ? 'warning' : 'default'),
      );
    };

    async function pollQuietly() {
      if (!aliveRef.current) return;
      try {
        const next = await getExperiment(experimentId);
        if (!aliveRef.current) return;
        setDetail(next as unknown as ExperimentDetail);
        setError(null);
      } catch {
        if (!aliveRef.current) return;
        setError('Could not refresh experiment — transient network or server error.');
      }
    }

    async function hydrate() {
      setHydrating(true);
      setError(null);
      setDetail(null);
      setLoadFeed([{ id: 'h0', text: 'Fetching experiment and run rows…', variant: 'default' }]);
      setReceivedBytes(null);
      setTotalBytes(null);
      stall.start();

      if (pollRef.current !== null) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }

      try {
        const loaded = await getExperimentWithProgress(
          experimentId,
          applyProg,
          abortHydrate.signal,
        );
        stall.stop();
        if (!aliveRef.current) return;
        setDetail(loaded as unknown as ExperimentDetail);
        setLoadFeed((f) => appendDetailFeed(f, 'Hydrated UI — polling for live phase updates.', 'default'));
      } catch (err) {
        stall.stop();
        if (!aliveRef.current) return;
        if (err instanceof DOMException && err.name === 'AbortError') return;
        const msg =
          err instanceof Error ? err.message : 'Failed to load experiment';
        setError(msg);
        setLoadFeed((f) => appendDetailFeed(f, `Failed: ${msg}`, 'warning'));
      } finally {
        stall.stop();
        if (!aliveRef.current) return;
        setHydrating(false);

        pollRef.current = window.setInterval(pollQuietly, DETAIL_POLL_MS);
        void pollQuietly();
      }
    }

    void hydrate();

    return () => {
      aliveRef.current = false;
      abortHydrate.abort();
      stall.stop();
      if (pollRef.current !== null) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [experimentId]);

  async function handleCancel() {
    if (!confirm('Cancel this experiment? Runs in progress will stop after the current phase.')) {
      return;
    }
    setCancelling(true);
    try {
      await cancelExperiment(experimentId);
      const refreshed = await getExperiment(experimentId);
      setDetail(refreshed as unknown as ExperimentDetail);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel');
    } finally {
      setCancelling(false);
    }
  }

  const TERMINAL_STATUSES: ExperimentStatus[] = ['complete', 'failed', 'partial', 'cancelled'];
  const isTerminal = detail && TERMINAL_STATUSES.includes(detail.status);
  const isRunning = detail?.status === 'running';

  const backToList = (
    <button
      type="button"
      onClick={onBack}
      className="mb-6 w-full rounded-lg px-3 py-2.5 text-left text-sm font-medium text-blue-400 hover:bg-slate-700/55 hover:text-blue-300"
    >
      ← All experiments
    </button>
  );

  function experimentRailBlurb(extra: string) {
    return (
      <>
        <div className="mb-6">
          <div className="text-sm font-semibold text-slate-200">Sidebar</div>
          <div className="mt-0.5 text-[11px] uppercase tracking-wider text-slate-500">Experiment</div>
        </div>
        {backToList}
        <p className="mt-4 text-xs leading-relaxed text-slate-400">{extra}</p>
      </>
    );
  }

  if (hydrating && !detail && !error) {
    return (
      <DashboardShell
        asideWidthClass="w-56 lg:w-60"
        header={
          <AppPageChrome
            tone="darkFrame"
            pageEyebrow="Experiment"
            pageTitle="Loading"
            pageMeta={<span className="font-mono">{experimentId}</span>}
            pageHint="Fetching runs, configuration, and live progress from the API."
            showDashboardFootnote={false}
          />
        }
        sidebar={experimentRailBlurb('Hydrating payloads from Mongo + your orchestration backend.')}
      >
        <div className="flex justify-center pb-8 pt-2">
          <LoadingFeedbackPanel
            title="Loading experiment detail"
            subtitle="Pulling run status, sweep config, and payloads from your server."
            feed={loadFeed}
            receivedBytes={receivedBytes}
            totalBytes={totalBytes}
            footer={`After hydrate, polls every ${DETAIL_POLL_MS / 1000}s while this screen stays open.`}
            theme="light"
          />
        </div>
      </DashboardShell>
    );
  }

  if (!hydrating && !detail && error) {
    return (
      <DashboardShell
        asideWidthClass="w-56 lg:w-60"
        header={
          <AppPageChrome
            tone="darkFrame"
            pageEyebrow="Experiment"
            pageTitle="Could not load"
            pageMeta={<span className="font-mono">{experimentId}</span>}
            pageHint="Check server connectivity or permissions. Diagnostics below may show which step failed."
            showDashboardFootnote={false}
          />
        }
        sidebar={experimentRailBlurb('Check that the FastAPI server is up and reachable from this dashboard.')}
      >
        <div className="mx-auto max-w-lg rounded-xl border border-red-200 bg-red-50 px-6 py-4 text-red-800">
          {error}
        </div>
        {loadFeed.length > 0 && (
          <div className="mt-8 flex justify-center">
            <LoadingFeedbackPanel
              title="Diagnostics"
              subtitle="Steps before failure"
              feed={loadFeed}
              receivedBytes={receivedBytes}
              totalBytes={totalBytes}
              expectPayloadProgress={false}
              theme="light"
            />
          </div>
        )}
      </DashboardShell>
    );
  }

  if (!detail) {
    return null;
  }

  return (
    <DashboardShell
      asideWidthClass="w-56 lg:w-60"
      contentMaxWidthClass="max-w-7xl"
      header={
        <AppPageChrome
          tone="darkFrame"
          pageEyebrow="Experiment"
          pageTitle={detail.experiment_name}
          pageMeta={<span className="font-mono">{experimentId}</span>}
          pageHint={
            isRunning
              ? `Live updates every ${DETAIL_POLL_MS / 1000}s until this batch reaches a terminal status.`
              : 'Runs, sweep metadata, and stored results appear in the sections below.'
          }
          showDashboardFootnote={false}
        />
      }
      sidebar={experimentRailBlurb(
        isRunning
          ? 'Cancel stays available until every run leaves the running phases.'
          : isTerminal && onExplore
          ? 'Open Explore results when you want aggregated rankings for this sweep.'
          : 'Status, configs, failures, and the run table populate the pane on the right.',
      )}
    >

        {/* Header with status + primary actions */}
        <div className="mb-5 rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-4 gap-y-2">
              <StatusBadge status={detail.status} />
              <p className="text-xs leading-snug text-slate-500">
                Runs table lists each sweep combo and pipeline phase below.
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-3">
              {(isTerminal || isRunning) && onExplore && (
                <button
                  type="button"
                  onClick={onExplore}
                  title={
                    isRunning
                      ? 'Opens Search Explorer with data stored so far; more results appear as runs finish.'
                      : undefined
                  }
                  className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white text-sm font-semibold rounded-xl shadow-md transition-all transform hover:scale-105"
                >
                  {isRunning ? '🔍 Explore live results' : '🔍 Explore Results'}
                </button>
              )}
              {isRunning && (
                <button
                  type="button"
                  onClick={handleCancel}
                  disabled={cancelling}
                  className="px-6 py-3 bg-red-600 hover:bg-red-700 disabled:bg-red-300 text-white text-sm font-semibold rounded-xl shadow-md transition-all"
                >
                  {cancelling ? 'Cancelling...' : '⏹ Cancel Experiment'}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Key metrics cards */}
        {detail && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <StatCard
              label="Total Runs"
              value={detail.run_count ?? 0}
              icon={icons.grid}
              color="blue"
            />
            <StatCard
              label="Successful"
              value={(detail.run_count ?? 0) - (detail.failed_count ?? 0)}
              icon={icons.check}
              color="green"
            />
            <StatCard
              label="Failed"
              value={detail.failed_count ?? 0}
              icon={icons.x}
              color="amber"
            />
            <StatCard
              label="Duration"
              value={formatDuration(detail.started_at, detail.completed_at)}
              icon={icons.clock}
              color="purple"
            />
          </div>
        )}

        {/* Progress visualization for running experiments */}
        {detail && isRunning && detail.runs && detail.runs.length > 0 && (
          <div className="mb-6 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl shadow-sm border border-blue-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-800 mb-1">Experiment Progress</h3>
                <p className="text-sm text-slate-600">
                  {detail.runs.filter(r => r.phase === Phase.COMPLETE).length} of {detail.runs.length} runs completed
                </p>
              </div>
              <ProgressRing
                percent={(detail.runs.filter(r => r.phase === Phase.COMPLETE).length / detail.runs.length) * 100}
                size={100}
              />
            </div>
          </div>
        )}

        {/* Metadata sections */}
        {detail && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Git & Timeline */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
              <div className="flex items-center gap-2 mb-4">
                {icons.code}
                <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
                  Git & Timeline
                </h2>
              </div>
              <div className="space-y-3">
                <MetadataItem
                  label="Git Commit"
                  value={detail.git_commit
                    ? `${detail.git_commit.slice(0, 8)}${detail.git_dirty ? ' (dirty)' : ''}`
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
                <MetadataItem label="App Version" value={detail.app_version} />
                <MetadataItem label="Python" value={detail.python_version} />
              </div>
            </div>

            {/* Sweep Configuration */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
              <div className="flex items-center gap-2 mb-4">
                {icons.settings}
                <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
                  Configuration
                </h2>
              </div>
              <div className="space-y-3">
                <MetadataItem label="Rerank Model" value={detail.rerank_model ?? 'none'} />
                <MetadataItem label="Top-K Initial" value={detail.top_k_initial} />
                <MetadataItem label="Top-K Final" value={detail.top_k_final} />
                <MetadataItem label="Parallelism" value={detail.parallelism} />
                <MetadataItem label="On Error" value={detail.on_error} />
                <MetadataItem label="Queries" value={detail.queries_file} />
              </div>
            </div>
          </div>
        )}

        {/* Data Paths */}
        {detail?.data_paths && detail.data_paths.length > 0 && (
          <div className="mb-6 bg-white rounded-xl shadow-sm border border-slate-200 p-5">
            <div className="flex items-center gap-2 mb-3">
              {icons.database}
              <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
                Data Sources
              </h2>
            </div>
            <div className="flex flex-wrap gap-2">
              {detail.data_paths.map((p) => (
                <span key={p} className="inline-flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-slate-100 to-slate-50 border border-slate-200 text-slate-700 text-sm font-mono rounded-lg shadow-sm">
                  📄 {p.split('/').pop()}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Sweep Dimensions - Visual Grid */}
        {detail?.sweep_summary && (
          <div className="mb-6 bg-gradient-to-br from-purple-50 to-pink-50 rounded-2xl shadow-sm border border-purple-200 p-6">
            <div className="flex items-center gap-2 mb-4">
              {icons.grid}
              <h2 className="text-lg font-bold text-slate-800">
                Sweep Dimensions
              </h2>
              <span className="ml-auto text-sm text-purple-700 font-semibold">
                {detail.sweep_summary.models.length *
                  detail.sweep_summary.chunking_methods.length *
                  detail.sweep_summary.chunk_sizes.length *
                  detail.sweep_summary.overlaps.length *
                  detail.sweep_summary.retrieval_methods.length} combinations
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <DimensionBadge label="Database Provider" values={[detail.sweep_summary.database_provider || 'mongodb']} />
              <DimensionBadge label="Embedding Provider" values={[detail.sweep_summary.embedding_provider || 'local']} />
              <DimensionBadge label="Embedding Models" values={detail.sweep_summary.models} />
              <DimensionBadge label="Chunking" values={detail.sweep_summary.chunking_methods} />
              <DimensionBadge label="Chunk Sizes" values={detail.sweep_summary.chunk_sizes} />
              <DimensionBadge label="Overlaps" values={detail.sweep_summary.overlaps} />
              <DimensionBadge label="Retrieval" values={detail.sweep_summary.retrieval_methods} />
              <DimensionBadge label="Rerank Provider" values={[detail.sweep_summary.rerank_provider || 'local']} />
            </div>
          </div>
        )}

        {/* Environment */}
        {detail?.env_params && (
          <div className="mb-6 bg-white rounded-xl shadow-sm border border-slate-200 p-5">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
              Environment
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetadataItem label="Server URL" value={detail.env_params.server_url} />
              {/* Only show Voyage rate limits if using Voyage provider */}
              {(detail.config?.embedding?.provider === 'voyage' ||
                detail.config?.retrieval?.rerank_provider === 'voyage') && (
                <>
                  <MetadataItem label="Voyage RPM" value={detail.env_params.voyage_rpm_limit} />
                  <MetadataItem label="Voyage TPM" value={detail.env_params.voyage_tpm_limit} />
                </>
              )}
              <MetadataItem label="Recover on Boot" value={String(detail.env_params.recover_on_boot)} />
            </div>
          </div>
        )}

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Runs Table - Enhanced */}
        {detail?.runs && detail.runs.length > 0 && (() => {
          const startIndex = (runsCurrentPage - 1) * runsItemsPerPage;
          const endIndex = startIndex + runsItemsPerPage;
          const paginatedRuns = detail.runs.slice(startIndex, endIndex);

          return (
            <div className="bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden">
              <div className="bg-gradient-to-r from-slate-50 to-slate-100 px-6 py-4 border-b border-slate-200">
                <h2 className="text-lg font-bold text-slate-800">
                  Run Details ({detail.runs.length})
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b-2 border-slate-200">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Run ID</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Database</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Embed Prov</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Embedding Model</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Chunker</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Size/Overlap</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Retrieval</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Rerank Prov</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Phase</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Elapsed</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {paginatedRuns.map((run, idx) => {
                      const isComplete = run.phase === Phase.COMPLETE;
                      const isFailed = run.phase === Phase.FAILED;
                      const rowBg = isFailed ? 'bg-red-50/50' : isComplete ? 'bg-green-50/30' : '';
                      const absoluteIndex = startIndex + idx;

                      return (
                        <tr key={run.run_id} className={`hover:bg-blue-50/40 transition-all duration-200 ${rowBg}`}>
                          <td className="px-4 py-4">
                            <div className="flex items-center gap-2">
                              <span className="w-6 h-6 rounded-full bg-slate-200 text-slate-600 text-xs font-bold flex items-center justify-center">
                                {absoluteIndex + 1}
                              </span>
                              <span className="text-sm font-mono text-slate-600">
                                {run.run_id.slice(0, 8)}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-4">
                            <span className="inline-flex items-center px-2.5 py-1 rounded-md bg-indigo-100 text-indigo-800 text-xs font-bold uppercase">
                              {run.database_provider || 'mongodb'}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <span className="inline-flex items-center px-2.5 py-1 rounded-md bg-teal-100 text-teal-800 text-xs font-medium uppercase">
                              {run.embedding_provider || 'local'}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <span className="inline-flex items-center px-2.5 py-1 rounded-md bg-blue-100 text-blue-800 text-xs font-medium">
                              {run.embedding_model}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <span className="inline-flex items-center px-2.5 py-1 rounded-md bg-purple-100 text-purple-800 text-xs font-medium">
                              {run.chunking_method}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <span className="text-sm font-mono text-slate-700 font-semibold">
                              {run.chunk_size} / {run.overlap}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <span className="inline-flex items-center px-2.5 py-1 rounded-md bg-amber-100 text-amber-800 text-xs font-medium">
                              {run.retrieval_method}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <span className="inline-flex items-center px-2.5 py-1 rounded-md bg-teal-100 text-teal-800 text-xs font-medium uppercase">
                              {run.rerank_provider || 'local'}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <PhaseIndicator current={run.phase} />
                          </td>
                          <td className="px-4 py-4">
                            <div className="flex items-center gap-1 text-sm text-slate-500">
                              {icons.clock}
                              <span className="font-medium">
                                {run.elapsed_ms > 0 ? `${(run.elapsed_ms / 1000).toFixed(1)}s` : '—'}
                              </span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <Pagination
                currentPage={runsCurrentPage}
                totalItems={detail.runs.length}
                itemsPerPage={runsItemsPerPage}
                onPageChange={setRunsCurrentPage}
                onItemsPerPageChange={handleRunsItemsPerPageChange}
              />
            </div>
          );
        })()}

        {/* Failed runs detail */}
        {detail?.runs && detail.runs.filter(r => r.phase === Phase.FAILED).length > 0 && (
          <div className="mt-6 bg-gradient-to-br from-red-50 to-orange-50 border-2 border-red-200 rounded-2xl p-6 shadow-lg">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-500 flex items-center justify-center text-white">
                {icons.x}
              </div>
              <h2 className="text-lg font-bold text-red-900">
                Failed Runs ({detail.runs.filter(r => r.phase === Phase.FAILED).length})
              </h2>
            </div>
            <div className="space-y-3">
              {detail.runs.filter(r => r.phase === Phase.FAILED).map(run => (
                <div key={run.run_id} className="bg-white border-l-4 border-red-400 rounded-lg p-4 shadow-sm">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-mono font-bold rounded">
                      {run.run_id.slice(0, 8)}
                    </span>
                    <span className="text-sm text-slate-700 font-medium">
                      {run.embedding_model} · {run.chunking_method} · {run.chunk_size}+{run.overlap}
                    </span>
                    {run.elapsed_ms > 0 && (
                      <span className="ml-auto text-xs text-slate-500 flex items-center gap-1">
                        {icons.clock}
                        {(run.elapsed_ms / 1000).toFixed(1)}s
                      </span>
                    )}
                  </div>
                  <div className="bg-red-50 rounded-md p-3 border border-red-100">
                    <p className="text-sm text-red-900 font-mono whitespace-pre-wrap">
                      {run.error_message || 'No error message recorded'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Success summary with explore CTA */}
        {isTerminal && detail?.runs && detail.runs.filter(r => r.phase === Phase.FAILED).length === 0 && (
          <div className="mt-6 bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-300 rounded-2xl p-6 shadow-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-green-500 flex items-center justify-center text-white">
                  {icons.check}
                </div>
                <div>
                  <h3 className="text-lg font-bold text-green-900">
                    All Runs Completed Successfully!
                  </h3>
                  <p className="text-sm text-green-700 mt-1">
                    {detail.runs.length} run(s) finished without errors
                  </p>
                </div>
              </div>
              {onExplore && (
                <button
                  onClick={onExplore}
                  className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white text-sm font-semibold rounded-xl shadow-md transition-all transform hover:scale-105 flex items-center gap-2"
                >
                  🔍 Explore Results
                </button>
              )}
            </div>
          </div>
        )}

        {!isTerminal && (
          <div className="mt-4 text-center text-xs text-slate-500">
            Polling every {DETAIL_POLL_MS / 1000}s <span className="animate-pulse">●</span>
          </div>
        )}
    </DashboardShell>
  );
}
