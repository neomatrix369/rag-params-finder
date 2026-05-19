import type { ExperimentStatus, RunStatus } from '../types';
import { Phase } from '../types';

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
