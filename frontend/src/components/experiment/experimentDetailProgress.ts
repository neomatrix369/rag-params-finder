/**
 * Progress rule (Slice 67D, finding E): a run is "finished" when it is complete, failed or
 * interrupted. Failed and interrupted runs will not become complete later, so they count
 * as finished work for the progress ring and the ETA. ProgressSubtitle renders this sentence
 * whenever a failed or interrupted run exists.
 * Caveat: the ETA averages elapsed time over all finished runs, so fast failures pull it down.
 */
export const FINISHED_RUN_RULE =
  'Progress and ETA count a run as finished when it is complete, failed or interrupted; ' +
  'failed and interrupted runs will not complete later.';

export function countFinishedRuns({
  complete,
  failed = 0,
  interrupted = 0,
}: {
  complete: number;
  failed?: number;
  interrupted?: number;
}): number {
  return complete + failed + interrupted;
}

/** Fixed-template progress sentence; the "finished" wording appears only when failed or interrupted runs exist. */
export function progressSentence({
  complete,
  failed = 0,
  interrupted = 0,
  total,
}: {
  complete: number;
  failed?: number;
  interrupted?: number;
  total: number;
}): string {
  if (failed + interrupted > 0) {
    const finished = countFinishedRuns({ complete, failed, interrupted });
    return `${finished} of ${total} runs finished (${complete} complete, ${failed} failed, ${interrupted} interrupted)`;
  }
  return `${complete} of ${total} runs completed`;
}

export function calculateProgressPercent({
  expected,
  ...runs
}: {
  complete: number;
  failed?: number;
  interrupted?: number;
  expected: number;
}): number {
  return expected > 0 ? Math.min(100, (countFinishedRuns(runs) / expected) * 100) : 0;
}

export function calculateProgressMetrics({
  completed,
  failed = 0,
  interrupted = 0,
  total,
  startedAt,
  now,
}: {
  completed: number;
  failed?: number;
  interrupted?: number;
  total: number;
  startedAt?: string;
  /** Injected clock (epoch ms); this function never reads the system clock. */
  now: number;
}): { elapsedStr: string; etaStr: string } {
  const start = parseSafeTimestamp(startedAt);

  let elapsedStr = '—';
  let etaStr = '—';

  const finished = countFinishedRuns({ complete: completed, failed, interrupted });

  if (start && finished > 0) {
    const elapsedMs = now - start;
    const elapsedSecs = elapsedMs / 1000;
    elapsedStr = formatTimeWithUnits(elapsedSecs);

    const avgTimePerRun = elapsedMs / finished;
    const remainingRuns = Math.max(0, total - finished);
    const rawEtaMs = avgTimePerRun * remainingRuns;
    const etaMs = rawEtaMs * 1.01;
    const etaSecs = etaMs / 1000;
    etaStr = formatTimeWithUnits(etaSecs);
  }

  return { elapsedStr, etaStr };
}

export function formatTimeWithUnits(totalSeconds: number): string {
  if (totalSeconds < 60) {
    return `${totalSeconds.toFixed(0)}s`;
  }

  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = Math.floor(totalSeconds % 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`;
  }
  return `${minutes}m ${seconds}s`;
}

export function formatDuration(startedAt?: string, completedAt?: string | null): string {
  if (!startedAt || !completedAt) return '—';
  const ms = (parseSafeTimestamp(completedAt) ?? NaN) - (parseSafeTimestamp(startedAt) ?? NaN);
  return formatElapsedMs(ms);
}

function formatElapsedMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return formatTimeWithUnits(ms / 1000);
}

/** The only place a date string is parsed in this module (the determinism guard allows exactly one date parse in this file). */

export function parseSafeTimestamp(value: string | undefined): number | null {
  if (!value) return null;
  const parsed = new Date(value).getTime();
  if (Number.isNaN(parsed)) return null;
  return parsed;
}

export function formatDurationFromRuns(
  runs: { created_at?: string; updated_at?: string }[] = [],
  startedAt?: string,
  completedAt?: string | null,
): string {
  const runStartedAt = Math.min(
    ...runs.map((run) => parseSafeTimestamp(run.created_at)).filter((value): value is number => value !== null),
  );
  const runCompletedAt = Math.max(
    ...runs.map((run) => parseSafeTimestamp(run.updated_at)).filter((value): value is number => value !== null),
  );

  const allRunsHaveTimestamps =
    Number.isFinite(runStartedAt) && Number.isFinite(runCompletedAt) && runCompletedAt >= runStartedAt;

  if (allRunsHaveTimestamps) {
    return formatElapsedMs(runCompletedAt - runStartedAt);
  }

  return formatDuration(startedAt, completedAt);
}
