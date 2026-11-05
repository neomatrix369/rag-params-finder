import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { clampShift } from './infoTipUtils';

export type InfoTipProps = {
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
 * Tooltip pattern: no aria-expanded on the trigger. The tip closes on Escape, outside tap, resize
 * and orientation change.
 */
export default function InfoTip({ label, children, className = '', id }: InfoTipProps) {
  const [open, setOpen] = useState(false);
  const generatedId = useId();
  const tipId = id ?? generatedId;
  const rootRef = useRef<HTMLSpanElement>(null);
  const tipRef = useRef<HTMLSpanElement>(null);
  const [shift, setShift] = useState(0);
  const shiftRef = useRef(0);

  const toggle = useCallback(() => setOpen((prev) => !prev), []);

  const onKeyDown = useCallback((event: KeyboardEvent) => {
    if (event.key === 'Escape') setOpen(false);
  }, []);

  // Thin shell around clampShift. The measured rect already includes the applied shift, so subtract
  // it to get the untransformed position: re-running the effect can never double-apply the nudge.
  useLayoutEffect(() => {
    const tip = tipRef.current;
    let next = 0;
    if (open && tip) {
      const { left, right } = tip.getBoundingClientRect();
      const applied = shiftRef.current;
      next = clampShift({ left: left - applied, right: right - applied }, window.innerWidth);
    }
    shiftRef.current = next;
    setShift(next);
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const close = () => setOpen(false);
    const onOutside = (event: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) close();
    };
    document.addEventListener('pointerdown', onOutside);
    window.addEventListener('resize', close);
    window.addEventListener('orientationchange', close);
    return () => {
      document.removeEventListener('pointerdown', onOutside);
      window.removeEventListener('resize', close);
      window.removeEventListener('orientationchange', close);
    };
  }, [open]);

  return (
    <span ref={rootRef} className={`relative inline-flex ${className}`}>
      <button
        type="button"
        onClick={toggle}
        onKeyDown={onKeyDown}
        aria-label={label}
        aria-describedby={tipId}
        className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-full text-muted hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
      >
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path strokeLinecap="round" d="M12 11v5M12 8h.01" />
        </svg>
      </button>
      <span
        ref={tipRef}
        id={tipId}
        style={{ transform: `translateX(calc(-50% + ${shift}px))` }}
        role="tooltip"
        hidden={!open}
        className="absolute left-1/2 top-full z-20 mt-1 w-64 max-w-[80vw] rounded-md border border-slate-200 bg-white p-2 text-left text-xs font-normal normal-case leading-snug tracking-normal text-slate-700 shadow-lg"
      >
        {children}
      </span>
    </span>
  );
}
