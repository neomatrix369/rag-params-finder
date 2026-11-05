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
 * Scope: SLICE-56 Part C2 - Space=pause, <-/->=back/next, Esc=exit; manual Next is the default,
 *        Autoplay is OFF by default and advances by each step's duration_s when on.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { WALKTHRU_STEPS, type WalkthruStep } from './steps';

export interface Walkthru {
  active: boolean;
  index: number;
  total: number;
  /** Current step, or undefined before start / with no steps. */
  step: WalkthruStep | undefined;
  paused: boolean;
  autoplay: boolean;
  isFirst: boolean;
  isLast: boolean;
  start: () => void;
  next: () => void;
  back: () => void;
  togglePause: () => void;
  setAutoplay: (on: boolean) => void;
  exit: () => void;
}

export interface UseWalkthruOptions {
  steps?: WalkthruStep[];
  /** Called after the Walkthru becomes inactive (so the host can restore its screen). */
  onExit?: () => void;
}

/** Elements whose own Space activation (click) must not be hijacked by the pause shortcut. */
function isActivationTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  if (tag === 'BUTTON' || tag === 'A' || tag === 'SUMMARY') return true;
  return el.getAttribute('role') === 'button';
}

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
  const [paused, setPaused] = useState(false);
  const [autoplay, setAutoplayState] = useState(false); // OFF by default

  const total = steps.length;
  // eslint-disable-next-line security/detect-object-injection -- index is a clamped number state
  const step = active ? steps[index] : undefined;
  const isFirst = index === 0;
  const isLast = index === total - 1;

  const start = useCallback(() => {
    setIndex(0);
    setPaused(false);
    setAutoplayState(false);
    setActive(true);
  }, []);

  const next = useCallback(() => {
    setIndex((i) => Math.min(total - 1, i + 1));
  }, [total]);

  const back = useCallback(() => {
    setIndex((i) => Math.max(0, i - 1));
  }, []);

  const togglePause = useCallback(() => setPaused((p) => !p), []);
  const setAutoplay = useCallback((on: boolean) => setAutoplayState(on), []);

  const exit = useCallback(() => {
    setActive(false);
    setPaused(false);
    setAutoplayState(false);
    onExitRef.current?.();
  }, []);

  // Auto-advance: only while active, Autoplay on, not paused and not on the last step.
  useEffect(() => {
    if (!active || !autoplay || paused || isLast || step === undefined) return undefined;
    const timer = setTimeout(next, step.durationS * 1000);
    return () => clearTimeout(timer);
  }, [active, autoplay, paused, isLast, index, step, next]);

  // Keyboard: Space pause, <-/-> back/next, Esc exit. Ignored inside form controls.
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
      } else if (event.key === ' ') {
        // Space activates a focused button/link/summary; don't hijack it into pause there.
        if (isActivationTarget(el)) return;
        event.preventDefault();
        togglePause();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [active, exit, next, back, togglePause]);

  return {
    active,
    index,
    total,
    step,
    paused,
    autoplay,
    isFirst,
    isLast,
    start,
    next,
    back,
    togglePause,
    setAutoplay,
    exit,
  };
}
