export function calculateProgressMetrics({
  completed,
  total,
  startedAt,
  now = Date.now(),
}: {
  completed: number;
  total: number;
  startedAt?: string;
  now?: number;
}): { elapsedStr: string; etaStr: string } {
  const start = startedAt ? new Date(startedAt).getTime() : null;

  let elapsedStr = '—';
  let etaStr = '—';

  if (start && completed > 0) {
    const elapsedMs = now - start;
    const elapsedSecs = elapsedMs / 1000;
    elapsedStr = formatTimeWithUnits(elapsedSecs);

    const avgTimePerRun = elapsedMs / completed;
    const remainingRuns = total - completed;
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
