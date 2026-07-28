import { detailIcons } from './icons';

export default function StatusBadge({ status }: { status: string }) {
  const configByStatus = {
    complete: { bg: 'bg-emerald-50', text: 'text-emerald-800', icon: detailIcons.check, border: 'border-emerald-200' },
    running: { bg: 'bg-blue-50', text: 'text-blue-800', icon: detailIcons.play, border: 'border-blue-200' },
    failed: { bg: 'bg-red-50', text: 'text-red-800', icon: detailIcons.x, border: 'border-red-200' },
    partial: { bg: 'bg-amber-50', text: 'text-amber-900', icon: detailIcons.x, border: 'border-amber-200' },
    cancelled: { bg: 'bg-slate-100', text: 'text-slate-800', icon: detailIcons.x, border: 'border-slate-300' },
    paused: { bg: 'bg-violet-50', text: 'text-violet-800', icon: detailIcons.clock, border: 'border-violet-200' },
  } as const;
  const defaultConfig = { bg: 'bg-canvas', text: 'text-ink', icon: detailIcons.clock, border: 'border-line' };
  const config =
    status in configByStatus
      ? configByStatus[status as keyof typeof configByStatus]
      : defaultConfig;

  return (
    <div className={`inline-flex min-h-9 items-center gap-2 rounded-full border px-4 py-2 font-semibold ${config.bg} ${config.text} ${config.border}`}>
      {config.icon}
      <span className="uppercase text-sm tracking-wide">{status}</span>
    </div>
  );
}
