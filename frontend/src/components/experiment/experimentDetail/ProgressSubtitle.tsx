import { calculateProgressMetrics, countFinishedRuns } from '../experimentDetailProgress';

export default function ProgressSubtitle({
  completed,
  failed = 0,
  interrupted = 0,
  total,
  startedAt,
}: {
  completed: number;
  failed?: number;
  interrupted?: number;
  total: number;
  startedAt?: string;
}) {
  const { elapsedStr, etaStr } = calculateProgressMetrics({
    completed,
    failed,
    interrupted,
    total,
    startedAt,
    now: new Date().getTime(),
  });

  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      <span className="font-medium text-ink">
        {failed + interrupted > 0
          ? `${countFinishedRuns({ complete: completed, failed, interrupted })} of ${total} runs finished (${completed} complete, ${failed} failed, ${interrupted} interrupted)`
          : `${completed} of ${total} runs completed`}
      </span>
      <span className="text-line">•</span>
      <span className="inline-flex items-center gap-1.5">
        <span className="text-xs font-semibold uppercase tracking-wide text-cobalt">Elapsed</span>
        <span className="font-mono font-semibold text-cobalt">{elapsedStr}</span>
      </span>
      <span className="text-line">•</span>
      <span className="inline-flex items-center gap-1.5">
        <span className="text-xs font-semibold uppercase tracking-wide text-accent-strong">ETA</span>
        <span className="font-mono font-semibold text-accent-strong">{etaStr}</span>
      </span>
    </div>
  );
}
