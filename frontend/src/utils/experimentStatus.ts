import type { ExperimentStatus, RunStatus, RetrieverConfig } from '../types';
import { Phase, RetrieverType } from '../types';

const TERMINAL_STATUSES: ExperimentStatus[] = ['complete', 'failed', 'partial', 'cancelled'];

export interface ExperimentRunSummary {
  expected: number;
  started: number;
  complete: number;
  failed: number;
  interrupted: number;
  neverStarted: number;
  inProgress: number;
}

export function summarizeExperimentRuns(
  runs: RunStatus[] | undefined,
  expectedRunCount: number | undefined,
): ExperimentRunSummary {
  const expected = expectedRunCount ?? runs?.length ?? 0;
  const started = runs?.length ?? 0;
  const complete = runs?.filter((run) => run.phase === Phase.COMPLETE).length ?? 0;
  const failed = runs?.filter((run) => run.phase === Phase.FAILED).length ?? 0;
  const interrupted = runs?.filter((run) => run.phase === Phase.INTERRUPTED).length ?? 0;
  const neverStarted = Math.max(0, expected - started);
  const inProgress = Math.max(0, started - complete - failed - interrupted);

  return { expected, started, complete, failed, interrupted, neverStarted, inProgress };
}

/**
 * Bayesian trials that were planned but neither attempted nor discarded by the sampler.
 * The one place this subtraction happens; list and detail screens both call it.
 */
export function bayesianNotStartedCount(
  planned: number,
  attempted: number,
  discarded: number,
): number {
  return Math.max(0, planned - attempted - discarded);
}

/**
 * The one denominator every Detail-screen count uses: planned trials for a Bayesian sweep
 * (run_count can differ), the expected run count for a grid sweep.
 */
export function detailDenominator({
  isBayesian,
  plannedTrials,
  expectedRuns,
}: {
  isBayesian: boolean;
  plannedTrials: number;
  expectedRuns: number;
}): number {
  return isBayesian ? plannedTrials : expectedRuns;
}

/** Ids of experiments that bulk actions may select (running ones are excluded). */
export function selectableExperimentIds(
  experiments: ReadonlyArray<{ experiment_id: string; status: ExperimentStatus }>,
): string[] {
  return experiments.filter((exp) => exp.status !== 'running').map((exp) => exp.experiment_id);
}

/**
 * Fixed-template sentence showing how the Bayesian Total splits. Discarded trials are
 * sampler decisions, not runs, so they are listed apart from the run cards.
 * Prints "=" only when the parts really add up to planned.
 */
export function bayesianTotalsLine({
  planned,
  attempted,
  discarded,
  notStarted,
  inProgress = 0,
}: {
  planned: number;
  attempted: number;
  discarded: number;
  notStarted: number;
  /** Runs still executing; they are part of attempted, so this only annotates it. */
  inProgress?: number;
}): string {
  const note = 'Discarded trials are not runs.';
  const attemptedText = inProgress > 0 ? `${attempted} attempted (${inProgress} in progress)` : `${attempted} attempted`;
  if (attempted + discarded + notStarted === planned) {
    return `Total ${planned} = ${attemptedText} + ${discarded} discarded + ${notStarted} not started. ${note}`;
  }
  const attemptedList = inProgress > 0 ? `attempted ${attempted} (${inProgress} in progress)` : `attempted ${attempted}`;
  return `Total ${planned}; ${attemptedList}, discarded ${discarded}, not started ${notStarted} (parts do not add up yet). ${note}`;
}

function isCompletedByTimestamp(
  completedAt: string | null | undefined,
): boolean {
  return Boolean(completedAt);
}

export function isTerminalExperimentStatus(
  status: ExperimentStatus | undefined,
  completedAt?: string | null,
): boolean {
  if (isCompletedByTimestamp(completedAt)) return true;
  if (!status) return false;
  return TERMINAL_STATUSES.includes(status);
}

export function isRunningExperimentStatus(
  status: ExperimentStatus | undefined,
  completedAt?: string | null,
): boolean {
  if (isCompletedByTimestamp(completedAt)) return false;
  return status === 'running';
}

export function isPausedExperimentStatus(
  status: ExperimentStatus | undefined,
  completedAt?: string | null,
): boolean {
  if (isCompletedByTimestamp(completedAt)) return false;
  return status === 'paused';
}

export function isActiveExperimentStatus(status: ExperimentStatus | undefined): boolean {
  return status === 'running' || status === 'paused';
}

/**
 * Display retrievers as human-readable strings with backward compatibility.
 *
 * New format: reads from `run.retrievers` array
 * Old format: falls back to `run.retrieval_method` + `run.retrieval_model`
 */
export function displayRetrievers(run: RunStatus | { retrievers?: RetrieverConfig[]; retrieval_method?: string; retrieval_provider?: string; retrieval_model?: string | null }): string[] {
  if (run.retrievers && run.retrievers.length > 0) {
    const retriever = run.retrievers[0];
    const isReranker = retriever.type === RetrieverType.RERANKER || retriever.type === RetrieverType.CROSS_ENCODER;
    if (isReranker && retriever.provider && retriever.model) {
      return [`${retriever.type} (${retriever.provider}:${retriever.model})`];
    }
    return [retriever.type];
  }

  // OLD format — reranker-only runs stored retrieval_method as dense for legacy consumers
  if (run.retrieval_model && run.retrieval_provider) {
    const rerankerType = run.retrieval_provider === 'voyage' ? RetrieverType.RERANKER : RetrieverType.CROSS_ENCODER;
    return [`${rerankerType} (${run.retrieval_provider}:${run.retrieval_model})`];
  }

  if (run.retrieval_method) {
    return [run.retrieval_method];
  }

  return ['dense'];
}
