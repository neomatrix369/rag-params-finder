/**
 * ExperimentDetailScreen
 *
 * Displays comprehensive experiment information with visual hierarchy:
 * - Status badges, metric cards, and progress indicators
 * - Themed metadata sections (Git, Config, Data, Sweep Dimensions)
 * - Enhanced runs table with color-coded badges
 * - Success/failure panels with large visual feedback
 */
import { DETAIL_POLL_MS } from '../../constants';
import AppPageChrome from '../chrome/AppPageChrome';
import DashboardShell from '../chrome/DashboardShell';
import LoadingFeedbackPanel from '../chrome/LoadingFeedbackPanel';
import ExperimentProgressCard from '../experiment/ExperimentProgressCard';
import ExperimentVectorDbStatsCard from '../stats/ExperimentVectorDbStatsCard';
import ExperimentControlButtons from '../experiment/ExperimentControlButtons';
import ConfirmDeleteModal from '../experiment/ConfirmDeleteModal';
import CollapsibleCard from '../chrome/CollapsibleCard';
import Pagination from '../chrome/Pagination';
import {
  detailIcons as icons,
  DimensionBadge,
  MetadataItem,
  PhaseIndicator,
  ProgressSubtitle,
  StatCard,
  StatusBadge,
} from '../experiment/experimentDetail';
import { formatDurationFromRuns } from '../experiment/experimentDetailProgress';
import { useExperimentDetail } from '../../hooks/useExperimentDetail';
import { Phase, Experiment } from '../../types';
import type { ExperimentDbStatsSummary } from '../../types';
import {
  displayDatabaseProvider,
  experimentHydratingBlurb,
} from '../../utils/storageLabels';
import {
  displayRetrievers,
  isPausedExperimentStatus,
  isRunningExperimentStatus,
  isTerminalExperimentStatus,
  summarizeExperimentRuns,
} from '../../utils/experimentStatus';
import { completionReasonLabel } from '../../utils/completionReason';

