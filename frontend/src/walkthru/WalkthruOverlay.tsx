/**
 * Walkthru overlay: a spotlight on the step's `[data-tour]` target and a callout with the controls.
 *
 * Pattern ported from neomatrix369/japanese-work-life-balancer (ui/src/components/TourOverlay.tsx) at
 * commit ccdbee1b4a4501b5e5394aafab225a583d630354, with the owner's permission (DECISIONS #276); idea
 * credited to Risako. The audio narration, lucide icons, bundled stylesheet and component design
 * library from that repo are NOT ported. Styling is Tailwind and the overlay never animates (so it respects
 * prefers-reduced-motion); only the scroll-into-view behaviour is reduced-motion aware.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part C2 - spotlight + callout, manual Next default, visible Autoplay toggle.
 */
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { clampToViewport, placeCallout, prefersReducedMotion, sameBox, type Box } from './overlayGeometry';

export interface WalkthruOverlayProps {
  /** `data-tour` anchor to spotlight; null = centred callout. */
  highlight: string | null;
  stepId: string;
  title: string;
  body: string;
  index: number;
  total: number;
  paused: boolean;
  autoplay: boolean;
  isFirst: boolean;
  isLast: boolean;
  onNext: () => void;
  onBack: () => void;
  onTogglePause: () => void;
  onSetAutoplay: (on: boolean) => void;
  onExit: () => void;
}

const BTN =
  'min-h-11 rounded-lg border border-line bg-paper px-3 text-sm font-semibold text-ink hover:border-accent disabled:opacity-40';

export default function WalkthruOverlay(props: WalkthruOverlayProps) {
  const {
    highlight, stepId, title, body, index, total, paused, autoplay, isFirst, isLast,
    onNext, onBack, onTogglePause, onSetAutoplay, onExit,
  } = props;
  const [rect, setRect] = useState<Box | null>(null);
  const calloutRef = useRef<HTMLDivElement>(null);
  // The callout's real measured size; a hard-coded guess pinned the card off-screen (see tests).
  const [size, setSize] = useState({ width: 360, height: 200 });
  const [viewport, setViewport] = useState(() => ({ width: window.innerWidth, height: window.innerHeight }));

  // Re-measure the real callout box whenever its content or the viewport changes.
  useLayoutEffect(() => {
    const el = calloutRef.current;
    if (!el) return;
    const next = { width: el.offsetWidth || 360, height: el.offsetHeight || 200 };
    setSize((prev) => (prev.width === next.width && prev.height === next.height ? prev : next));
  }, [title, body, stepId, index, isLast, viewport.width, viewport.height]);

  // Keep the viewport in sync so placement is recomputed on resize/rotation.
  useEffect(() => {
    const onResize = (): void => setViewport({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // Track the target's box every frame (panels move as the page scrolls / loads).
  useEffect(() => {
    if (!highlight) {
      setRect(null);
      return undefined;
    }
    let raf = 0;
    let scrolled = false;
    const tick = (): void => {
      const el = document.querySelector<HTMLElement>(`[data-tour="${highlight}"]`);
      if (el && !scrolled) {
        scrolled = true;
        el.scrollIntoView?.({ block: 'center', behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
      }
      const r = el?.getBoundingClientRect();
      const next = r ? clampToViewport(r, document.documentElement.clientWidth, window.innerHeight) : null;
      // Only re-render when the box actually moved; a static target must not re-render every frame.
      setRect((prev) => (sameBox(prev, next) ? prev : next));
      raf = requestAnimationFrame(tick);
    };
    tick();
    return () => cancelAnimationFrame(raf);
  }, [highlight, stepId]);

  const pos = placeCallout(rect, size, viewport);

  return createPortal(
    <div className="fixed inset-0 z-[60]" data-testid="walkthru-root">
      {rect ? (
        <div
          data-testid="walkthru-spotlight"
          className="pointer-events-none fixed rounded-lg ring-4 ring-accent ring-offset-2"
          style={{ top: rect.top, left: rect.left, width: rect.width, height: rect.height, boxShadow: '0 0 0 9999px rgba(0,0,0,0.5)' }}
          aria-hidden="true"
        />
      ) : (
        <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
      )}
      <div
        ref={calloutRef}
        role="dialog"
        aria-modal="false"
        aria-label={title}
        className="fixed max-h-[calc(100vh-16px)] w-[min(360px,calc(100vw-16px))] overflow-y-auto rounded-panel border border-line bg-paper p-4 text-ink shadow-lift"
        style={{ top: pos.top, left: pos.left }}
      >
        <div className="mb-2 flex items-center justify-between gap-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted">
            Step {index + 1} of {total}
          </span>
          <button type="button" onClick={onExit} aria-label="Exit walkthru" title="Exit (Esc)" className="h-8 w-8 rounded-lg text-lg text-muted hover:text-ink">
            <span aria-hidden="true">×</span>
          </button>
        </div>
        <h2 className="font-display text-lg font-semibold text-ink">{title}</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink" aria-live="polite">
          {body}
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button type="button" className={BTN} onClick={onBack} disabled={isFirst}>
            Back
          </button>
          {!isLast && (
            <button type="button" className={BTN} onClick={onTogglePause} aria-pressed={paused}>
              {paused ? 'Resume' : 'Pause'}
            </button>
          )}
          {isLast ? (
            <button type="button" className={`${BTN} border-accent bg-accent-soft`} onClick={onExit}>
              Finish
            </button>
          ) : (
            <button type="button" className={`${BTN} border-accent bg-accent-soft`} onClick={onNext}>
              Next
            </button>
          )}
          <label className="ml-auto flex min-h-11 items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={autoplay}
              onChange={(event) => onSetAutoplay(event.target.checked)}
              aria-label="Autoplay"
            />
            Autoplay
          </label>
        </div>
        <p className="mt-3 text-xs text-muted">Space pause · ←/→ back/next · Esc exit</p>
      </div>
    </div>,
    document.body,
  );
}
