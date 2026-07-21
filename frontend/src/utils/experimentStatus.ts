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
