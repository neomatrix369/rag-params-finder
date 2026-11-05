/**
 * Walkthru state machine.
 *
 * Pattern ported from neomatrix369/japanese-work-life-balancer (ui/src/tour/useTour.ts) at commit
 * ccdbee1b4a4501b5e5394aafab225a583d630354, with the owner's permission (DECISIONS #276); idea
 * credited to Risako. The audio narration and the live-solve controller from that repo are NOT
 * ported - this Walkthru only steps through recorded demo data.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part C2 - <-/->=back/next, Esc=exit; auto-advance always on, clicking the real
 *        app button for the step that needs one (leaderboard Select).
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { WALKTHRU_STEPS, type WalkthruStep } from './steps';

export interface Walkthru {
  active: boolean;
  index: number;
  total: number;
  /** Current step, or undefined before start / with no steps. */
  step: WalkthruStep | undefined;
  isFirst: boolean;
  isLast: boolean;
  start: () => void;
  next: () => void;
  back: () => void;
  exit: () => void;
}

export interface UseWalkthruOptions {
  steps?: WalkthruStep[];
  /** Called after the Walkthru becomes inactive (so the host can restore its screen). */
  onExit?: () => void;
}

/**
 * CSS selector to click on the real app UI before advancing from a given step.
 * null means no click — just advance after durationS.
 */
const STEP_CLICK: Partial<Record<string, string>> = {
  leaderboard: '[data-suggested="true"] button',
};

/** True while a modal dialog (e.g. the About box) is open and should own Esc itself. */
function modalDialogOpen(): boolean {
  return typeof document !== 'undefined' && document.querySelector('[role="dialog"][aria-modal="true"]') !== null;
}

export function useWalkthru(options: UseWalkthruOptions = {}): Walkthru {
  const steps = options.steps ?? WALKTHRU_STEPS;
  const onExitRef = useRef(options.onExit);
  onExitRef.current = options.onExit;

  const [active, setActive] = useState(false);
  const [index, setIndex] = useState(0);

  const total = steps.length;
  // eslint-disable-next-line security/detect-object-injection -- index is a clamped number state
  const step = active ? steps[index] : undefined;
  const isFirst = index === 0;
  const isLast = index === total - 1;

  const start = useCallback(() => {
    setIndex(0);
    setActive(true);
  }, []);

  const next = useCallback(() => {
    setIndex((i) => Math.min(total - 1, i + 1));
  }, [total]);

  const back = useCallback(() => {
    setIndex((i) => Math.max(0, i - 1));
  }, []);

  const exit = useCallback(() => {
    setActive(false);
    onExitRef.current?.();
  }, []);

  // Auto-advance: always on. Click the real app button for the step (if any), then advance.
  useEffect(() => {
    if (!active || step === undefined) return undefined;
    const selector = STEP_CLICK[step.id] ?? null;
    const timer = setTimeout(() => {
      if (selector) document.querySelector<HTMLElement>(selector)?.click();
      if (isLast) exit();
      else next();
    }, step.durationS * 1000);
    return () => clearTimeout(timer);
  }, [active, index, step, isLast, next, exit]);

  // Keyboard: <-/-> back/next, Esc exit. Ignored inside form controls.
  useEffect(() => {
    if (!active) return undefined;
    const onKey = (event: KeyboardEvent): void => {
      const el = event.target as HTMLElement | null;
      const tag = el?.tagName ?? '';
      if (tag === 'SELECT' || tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (event.key === 'Escape') {
        // A modal dialog (the About box) owns Esc while open; let it close itself, not the Walkthru.
        if (modalDialogOpen()) return;
        event.preventDefault();
        exit();
      } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        next();
      } else if (event.key === 'ArrowLeft') {
        event.preventDefault();
        back();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [active, exit, next, back]);

  return {
    active,
    index,
    total,
    step,
    isFirst,
    isLast,
    start,
    next,
    back,
    exit,
  };
}
