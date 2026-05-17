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
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth="4"
          fill="none"
          className="text-slate-200"
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
          className="text-green-500 transition-all duration-500"
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute text-lg font-bold text-slate-700">{Math.round(percent)}%</span>
    </div>
  );
}

interface ExperimentProgressCardProps {
  /** Main title (e.g., "Experiment Progress") */
  title: string;
  /** Subtitle showing completion (e.g., "1 of 2 runs completed") */
  subtitle: string;
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
      ? 'bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl shadow-sm border border-blue-200 p-4'
      : 'bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl shadow-sm border border-blue-200 p-6';

  const titleClasses =
    variant === 'compact'
      ? 'text-base font-bold text-slate-800'
      : 'text-lg font-bold text-slate-800 mb-1';

  const subtitleClasses = 'text-sm text-slate-600';

  return (
    <div className={`${containerClasses} ${className}`}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className={titleClasses}>{title}</h3>
          <p className={subtitleClasses}>{subtitle}</p>
        </div>
        <ProgressRing percent={percent} size={actualRingSize} />
      </div>
    </div>
  );
}
