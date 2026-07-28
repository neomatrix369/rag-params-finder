import type { ReactNode } from 'react';

export default function StatCard({
  label,
  value,
  icon,
  trend,
  color = 'blue',
  compact = false,
}: {
  label: string;
  value: string | number;
  icon: ReactNode;
  trend?: string;
  color?: 'blue' | 'green' | 'purple' | 'amber' | 'red' | 'slate';
  compact?: boolean;
}) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    green: 'bg-green-50 text-green-700 border-green-200',
    purple: 'bg-accent-soft text-accent-strong border-accent',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
    red: 'bg-red-50 text-red-700 border-red-200',
    slate: 'bg-slate-50 text-slate-600 border-slate-200',
  } as const;
  // color is a typed union — safe lookup, not user-controlled injection.
  // eslint-disable-next-line security/detect-object-injection -- keyed by StatCard color prop union
  const colorClass = colors[color];

  if (compact) {
    return (
      <div className={`${colorClass} rounded-lg border px-3 py-2.5 min-w-0 h-full`}>
        <div className="flex items-center gap-2 min-w-0">
          <div className="shrink-0 scale-90 opacity-80">{icon}</div>
          <div className="min-w-0 flex-1">
            <div className="text-lg font-bold leading-none tabular-nums truncate">{value}</div>
            <div className="mt-1 truncate text-xs font-semibold uppercase tracking-wide opacity-75">
              {label}
            </div>
          </div>
          {trend && (
            <span className="shrink-0 text-xs font-medium opacity-75">{trend}</span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={`${colorClass} rounded-xl p-4 border-2 shadow-sm`}>
      <div className="flex items-start justify-between mb-2">
        <div className="p-2 rounded-lg bg-white/80">
          {icon}
        </div>
        {trend && <span className="text-xs font-medium opacity-75">{trend}</span>}
      </div>
      <div className="mt-2">
        <div className="text-2xl font-bold">{value}</div>
        <div className="text-xs font-medium uppercase tracking-wide mt-1 opacity-75">{label}</div>
      </div>
    </div>
  );
}
