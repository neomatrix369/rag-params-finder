export type StatTileProps = {
  label: string;
  value: string | number;
  hint?: string;
  /** `comfortable` for panel tiles; `compact` for dense experiment cards. */
  density?: 'comfortable' | 'compact';
};

export default function StatTile({
  label,
  value,
  hint,
  density = 'comfortable',
}: StatTileProps) {
  if (density === 'compact') {
    return (
      <div className="rounded-md border border-indigo-100 bg-white/90 px-3 py-2">
        <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
        <div className="text-lg font-bold text-indigo-600">{value}</div>
        {hint ? <div className="mt-0.5 text-[10px] leading-snug text-slate-500">{hint}</div> : null}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-indigo-200 bg-white p-4">
      <div className="mb-1 text-xs uppercase tracking-wider text-slate-500">{label}</div>
      <div className="text-2xl font-bold text-indigo-600">{value}</div>
      {hint ? <div className="mt-1 text-xs text-slate-500">{hint}</div> : null}
    </div>
  );
}
