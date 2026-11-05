import { useCallback, useId, useState, type ReactNode } from 'react';

type CollapsibleCardProps = {
  title: string;
  icon?: ReactNode;
  headerExtra?: ReactNode;
  storageKey?: string;
  defaultOpen?: boolean;
  /**
   * Optional override (Slice 56 Part C1). When defined it forces the card open or closed and
   * ignores header clicks (nothing is written to storage); when undefined the card behaves exactly
   * as before, so dropping the override restores the card's own state.
   */
  open?: boolean;
  compact?: boolean;
  className?: string;
  children: ReactNode;
};

function readStoredOpen(storageKey: string | undefined, defaultOpen: boolean): boolean {
  if (!storageKey) return defaultOpen;
  const stored = localStorage.getItem(storageKey);
  if (stored === null) return defaultOpen;
  return stored === 'true';
}

export default function CollapsibleCard({
  title,
  icon,
  headerExtra,
  storageKey,
  defaultOpen = true,
  open: openOverride,
  compact = false,
  className = '',
  children,
}: CollapsibleCardProps) {
  const [ownOpen, setOpen] = useState(() => readStoredOpen(storageKey, defaultOpen));
  const open = openOverride ?? ownOpen;
  const contentId = useId();

  const toggle = useCallback(() => {
    if (openOverride !== undefined) return;
    setOpen((prev) => {
      const next = !prev;
      if (storageKey) localStorage.setItem(storageKey, String(next));
      return next;
    });
  }, [storageKey, openOverride]);

  return (
    <div className={className}>
      <button
        type="button"
        onClick={toggle}
        className="flex min-h-11 w-full items-center gap-2 rounded-lg text-left"
        aria-expanded={open}
        aria-controls={contentId}
      >
        <svg
          className={`h-4 w-4 shrink-0 text-muted transition-transform ${open ? 'rotate-90' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        {icon}
        <h2
          className={
            compact
              ? 'flex-1 text-sm font-bold uppercase tracking-wider text-ink'
              : 'flex-1 font-display text-lg font-semibold text-ink'
          }
        >
          {title}
        </h2>
        {headerExtra}
      </button>
      {open ? <div id={contentId} className="mt-4">{children}</div> : null}
    </div>
  );
}
