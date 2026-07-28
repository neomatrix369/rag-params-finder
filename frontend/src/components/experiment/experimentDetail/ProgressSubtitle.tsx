import { calculateProgressMetrics } from '../experimentDetailProgress';

export default function ProgressSubtitle({
  completed,
  total,
  startedAt,
}: {
  completed: number;
  total: number;
  startedAt?: string;
}) {
  const { elapsedStr, etaStr } = calculateProgressMetrics({
    completed,
    total,
    startedAt,
    now: new Date().getTime(),
  });

  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      <span className="font-medium text-ink">
        {completed} of {total} runs completed
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
