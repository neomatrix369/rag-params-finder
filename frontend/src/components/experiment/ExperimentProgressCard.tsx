/**
 * ExperimentProgressCard
 *
 * Reusable progress card with circular progress indicator.
 * Shows completion ratio with visual feedback via progress ring.
 *
 * Used across:
 * - ExperimentDetailScreen (main experiment progress)
 * - ExperimentsScreen (inline experiment progress)
 * - Any other screens showing experiment completion status
 */

interface ProgressRingProps {
  percent: number;
  size?: number;
}

function ProgressRing({ percent, size = 80 }: ProgressRingProps) {
  const safePercent = Math.min(100, Math.max(0, percent));
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (safePercent / 100) * circumference;

  return (
    <div
      className="relative inline-flex items-center justify-center"
      role="progressbar"
      aria-label="Experiment completion"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(safePercent)}
    >
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth="4"
          fill="none"
          className="text-accent-soft"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth="4"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="text-accent transition-all duration-500"
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute font-display text-lg font-semibold text-ink">{Math.round(safePercent)}%</span>
    </div>
  );
}

interface ExperimentProgressCardProps {
  /** Main title (e.g., "Experiment Progress") */
  title: string;
  /** Subtitle showing completion (e.g., "1 of 2 runs completed") - accepts string or React node */
  subtitle: string | React.ReactNode;
  /** Completion percentage (0-100) */
  percent: number;
  /** Size variant */
  variant?: 'default' | 'compact';
  /** Custom CSS classes */
  className?: string;
  /** Progress ring size */
  ringSize?: number;
}

export default function ExperimentProgressCard({
  title,
  subtitle,
  percent,
  variant = 'default',
  className = '',
  ringSize,
}: ExperimentProgressCardProps) {
  const defaultRingSize = variant === 'compact' ? 60 : 100;
  const actualRingSize = ringSize ?? defaultRingSize;

  const containerClasses =
    variant === 'compact'
      ? 'relative overflow-hidden rounded-xl border border-line bg-paper p-4 shadow-panel'
      : 'relative overflow-hidden rounded-panel border border-line bg-paper p-6 shadow-panel';

  const titleClasses =
    variant === 'compact'
      ? 'font-display text-base font-semibold text-ink'
      : 'mb-1 font-display text-xl font-semibold text-ink';

  const subtitleClasses = 'text-sm text-muted';

  return (
    <div className={`${containerClasses} ${className}`}>
      <div className="absolute inset-y-0 left-0 w-1 bg-accent" aria-hidden="true" />
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h3 className={titleClasses}>{title}</h3>
          <div className={subtitleClasses}>{subtitle}</div>
        </div>
        <ProgressRing percent={percent} size={actualRingSize} />
      </div>
    </div>
  );
}
