import { useCallback, useState, type ReactNode } from 'react';

type CollapsibleCardProps = {
  title: string;
  icon?: ReactNode;
  headerExtra?: ReactNode;
  storageKey?: string;
  defaultOpen?: boolean;
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
  compact = false,
  className = '',
  children,
}: CollapsibleCardProps) {
  const [open, setOpen] = useState(() => readStoredOpen(storageKey, defaultOpen));

  const toggle = useCallback(() => {
    setOpen((prev) => {
      const next = !prev;
      if (storageKey) localStorage.setItem(storageKey, String(next));
      return next;
    });
  }, [storageKey]);

  return (
    <div className={className}>
      <button
        type="button"
        onClick={toggle}
        className="flex w-full items-center gap-2 text-left"
        aria-expanded={open}
      >
        <svg
          className={`h-4 w-4 shrink-0 text-slate-500 transition-transform ${open ? 'rotate-90' : ''}`}
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
              ? 'flex-1 text-sm font-bold uppercase tracking-wider text-slate-700'
              : 'flex-1 text-lg font-bold text-slate-800'
          }
        >
          {title}
        </h2>
        {headerExtra}
      </button>
      {open ? <div className="mt-4">{children}</div> : null}
    </div>
  );
}
