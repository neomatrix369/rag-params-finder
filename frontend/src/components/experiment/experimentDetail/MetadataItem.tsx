export default function MetadataItem({
  label,
  value,
}: {
  label: string;
  value: string | number | boolean | undefined;
}) {
  if (value === undefined || value === null) return null;

  const formatValue = (val: string | number | boolean): string => {
    if (typeof val === 'number') {
      if (label.includes('TPM') || label.includes('RPM')) {
        return val.toLocaleString();
      }
      return String(val);
    }
    return String(val);
  };

  return (
    <div className="flex flex-col">
      <span className="text-xs uppercase tracking-wider text-muted">{label}</span>
      <span className="font-mono text-sm text-ink">{formatValue(value)}</span>
    </div>
  );
}
