import { FINISHED_RUN_RULE, calculateProgressMetrics, progressSentence } from '../experimentDetailProgress';

export default function ProgressSubtitle({
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
  /** Injected clock (epoch ms); the screen supplies it, this component never reads the system clock. */
  now: number;
}) {
  const { elapsedStr, etaStr } = calculateProgressMetrics({
    completed,
    failed,
    interrupted,
    total,
    startedAt,
    now,
  });

  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      <span className="font-medium text-ink">
        {progressSentence({ complete: completed, failed, interrupted, total })}
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
      {failed + interrupted > 0 && (
        <p className="basis-full text-xs text-muted">{FINISHED_RUN_RULE}</p>
      )}
    </div>
  );
}
