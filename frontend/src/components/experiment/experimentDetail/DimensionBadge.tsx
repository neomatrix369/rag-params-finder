export default function DimensionBadge({
  label,
  values,
}: {
  label: string;
  values: (string | number)[];
}) {
  return (
    <div className="rounded-xl border border-line bg-paper p-3">
      <div className="mb-2 flex items-center gap-2">
        <div className="h-2 w-2 rounded-full bg-accent"></div>
        <span className="text-xs font-bold uppercase tracking-wider text-muted">{label}</span>
      </div>
      <div className="flex flex-wrap gap-1">
        {values.map((v, i) => (
          <span key={i} className="inline-flex items-center rounded-md border border-line bg-canvas px-2 py-1 text-xs font-medium text-ink">
            {String(v)}
          </span>
        ))}
      </div>
    </div>
  );
}
