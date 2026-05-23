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

export function isTerminalExperimentStatus(status: ExperimentStatus | undefined): boolean {
  if (!status) return false;
  return TERMINAL_STATUSES.includes(status);
}

export function isRunningExperimentStatus(status: ExperimentStatus | undefined): boolean {
  return status === 'running';
}

export function isPausedExperimentStatus(status: ExperimentStatus | undefined): boolean {
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
  // NEW format — unified retrievers
  if (run.retrievers && run.retrievers.length > 0) {
    return run.retrievers.map((r) => {
      const isReranker = r.type === RetrieverType.RERANKER || r.type === RetrieverType.CROSS_ENCODER;
      if (isReranker && r.provider && r.model) {
        return `${r.type} (${r.provider}:${r.model})`;
      }
      return r.type;
    });
  }

  // OLD format — backward compatibility
  const methods: string[] = [];
  if (run.retrieval_method) {
    methods.push(run.retrieval_method);
  }
  if (run.retrieval_model && run.retrieval_provider) {
    methods.push(`reranker (${run.retrieval_provider}:${run.retrieval_model})`);
  }

  return methods.length > 0 ? methods : ['dense']; // default fallback
}
