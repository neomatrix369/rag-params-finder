/**
 * Pure placement helpers for the Walkthru overlay (spotlight clipping + callout placement).
 *
 * Pattern ported from neomatrix369/japanese-work-life-balancer (ui/src/components/TourOverlay.tsx) at
 * commit ccdbee1b4a4501b5e5394aafab225a583d630354, with the owner's permission (DECISIONS #276); idea
 * credited to Risako. Kept in a non-component module so React Fast Refresh stays happy.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part C2 - overlay geometry.
 */

export interface Box {
  top: number;
  left: number;
  width: number;
  height: number;
}

const PAD = 6;
const GAP = 12;
const MARGIN = 8;

/** Equal boxes (null-aware), so the overlay can skip a re-render when the target has not moved. */
export function sameBox(a: Box | null, b: Box | null): boolean {
  if (a === null || b === null) return a === b;
  return a.top === b.top && a.left === b.left && a.width === b.width && a.height === b.height;
}

export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}

/** Padded target box, clipped to the viewport so a fixed element never sticks out past the edge. */
export function clampToViewport(rect: Box, vw: number, vh: number): Box {
  const left = Math.max(0, rect.left - PAD);
  const top = Math.max(0, rect.top - PAD);
  const right = Math.min(vw, rect.left + rect.width + PAD);
  const bottom = Math.min(vh, rect.top + rect.height + PAD);
  return { top, left, width: Math.max(0, right - left), height: Math.max(0, bottom - top) };
}

/** Place the callout below the target, else above, else pinned inside the viewport; centred when no rect. */
export function placeCallout(
  rect: Box | null,
  size: { width: number; height: number },
  viewport: { width: number; height: number },
): { top: number; left: number; side: 'below' | 'above' | 'inside' | 'center' } {
  const { width: vw, height: vh } = viewport;
  if (!rect) {
    return {
      top: Math.max(MARGIN, (vh - size.height) / 2),
      left: Math.max(MARGIN, (vw - size.width) / 2),
      side: 'center',
    };
  }
  const left = Math.min(Math.max(MARGIN, rect.left), Math.max(MARGIN, vw - size.width - MARGIN));
  const below = rect.top + rect.height + GAP;
  if (below + size.height <= vh - MARGIN) return { top: below, left, side: 'below' };
  const above = rect.top - GAP - size.height;
  if (above >= MARGIN) return { top: above, left, side: 'above' };
  return { top: Math.max(MARGIN, vh - size.height - MARGIN), left, side: 'inside' };
}
