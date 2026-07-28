export type StatRowProps = {
  label: string;
  value: string;
  mono?: boolean;
  density?: 'comfortable' | 'compact';
};

/** Label/value row used inside vector-DB stats panels. */
export default function StatRow({
  label,
  value,
  mono = false,
  density = 'comfortable',
}: StatRowProps) {
  const gap = density === 'compact' ? 'gap-3 text-xs' : 'gap-4';
  let monoClass = '';
  if (mono) {
    monoClass = density === 'compact' ? 'font-mono text-[11px]' : 'font-mono text-xs';
  }

  return (
    <div className={`flex justify-between ${gap}`}>
      <span className="text-slate-600">{label}</span>
      <span className={`font-medium text-slate-900 ${monoClass}`}>{value}</span>
    </div>
  );
}
