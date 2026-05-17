/**
 * PollingIndicator
 *
 * Subtle, non-intrusive indicator for background polling/refresh operations.
 * Shows a pulsing dot with "Syncing..." text when active.
 *
 * Usage:
 *   <PollingIndicator active={isPolling} />
 */

export default function PollingIndicator({ active }: { active: boolean }) {
  if (!active) return null;

  return (
    <div className="flex items-center gap-2 text-xs text-slate-500" role="status" aria-live="polite">
      <span
        className="h-2 w-2 rounded-full bg-blue-500 animate-pulse"
        aria-hidden="true"
      />
      <span>Syncing...</span>
    </div>
  );
}
