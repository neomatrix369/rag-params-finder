import { useCallback, useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';

type InfoTipProps = {
  /** Accessible name of the trigger (short, e.g. "About Total"); the tip text is NOT repeated in it. */
  label: string;
  children: ReactNode;
  className?: string;
  /** Optional caller-supplied tip id; defaults to React useId (deterministic, never random). */
  id?: string;
};

/**
 * Dependency-free explain affordance (Slice 67C). A native button toggles a tip that stays in the
 * DOM and is linked via aria-describedby, so assistive tech reads it once (no live region).
 */
export default function InfoTip({ label, children, className = '', id }: InfoTipProps) {
  const [open, setOpen] = useState(false);
  const generatedId = useId();
  const tipId = id ?? generatedId;
  const rootRef = useRef<HTMLSpanElement>(null);

  const toggle = useCallback(() => setOpen((prev) => !prev), []);

  const onKeyDown = useCallback((event: KeyboardEvent) => {
    if (event.key === 'Escape') setOpen(false);
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const onOutside = (event: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('pointerdown', onOutside);
    return () => document.removeEventListener('pointerdown', onOutside);
  }, [open]);

  return (
    <span ref={rootRef} className={`relative inline-flex ${className}`} onKeyDown={onKeyDown}>
      <button
        type="button"
        onClick={toggle}
        aria-label={label}
        aria-describedby={tipId}
        aria-expanded={open}
        className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-full text-muted hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
      >
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path strokeLinecap="round" d="M12 11v5M12 8h.01" />
        </svg>
      </button>
      <span
        id={tipId}
        role="tooltip"
        hidden={!open}
        className="absolute left-1/2 top-full z-20 mt-1 w-64 max-w-[80vw] -translate-x-1/2 rounded-md border border-slate-200 bg-white p-2 text-left text-xs font-normal normal-case leading-snug tracking-normal text-slate-700 shadow-lg"
      >
        {children}
      </span>
    </span>
  );
}