export default function ExperimentDetailScreen({
  experimentId,
  initialExperiment,
  initialDbStats,
  onBack,
  onExplore,
}: {
  experimentId: string;
  initialExperiment?: Experiment;
  initialDbStats?: ExperimentDbStatsSummary;
  onBack: () => void;
  onExplore?: () => void;
}) {
  const {
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
  } = useExperimentDetail({
    experimentId,
    initialExperiment,
    initialDbStats,
    onDeleted: onBack,
  });

  const isTerminal = detail && isTerminalExperimentStatus(detail.status, detail.completed_at);
  const isRunning = isRunningExperimentStatus(detail?.status, detail?.completed_at);
  const isPaused = isPausedExperimentStatus(detail?.status, detail?.completed_at);
  const canExplore = Boolean(onExplore && (isTerminal || isRunning || isPaused));
  const canDelete = isTerminal || isPaused;

  const backToList = (
    <button
      type="button"
      onClick={onBack}
      className="mb-6 inline-flex min-h-11 w-full items-center gap-2 rounded-lg px-3 text-left text-sm font-semibold text-emerald-300 hover:bg-white/10 hover:text-white"
    >
      {icons.back} All experiments
    </button>
  );

  const compactBackToList = (
    <button
      type="button"
      onClick={onBack}
      className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-white/20 px-3 text-sm font-semibold text-white hover:border-emerald-300 hover:bg-white/10 lg:hidden"
    >
      {icons.back} Back
    </button>
  );

  function experimentRailBlurb(extra: string) {
    return (
      <>
        <div className="mb-6">
          <div className="font-display text-lg font-semibold text-white">From sweep to results</div>
          <div className="mt-1 text-xs font-bold uppercase tracking-widest text-emerald-300">Experiment detail</div>
        </div>
        {backToList}
        <ol className="space-y-4 border-l border-white/15 pl-4 text-xs text-slate-300">
          <li><span className="block font-mono text-xs text-emerald-300">01 · IDENTITY</span>Confirm the sweep and lifecycle state.</li>
          <li><span className="block font-mono text-xs text-emerald-300">02 · CONFIG</span>Trace the parameter space that produced each run.</li>
          <li><span className="block font-mono text-xs text-emerald-300">03 · RESULTS</span>Inspect completed runs and stored results.</li>
        </ol>
        <p className="mt-6 rounded-xl border border-white/10 bg-white/5 p-3 text-xs leading-relaxed text-slate-300">{extra}</p>
      </>
    );
  }

  if (hydrating && !detail && !error) {
    return (
      <DashboardShell
        asideWidthClass="w-full lg:w-60"
        hideSidebarOnCompact
        header={
          <AppPageChrome
            tone="darkFrame"
            pageEyebrow="Experiment"
            pageTitle="Loading"
            pageMeta={<span className="font-mono">{experimentId}</span>}
            pageHint="Fetching runs, configuration, and live progress from the API."
            topRight={compactBackToList}
            showDashboardFootnote={false}
          />
        }
        sidebar={experimentRailBlurb(experimentHydratingBlurb())}
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
        asideWidthClass="w-full lg:w-60"
        hideSidebarOnCompact
        header={
          <AppPageChrome
            tone="darkFrame"
            pageEyebrow="Experiment"
            pageTitle="Could not load"
            pageMeta={<span className="font-mono">{experimentId}</span>}
            pageHint="Check server connectivity or permissions. Diagnostics below may show which step failed."
            topRight={compactBackToList}
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

  const runSummary = summarizeExperimentRuns(detail.runs, detail.run_count);
  const isBayesianStrategy = detail.config?.execution?.search_strategy === 'bayesian';
  const bayesianSummary = detail.bayesian_summary;
  const bayesianPlannedTrials = isBayesianStrategy && typeof bayesianSummary?.planned_trials === 'number'
    ? bayesianSummary.planned_trials
    : runSummary.expected;
  const bayesianAttemptedTrials = isBayesianStrategy
    ? Math.max(
        0,
        bayesianSummary?.attempted_trials
          ?? (runSummary.complete + runSummary.failed + runSummary.interrupted + runSummary.inProgress),
      )
    : 0;
  const bayesianDiscardedCount = isBayesianStrategy
    ? Math.max(0, bayesianSummary?.discarded_trials ?? 0)
    : 0;
  const bayesianNotStartedCount = isBayesianStrategy
    ? Math.max(0, bayesianPlannedTrials - bayesianAttemptedTrials - bayesianDiscardedCount)
    : runSummary.neverStarted;
  const isBayesianIncomplete = isBayesianStrategy
    && bayesianAttemptedTrials < bayesianPlannedTrials;
  const hasShortfallCompletionReason = detail.completion_reason
    ? ['completed_with_sampling_shortfall', 'completed_with_shortfall'].includes(detail.completion_reason)
    : false;
  const bayesianCompletedCount = isBayesianStrategy
    ? hasShortfallCompletionReason
      ? bayesianAttemptedTrials
      : Math.max(0, bayesianAttemptedTrials - runSummary.failed - runSummary.interrupted - runSummary.inProgress)
    : runSummary.complete;
  const isCompleteWithBayesianShortfall = detail.status === 'complete' && isBayesianIncomplete;
  const sweepSummary = (() => {
    if (detail.status === 'running') {
      return `${runSummary.complete} of ${runSummary.expected} runs are complete; stored results can grow as the sweep continues.`;
    }
    if (detail.status === 'paused') {
      return `Paused after ${runSummary.complete} of ${runSummary.expected} runs completed; resume to run the remaining parameter combinations.`;
    }
    if (detail.status === 'complete') {
      const reasonSuffix = detail.completion_reason && detail.completion_reason !== 'all_planned_trials_completed'
        ? ` (${completionReasonLabel(detail.completion_reason)})`
        : '';
      if (isBayesianIncomplete) {
        return `Planned ${bayesianPlannedTrials} Bayesian combinations. `
          + `${bayesianAttemptedTrials} attempted: ${bayesianCompletedCount} complete, ${runSummary.interrupted} interrupted, `
          + `${bayesianDiscardedCount} discarded by sampler, ${bayesianNotStartedCount} not started${reasonSuffix}.`;
      }
      return `All ${runSummary.expected} configured runs completed${reasonSuffix}; stored results are ready to inspect.`;
    }
    const partialReasonSuffix = detail.completion_reason
      ? ` (${completionReasonLabel(detail.completion_reason)})`
      : '';
    if (detail.status === 'partial') {
      if (isBayesianStrategy) {
        return `Planned ${bayesianPlannedTrials} Bayesian combinations. `
          + `${bayesianAttemptedTrials} attempted: ${runSummary.complete} complete, ${runSummary.failed} failed, `
          + `${runSummary.interrupted} interrupted, ${bayesianDiscardedCount} discarded by sampler, ${bayesianNotStartedCount} not started${partialReasonSuffix}.`;
      }
      return `${runSummary.complete} of ${runSummary.expected} runs completed${partialReasonSuffix}; treat rankings from completed runs as preliminary results.`;
    }
    if (detail.status === 'cancelled') {
      return `Collection stopped after ${runSummary.complete} of ${runSummary.expected} runs completed.`;
    }
    return `${runSummary.failed} failed and ${runSummary.complete} completed of ${runSummary.expected} configured runs.`;
  })();
  const nextStepLabel = runSummary.complete > 0
    ? 'Inspect stored results'
    : isRunning
      ? 'Await first completed run'
      : 'No completed results';
  const metricsGridClass = runSummary.inProgress > 0
    ? 'grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-2.5 p-4'
    : 'grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 p-4';

  return (
    <DashboardShell
      asideWidthClass="w-full lg:w-60"
      contentMaxWidthClass="max-w-7xl"
      hideSidebarOnCompact
      header={
        <AppPageChrome
          tone="darkFrame"
          pageEyebrow="Experiment results"
          pageTitle={detail.experiment_name}
          pageMeta={<span className="font-mono">{experimentId}</span>}
          pageHint={
            isRunning
              ? `Live updates every ${DETAIL_POLL_MS / 1000}s. Follow completed runs into stored results while the sweep continues.`
              : isPaused
                ? 'The sweep is paused. Review completed-run results now or resume the remaining parameter combinations.'
                : 'Connect this experiment’s identity and configuration to its run outcomes and stored results.'
          }
          topRight={
            <>
              {compactBackToList}
              <ExperimentControlButtons
                experimentId={experimentId}
                status={detail.status}
                tone="dark"
                onStatusChange={refreshDetailAfterControl}
                onError={(message) => setError(message)}
              />
            </>
          }
          showDashboardFootnote={false}
        />
      }
      sidebar={experimentRailBlurb(
        isRunning
          ? 'Pause or cancel from the header while runs are in flight.'
          : isPaused
            ? 'Resume from the header to continue the sweep.'
          : isTerminal && onExplore
          ? 'Open Explore results when you want aggregated rankings for this sweep.'
          : 'Status, configs, failures, and the run table populate the pane on the right.',
      )}
    >

        {/* Overview: identity, result fidelity, actions, and run-outcome metrics. */}
        <section className="mb-6 overflow-hidden rounded-panel border border-line bg-paper shadow-panel" aria-labelledby="sweep-overview-title">
          <div className="flex flex-col gap-4 border-b border-line p-5 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <p className="text-xs font-bold uppercase tracking-widest text-accent-strong">Identity → configuration → results</p>
              <h2 id="sweep-overview-title" className="mt-1 font-display text-2xl font-semibold text-ink">Sweep overview</h2>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <StatusBadge status={detail.status} />
                <p className="max-w-3xl text-sm leading-relaxed text-muted">{sweepSummary}</p>
              </div>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              {canExplore && (
                <button
                  type="button"
                  onClick={onExplore}
                  title={
                    isRunning
                      ? 'Opens Search Explorer with data stored so far; more results appear as runs finish.'
                      : isPaused
                        ? 'Explore results from completed runs; resume to continue the sweep.'
                        : undefined
                  }
                  className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-accent-strong"
                >
                  {icons.search} {isRunning ? 'Explore live results' : 'Explore results'}
                </button>
              )}
              {canDelete && (
                <button
                  type="button"
                  onClick={() => setShowDeleteModal(true)}
                  className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-line bg-paper px-4 text-sm font-semibold text-ink shadow-sm transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-700"
                >
                  {icons.trash} Delete
                </button>
              )}
            </div>
          </div>

          <div className="grid gap-3 border-b border-line bg-canvas p-4 sm:grid-cols-3">
            <div className="rounded-xl border border-line bg-paper p-3">
              <p className="text-xs font-bold uppercase tracking-wider text-muted">Lifecycle</p>
              <p className="mt-1 text-sm font-semibold capitalize text-ink">{detail.status}</p>
            </div>
            <div className="rounded-xl border border-line bg-paper p-3">
              <p className="text-xs font-bold uppercase tracking-wider text-muted">Run set</p>
              <p className="mt-1 text-sm font-semibold text-ink">
                {isBayesianStrategy
                  ? `${bayesianAttemptedTrials} attempted · ${bayesianPlannedTrials} planned`
                  : `${runSummary.complete} complete · ${runSummary.expected} configured`}
              </p>
            </div>
            <div className="rounded-xl border border-line bg-paper p-3">
              <p className="text-xs font-bold uppercase tracking-wider text-muted">Next step</p>
              <p className="mt-1 text-sm font-semibold text-accent-strong">{nextStepLabel}</p>
            </div>
          </div>

          <div className={metricsGridClass}>
            <StatCard compact label="Total" value={runSummary.expected} icon={icons.grid} color="blue" />
            <StatCard compact label="Successful" value={runSummary.complete} icon={icons.check} color="green" />
            <StatCard compact label="Failed" value={runSummary.failed} icon={icons.x} color="red" />
            <StatCard compact label="Interrupted" value={runSummary.interrupted} icon={icons.x} color="amber" />
            <StatCard
              compact
              label={isBayesianStrategy ? 'Not Started' : 'Not Started'}
              value={isBayesianStrategy ? bayesianNotStartedCount : runSummary.neverStarted}
              icon={icons.grid}
              color="slate"
            />
            {isBayesianStrategy && (
              <StatCard
                compact
                label="Discarded by Sampler"
                value={bayesianDiscardedCount}
                icon={icons.x}
                color="slate"
              />
            )}
            {runSummary.inProgress > 0 && (
              <StatCard compact label="In Progress" value={runSummary.inProgress} icon={icons.play} color="purple" />
            )}
            <StatCard
              compact
              label="Duration"
              value={
                isRunning || isPaused
                  ? '—'
                  : formatDurationFromRuns(detail.runs ?? [], detail.started_at, detail.completed_at)
              }
              icon={icons.clock}
              color="purple"
            />
          </div>
        </section>

        {/* Progress visualization for running experiments */}
        {detail && isRunning && detail.runs && detail.runs.length > 0 && (
          <div className="mb-6">
            <ExperimentProgressCard
              title="Experiment Progress"
              subtitle={
                <ProgressSubtitle
                  completed={runSummary.complete}
                  total={runSummary.expected}
                  startedAt={detail.started_at}
                />
              }
              percent={runSummary.expected > 0 ? (runSummary.complete / runSummary.expected) * 100 : 0}
              variant="default"
            />
          </div>
        )}

        {/* Metadata sections */}
        {detail && (
          <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="rounded-panel border border-line bg-paper p-5 shadow-panel">
              <CollapsibleCard
                title="Git & Timeline"
                icon={icons.code}
                compact
                storageKey={`detail-git-${experimentId}`}
                headerExtra={
                  detail.git_commit ? (
                    <span className="font-mono text-xs text-muted">
                      {detail.git_commit.slice(0, 8)}
                      {detail.git_dirty ? ' *' : ''}
                    </span>
                  ) : null
                }
              >
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
                  <MetadataItem
                    label="Completion Reason"
                    value={detail.completion_reason ? completionReasonLabel(detail.completion_reason) : undefined}
                  />
                  <MetadataItem label="App Version" value={detail.app_version} />
                  <MetadataItem label="Python" value={detail.python_version} />
                </div>
              </CollapsibleCard>
            </div>

            <div className="rounded-panel border border-line bg-paper p-5 shadow-panel">
              <CollapsibleCard
                title="Configuration"
                icon={icons.settings}
                compact
                storageKey={`detail-config-${experimentId}`}
                headerExtra={
                  detail.retrieval_model ? (
                    <span className="max-w-36 truncate text-xs text-muted" title={detail.retrieval_model}>
                      {detail.retrieval_model}
                    </span>
                  ) : (
                    <span className="text-xs text-muted">no rerank</span>
                  )
                }
              >
                <div className="space-y-3">
                  <MetadataItem
                    label="Search Strategy"
                    value={detail.config?.execution?.search_strategy ?? 'grid'}
                  />
                  <MetadataItem label="Rerank Model" value={detail.retrieval_model ?? 'none'} />
                  <MetadataItem label="Top-K Initial" value={detail.top_k_initial} />
                  <MetadataItem label="Top-K Final" value={detail.top_k_final} />
                  <MetadataItem label="Parallelism" value={detail.parallelism} />
                  {detail.config?.execution?.search_strategy === 'bayesian' ? (
                    <>
                      <MetadataItem
                        label="Planned Bayesian Trials"
                        value={detail.run_count}
                      />
                      <MetadataItem
                        label="Grid-Equivalent Count"
                        value={detail.grid_equivalent_count}
                      />
                    </>
                  ) : null}
                  <MetadataItem label="On Error" value={detail.on_error} />
                  <MetadataItem label="Queries" value={detail.queries_file} />
                </div>
              </CollapsibleCard>
            </div>
          </div>
        )}

        {/* Data Paths */}
        {detail?.data_paths && detail.data_paths.length > 0 && (
          <div className="mb-6 rounded-panel border border-line bg-paper p-5 shadow-panel">
            <div className="mb-3 flex items-center gap-2 text-accent-strong">
              {icons.database}
              <h2 className="text-sm font-bold uppercase tracking-wider text-ink">
                Data Sources
              </h2>
            </div>
            <div className="flex flex-wrap gap-2">
              {detail.data_paths.map((p) => (
                <span key={p} className="inline-flex min-h-11 max-w-full items-center gap-2 break-all rounded-lg border border-line bg-canvas px-3 font-mono text-sm text-ink">
                  {icons.document} {p.split('/').pop()}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Sweep Dimensions - Visual Grid */}
        {detail?.sweep_summary && (
          <div className="mb-6 rounded-panel border border-line bg-paper p-5 shadow-panel">
            <CollapsibleCard
              title="Sweep Dimensions"
              icon={icons.grid}
              storageKey={`detail-sweep-${experimentId}`}
              headerExtra={
                <span className="text-sm font-semibold text-accent-strong">
                  {detail.sweep_summary.models.length *
                    detail.sweep_summary.chunking_methods.length *
                    detail.sweep_summary.chunk_sizes.length *
                    detail.sweep_summary.overlaps.length *
                    (detail.sweep_summary.paddings?.length ?? 1)}{' '}
                  combinations
                </span>
              }
            >
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <DimensionBadge label="Database Provider" values={[displayDatabaseProvider(detail.sweep_summary.database_provider)]} />
                <DimensionBadge label="Embedding Provider" values={[detail.sweep_summary.embedding_provider || 'local']} />
                <DimensionBadge label="Embedding Models" values={detail.sweep_summary.models} />
                <DimensionBadge label="Chunking" values={detail.sweep_summary.chunking_methods} />
                <DimensionBadge label="Chunk Sizes" values={detail.sweep_summary.chunk_sizes} />
                <DimensionBadge label="Overlaps" values={detail.sweep_summary.overlaps} />
                {detail.config?.execution?.search_strategy === 'bayesian' && (
                  <DimensionBadge
                    label="Bayesian Strategy"
                    values={['chunk_size × overlap']}
                  />
                )}
                {detail.sweep_summary.paddings && detail.sweep_summary.paddings.length > 0 && (
                  <DimensionBadge label="Paddings" values={detail.sweep_summary.paddings} />
                )}

                {/* Unified Retrievers display with backward compatibility */}
                {detail.sweep_summary.retrievers ? (
                  <DimensionBadge label="Retrievers" values={detail.sweep_summary.retrievers} />
                ) : (
                  <>
                    <DimensionBadge label="Retrieval" values={detail.sweep_summary.retrieval_methods || ['dense']} />
                    {detail.sweep_summary.retrieval_provider && (
                      <DimensionBadge label="Retrieval Provider" values={[detail.sweep_summary.retrieval_provider]} />
                    )}
                  </>
                )}
              </div>
            </CollapsibleCard>

            {detail.config?.execution?.search_strategy === 'bayesian' && detail.bayesian_summary && (
              <CollapsibleCard
                title="Bayesian Summary"
                icon={icons.grid}
                storageKey={`detail-bayesian-summary-${experimentId}`}
                headerExtra={
                  <span className="text-sm font-semibold text-accent-strong">
                    {detail.run_count}/{detail.grid_equivalent_count ?? '—'} trials
                  </span>
                }
                className="mt-3"
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <MetadataItem label="Best Query Avg Score" value={detail.bayesian_summary.best_query_avg_score} />
                  <MetadataItem label="Best Chunk Size" value={detail.bayesian_summary.best_chunk_size} />
                  <MetadataItem label="Best Overlap" value={detail.bayesian_summary.best_overlap} />
                  <MetadataItem
                    label="Best Embedding"
                    value={detail.bayesian_summary.best_embedding_model}
                  />
                  <MetadataItem label="Attempts" value={detail.bayesian_summary.attempted_trials} />
                  <MetadataItem label="Discarded by Sampler" value={detail.bayesian_summary.discarded_trials} />
                  <MetadataItem
                    label="Sampler Notes"
                    value={detail.bayesian_summary.termination_reason || 'none'}
                  />
                </div>
              </CollapsibleCard>
            )}
          </div>
        )}

        {/* Environment */}
        {detail?.env_params && (
          <div className="mb-6 rounded-panel border border-line bg-paper p-5 shadow-panel">
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-muted">
              Environment
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetadataItem label="Server URL" value={detail.env_params.server_url} />
              {/* Only show Voyage rate limits if using Voyage provider */}
              {(detail.config?.embedding?.provider === 'voyage' ||
                detail.config?.retrieval?.retrieval_provider === 'voyage') && (
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
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700" role="alert">
            {error}
          </div>
        )}

        {/* Runs Table - Enhanced */}
        {detail?.runs && detail.runs.length > 0 && (() => {
          const startIndex = (runsCurrentPage - 1) * runsItemsPerPage;
          const endIndex = startIndex + runsItemsPerPage;
          const paginatedRuns = detail.runs.slice(startIndex, endIndex);

          return (
            <section className="overflow-hidden rounded-panel border border-line bg-paper shadow-panel" aria-labelledby="run-details-title">
              <div className="border-b border-line bg-canvas px-6 py-4">
                <p className="text-xs font-bold uppercase tracking-widest text-accent-strong">Run results</p>
                <h2 id="run-details-title" className="font-display text-xl font-semibold text-ink">
                  Run details ({detail.runs.length})
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b-2 border-line bg-canvas">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Run ID</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Database</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Embed Prov</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Embedding Model</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Chunker</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Size/Overlap/Pad</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Retrievers</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Phase</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Elapsed</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {paginatedRuns.map((run, idx) => {
                      const isComplete = run.phase === Phase.COMPLETE;
                      const isFailed = run.phase === Phase.FAILED || run.phase === Phase.INTERRUPTED;
                      const rowBg = isFailed ? 'bg-red-50/50' : isComplete ? 'bg-green-50/30' : '';
                      const absoluteIndex = startIndex + idx;

                      return (
                        <tr key={run.run_id} className={`hover:bg-blue-50/40 transition-all duration-200 ${rowBg}`}>
                          <td className="px-4 py-4">
                            <div className="flex items-center gap-2">
                              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-canvas text-xs font-bold text-muted">
                                {absoluteIndex + 1}
                              </span>
                              <span className="font-mono text-sm text-muted">
                                {run.run_id.slice(0, 8)}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-4">
                            <span className="inline-flex items-center rounded-md border border-line bg-canvas px-2.5 py-1 text-xs font-bold uppercase text-ink">
                              {displayDatabaseProvider(run.database_provider)}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <span className="inline-flex items-center rounded-md border border-line bg-canvas px-2.5 py-1 text-xs font-medium uppercase text-ink">
                              {run.embedding_provider || 'local'}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <span className="inline-flex items-center rounded-md border border-line bg-paper px-2.5 py-1 text-xs font-medium text-cobalt">
                              {run.embedding_model}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <span className="inline-flex items-center rounded-md border border-line bg-paper px-2.5 py-1 text-xs font-medium text-accent-strong">
                              {run.chunking_method}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <span className="text-sm font-mono text-slate-700 font-semibold">
                              {run.chunk_size}/{run.overlap}/{run.padding ?? 0}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <div className="flex flex-wrap gap-1">
                              {displayRetrievers(run).map((retriever, idx) => (
                                <span
                                  key={idx}
                                  className="inline-flex items-center rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-900"
                                  title={retriever}
                                >
                                  {retriever}
                                </span>
                              ))}
                            </div>
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
                selectId="runs-per-page"
              />
            </section>
          );
        })()}

        {/* Interrupted runs detail */}
        {detail?.runs && runSummary.interrupted > 0 && (
          <div className="mt-6 rounded-panel border border-amber-200 bg-amber-50 p-5 shadow-panel sm:p-6">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-500 text-white">
                {icons.x}
              </div>
              <h2 className="text-lg font-bold text-amber-900">
                Interrupted Runs ({runSummary.interrupted})
              </h2>
            </div>
            <div className="space-y-3">
              {detail.runs.filter((run) => run.phase === Phase.INTERRUPTED).map((run) => (
                <div key={run.run_id} className="rounded-lg border border-l-4 border-amber-200 border-l-amber-400 bg-paper p-4 shadow-sm">
                  <div className="mb-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
                    <span className="px-2 py-1 bg-amber-100 text-amber-800 text-xs font-mono font-bold rounded">
                      {run.run_id.slice(0, 8)}
                    </span>
                    <span className="break-words text-sm font-medium text-ink">
                      {run.embedding_model} · {run.chunking_method} · {run.chunk_size}/{run.overlap}/{run.padding ?? 0}
                    </span>
                  </div>
                  <div className="bg-amber-50 rounded-md p-3 border border-amber-100">
                    <p className="text-sm text-amber-900 font-mono whitespace-pre-wrap">
                      {run.error_message || 'Run was interrupted before completion'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Failed runs detail */}
        {detail?.runs && detail.runs.filter(r => r.phase === Phase.FAILED).length > 0 && (
          <div className="mt-6 rounded-panel border border-red-200 bg-red-50 p-5 shadow-panel sm:p-6">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500 text-white">
                {icons.x}
              </div>
              <h2 className="text-lg font-bold text-red-900">
                Failed Runs ({detail.runs.filter(r => r.phase === Phase.FAILED).length})
              </h2>
            </div>
            <div className="space-y-3">
              {detail.runs.filter(r => r.phase === Phase.FAILED).map(run => (
                <div key={run.run_id} className="rounded-lg border border-l-4 border-red-200 border-l-red-400 bg-paper p-4 shadow-sm">
                  <div className="mb-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
                    <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-mono font-bold rounded">
                      {run.run_id.slice(0, 8)}
                    </span>
                    <span className="break-words text-sm font-medium text-ink">
                      {run.embedding_model} · {run.chunking_method} · {run.chunk_size}/{run.overlap}/{run.padding ?? 0}
                    </span>
                    {run.elapsed_ms > 0 && (
                      <span className="flex items-center gap-1 text-xs text-muted sm:ml-auto">
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

        {/* Terminal outcome summary */}
        {isTerminal && detail.status === 'complete' && (
        <div
          className={isCompleteWithBayesianShortfall
            ? 'mt-6 rounded-panel border border-amber-300 bg-amber-50 p-5 shadow-panel sm:p-6'
            : 'mt-6 rounded-panel border border-emerald-300 bg-emerald-50 p-5 shadow-panel sm:p-6'}
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-white">
                {icons.check}
              </div>
                <div>
                  <h3 className="text-lg font-bold text-green-900">
                    {isCompleteWithBayesianShortfall
                      ? 'Bayesian Sampling Completed with Partial Coverage'
                      : 'All Runs Completed Successfully!'}
                  </h3>
                <p className="text-sm text-green-700 mt-1">
                    {isCompleteWithBayesianShortfall
                      ? `Attempted ${bayesianAttemptedTrials} of ${bayesianPlannedTrials} combinations; ${bayesianCompletedCount} completed successfully with no failures${detail.completion_reason && detail.completion_reason !== 'all_planned_trials_completed' ? ` (${completionReasonLabel(detail.completion_reason)})` : ''}.`
                      : `${runSummary.complete} of ${runSummary.expected} run(s) finished without errors`}
                  </p>
                </div>
              </div>
              {onExplore && (
                <button
                  type="button"
                  onClick={onExplore}
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-accent px-5 text-sm font-semibold text-white shadow-sm hover:bg-accent-strong"
                >
                  {icons.search} Explore results
                </button>
              )}
            </div>
          </div>
        )}

        {isTerminal && detail.status === 'partial' && (
          <div className="mt-6 rounded-panel border border-amber-300 bg-amber-50 p-5 shadow-panel sm:p-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-amber-500 flex items-center justify-center text-white">
                  {icons.x}
                </div>
                <div>
                  <h3 className="text-lg font-bold text-amber-900">Sweep Incomplete</h3>
                  <p className="text-sm text-amber-800 mt-1">
                    {isBayesianStrategy
                      ? `Bayesian partial: ${bayesianAttemptedTrials} of ${bayesianPlannedTrials} attempted and started, `
                        + `${runSummary.complete} completed successfully, ${bayesianDiscardedCount} discarded by sampler, ${bayesianNotStartedCount} not started.`
                      : `${runSummary.complete} of ${runSummary.expected} run(s) completed successfully.`}
                    {runSummary.interrupted > 0 && ` ${runSummary.interrupted} interrupted.`}
                    {runSummary.failed > 0 && ` ${runSummary.failed} failed.`}
                    {runSummary.neverStarted > 0 && ` ${runSummary.neverStarted} not started.`}
                    {isBayesianStrategy && bayesianDiscardedCount > 0 && (
                      <span>
                        {' '}
                        {detail.bayesian_summary?.termination_reason === 'sampler_candidate_exhaustion'
                          ? `${bayesianDiscardedCount} were discarded by Bayesian sampler pruning.`
                          : `${bayesianDiscardedCount} discarded while exploring candidate trials.`}
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-amber-700 mt-2">
                    {isBayesianStrategy
                      ? `Bayesian sweep configured ${bayesianPlannedTrials} candidate combinations: ${bayesianAttemptedTrials} attempted, ${bayesianDiscardedCount} discarded by sampler, ${bayesianNotStartedCount} not started.`
                      : 'The experiment stopped before every parameter combination ran — often after a server restart or cancellation mid-sweep.'}
                  </p>
                </div>
              </div>
              {onExplore && runSummary.complete > 0 && (
                <button
                  type="button"
                  onClick={onExplore}
                  className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-lg bg-accent px-5 text-sm font-semibold text-white shadow-sm hover:bg-accent-strong"
                >
                  {icons.search} Explore completed-run results
                </button>
              )}
            </div>
          </div>
        )}

        {isTerminal && detail.status === 'cancelled' && (
          <div className="mt-6 rounded-panel border border-slate-300 bg-slate-50 p-5 shadow-panel sm:p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-slate-500 flex items-center justify-center text-white">
                {icons.x}
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Experiment Cancelled</h3>
                <p className="text-sm text-slate-700 mt-1">
                  {runSummary.complete} of {runSummary.expected} run(s) completed before cancellation.
                </p>
              </div>
            </div>
          </div>
        )}

        {isPaused && (
          <div className="mt-6 rounded-panel border border-violet-300 bg-violet-50 p-5 shadow-panel sm:p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-violet-500 flex items-center justify-center text-white">
                {icons.clock}
              </div>
              <div>
                <h3 className="text-lg font-bold text-violet-900">Experiment Paused</h3>
                <p className="text-sm text-violet-800 mt-1">
                  {runSummary.complete} of {runSummary.expected} run(s) completed.
                  {runSummary.neverStarted > 0 && ` ${runSummary.neverStarted} not started yet.`}
                </p>
                <p className="text-xs text-violet-700 mt-2">
                  Resume to continue from the next parameter combination. Use controls in the header above.
                </p>
              </div>
            </div>
          </div>
        )}

        <section className="mt-8 border-t border-line pt-6" aria-labelledby="experiment-storage-context-title">
          <p className="text-xs font-bold uppercase tracking-widest text-accent-strong">Operational context</p>
          <h2 id="experiment-storage-context-title" className="mt-1 font-display text-xl font-semibold text-ink">Stored-result footprint</h2>
          <p className="mb-4 mt-1 text-sm text-muted">Storage metrics remain available after the run outcome, without competing with the primary decision path.</p>
          <ExperimentVectorDbStatsCard
            experimentId={experimentId}
            stats={dbStats ?? undefined}
            loading={dbStatsLoading && !dbStats}
          />
        </section>

        {isRunning && (
          <div className="mt-4 text-center text-xs text-muted">
            Polling every {DETAIL_POLL_MS / 1000}s <span className="animate-pulse">●</span>
          </div>
        )}

        <ConfirmDeleteModal
          isOpen={showDeleteModal}
          onClose={() => setShowDeleteModal(false)}
          onConfirm={handleDelete}
          experimentName={detail?.experiment_name || ''}
          experimentId={experimentId}
          isDeleting={deleting}
        />
    </DashboardShell>
  );
}
