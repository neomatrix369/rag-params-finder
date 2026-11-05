/**
 * Tests for the Walkthru overlay (callout + spotlight).
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part C2 - overlay rendering, exit button, centred-vs-spotlight placement,
 *        prefers-reduced-motion. Nav controls removed — tour drives real app buttons.
 */
import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import WalkthruOverlay from './WalkthruOverlay';
import { clampToViewport, placeCallout, prefersReducedMotion, sameBox } from './overlayGeometry';

const base = {
  highlight: null as string | null,
  stepId: 'leaderboard',
  title: 'One question, many stores',
  body: 'Same dataset, different store.',
  index: 0,
  total: 5,
  onExit: () => undefined,
};

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.querySelectorAll('[data-tour]').forEach((el) => el.remove());
});

describe('placeCallout / clampToViewport', () => {
  it('Given targets near the edges, when placed, then the callout stays inside the viewport', () => {
    /**
     * Scenario: Callouts never leave the screen at 1280 or 390 px.
     * Slice: 56 Part C2 - overlay layout
     */
    // -- Given --
    const size = { width: 360, height: 200 };
    const vp = { width: 1280, height: 800 };

    // -- When --
    const below = placeCallout({ top: 50, left: 1200, width: 60, height: 40 }, size, vp);
    const above = placeCallout({ top: 600, left: 10, width: 300, height: 150 }, size, vp);
    const inside = placeCallout({ top: 0, left: 0, width: 1280, height: 2000 }, size, vp);
    const center = placeCallout(null, size, vp);

    // -- Then --
    expect(below.side).toBe('below');
    expect(below.left + size.width).toBeLessThanOrEqual(vp.width);
    expect(above.side).toBe('above');
    expect(inside.side).toBe('inside');
    expect(inside.top + size.height).toBeLessThanOrEqual(vp.height);
    expect(center.side).toBe('center');
    // Spotlight clip never sticks past the edge.
    expect(clampToViewport({ top: -20, left: 0, width: 390, height: 2000 }, 390, 844)).toEqual({
      top: 0,
      left: 0,
      width: 390,
      height: 844,
    });
  });
});

describe('placeCallout keeps a tall card fully on-screen', () => {
  const MARGIN = 8;
  const CARD = { width: 360, height: 300 }; // the real card is ~300px, not the old 200px guess

  it.each([
    ['1280x800', { width: 1280, height: 800 }],
    ['390x844', { width: 390, height: 844 }],
  ])('Given a ~300px card in %s, when placed against varied targets, then it never runs off-screen', (_label, vp) => {
    /**
     * Scenario: The Next/Autoplay controls at the card bottom must stay inside the viewport
     *   whatever the highlighted target's size or position (the real-browser Next-off-screen bug).
     * Slice: 56 Part C2 - callout clamped to the viewport
     */
    // -- Given: a large target filling the screen, one near the bottom, one near the top, and none --
    const cases = [
      placeCallout({ top: 0, left: 0, width: vp.width, height: vp.height }, CARD, vp),
      placeCallout({ top: vp.height - 60, left: 10, width: 200, height: 50 }, CARD, vp),
      placeCallout({ top: 10, left: 10, width: 200, height: 50 }, CARD, vp),
      placeCallout(null, CARD, vp),
    ];

    // -- Then: every placement sits within [MARGIN, vh - height - MARGIN] --
    for (const pos of cases) {
      expect(pos.top).toBeGreaterThanOrEqual(MARGIN);
      expect(pos.top + CARD.height).toBeLessThanOrEqual(vp.height - MARGIN);
    }
  });

  it('Given a card taller than the viewport, when placed, then top pins to MARGIN (the card scrolls)', () => {
    /**
     * Scenario: Even a mis-measured, over-tall card cannot push its top below MARGIN.
     * Slice: 56 Part C2 - safety net for an over-tall card
     */
    // -- Given --
    const vp = { width: 390, height: 500 };
    const tall = { width: 360, height: 900 };

    // -- When --
    const pos = placeCallout({ top: 100, left: 0, width: 390, height: 200 }, tall, vp);

    // -- Then --
    expect(pos.top).toBe(MARGIN);
  });
});

describe('sameBox', () => {
  it('Given equal, differing and null boxes, when compared, then equality is decided value-wise', () => {
    /**
     * Scenario: The overlay skips a re-render only when the target box is unchanged.
     * Slice: 56 Part C2 - no per-frame re-render for a static target
     */
    // -- Given --
    const a = { top: 1, left: 2, width: 3, height: 4 };

    // -- When / Then --
    expect(sameBox(a, { ...a })).toBe(true);
    expect(sameBox(a, { ...a, top: 9 })).toBe(false);
    expect(sameBox(null, null)).toBe(true);
    expect(sameBox(a, null)).toBe(false);
    expect(sameBox(null, a)).toBe(false);
  });
});

describe('prefersReducedMotion', () => {
  it('Given a reduce preference, when queried, then it reports true', () => {
    /**
     * Scenario: The overlay reads the OS reduced-motion setting for scroll behaviour.
     * Slice: 56 Part C2 - reduced motion
     */
    // -- Given: jsdom has no matchMedia, so define one that reports the reduce preference --
    vi.stubGlobal('matchMedia', () => ({ matches: true }) as MediaQueryList);

    // -- When / Then --
    expect(prefersReducedMotion()).toBe(true);
  });

  it('Given no matchMedia support, when queried, then it reports false', () => {
    /**
     * Scenario: Without a matchMedia implementation the overlay assumes motion is allowed.
     * Slice: 56 Part C2 - reduced motion fallback
     */
    // -- Given --
    vi.stubGlobal('matchMedia', undefined);

    // -- When / Then --
    expect(prefersReducedMotion()).toBe(false);
  });
});

describe('WalkthruOverlay', () => {
  it('Given a mid-walkthru step, when rendered, then the dialog, step counter and exit button are present', () => {
    /**
     * Scenario: The overlay shows step info and an exit button; nav controls are gone.
     * Slice: 56 Part C2 - overlay callout
     */
    // -- Given / When --
    render(<WalkthruOverlay {...base} index={1} />);

    // -- Then --
    expect(screen.getByRole('dialog', { name: base.title })).toBeInTheDocument();
    expect(screen.getByText('Step 2 of 5')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Exit walkthru' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Next' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Back' })).toBeNull();
    expect(screen.queryByRole('checkbox', { name: 'Autoplay' })).toBeNull();
  });

  it('Given the exit button, when clicked, then onExit fires', () => {
    /**
     * Scenario: The × button is the only manual control in the callout.
     * Slice: 56 Part C2 - exit control
     */
    // -- Given --
    const onExit = vi.fn();
    render(<WalkthruOverlay {...base} onExit={onExit} />);

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Exit walkthru' }));

    // -- Then --
    expect(onExit).toHaveBeenCalledTimes(1);
  });

  it('Given no highlight, when rendered, then a dimmed backdrop is shown instead of a spotlight', () => {
    /**
     * Scenario: A centred callout dims the whole screen (step 5 "Try it").
     * Slice: 56 Part C2 - centred callout
     */
    // -- Given / When --
    render(<WalkthruOverlay {...base} highlight={null} />);

    // -- Then --
    expect(screen.queryByTestId('walkthru-spotlight')).toBeNull();
  });

  it('Given a highlight target in the DOM, when rendered, then a spotlight is drawn over it', () => {
    /**
     * Scenario: The step spotlights its `[data-tour]` panel.
     * Slice: 56 Part C2 - spotlight via [data-tour] box
     */
    // -- Given --
    const target = document.createElement('div');
    target.setAttribute('data-tour', 'leaderboard');
    document.body.appendChild(target);

    // -- When --
    render(<WalkthruOverlay {...base} highlight="leaderboard" />);

    // -- Then --
    expect(screen.getByTestId('walkthru-spotlight')).toBeInTheDocument();
    target.remove();
  });

  it('Given a real card height, when measured, then the card is placed inside the viewport (not off-screen)', () => {
    /**
     * Scenario: jsdom reports offsetHeight 0; stubbing a real ~300px height proves the measured
     *   size (not the old 200px guess) drives placement and keeps the whole card on-screen.
     * Slice: 56 Part C2 - measured callout size (real-browser Next-off-screen bug)
     */
    // -- Given: an 800px-tall viewport and a 300px-tall card --
    const hDesc = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
    const wDesc = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth');
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, get: () => 300 });
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', { configurable: true, get: () => 360 });
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1280 });
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 });

    try {
      // -- When: no highlight → centred, so top = (800 - 300) / 2 = 250 (would be 300 with the old guess) --
      render(<WalkthruOverlay {...base} highlight={null} />);
      const dialog = screen.getByRole('dialog', { name: base.title });
      const top = parseFloat(dialog.style.top);

      // -- Then --
      expect(top).toBe(250);
      expect(top).toBeGreaterThanOrEqual(8);
      expect(top + 300).toBeLessThanOrEqual(800 - 8);
    } finally {
      if (hDesc) Object.defineProperty(HTMLElement.prototype, 'offsetHeight', hDesc);
      if (wDesc) Object.defineProperty(HTMLElement.prototype, 'offsetWidth', wDesc);
    }
  });

  it('Given a target near the viewport bottom, when placed with a tall card, then it is clamped on-screen', () => {
    /**
     * Scenario: A large highlighted panel used to pin the card bottom off-screen.
     * Slice: 56 Part C2 - bottom clamp
     */
    // -- Given --
    const hDesc = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, get: () => 300 });
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 });
    const target = document.createElement('div');
    target.setAttribute('data-tour', 'leaderboard');
    target.getBoundingClientRect = () =>
      ({ top: 740, left: 10, width: 300, height: 50, right: 310, bottom: 790, x: 10, y: 740, toJSON: () => ({}) }) as DOMRect;
    document.body.appendChild(target);

    try {
      // -- When --
      render(<WalkthruOverlay {...base} highlight="leaderboard" />);
      const dialog = screen.getByRole('dialog', { name: base.title });
      const top = parseFloat(dialog.style.top);

      // -- Then --
      expect(top).toBeGreaterThanOrEqual(8);
      expect(top + 300).toBeLessThanOrEqual(800 - 8);
    } finally {
      if (hDesc) Object.defineProperty(HTMLElement.prototype, 'offsetHeight', hDesc);
      target.remove();
    }
  });

  it('Given the overlay, when rendered, then the exit button lives inside the card element', () => {
    /**
     * Scenario: The exit control must be reachable within the dialog card, not clipped away.
     * Slice: 56 Part C2 - exit button inside the card
     */
    // -- Given / When --
    render(<WalkthruOverlay {...base} index={1} />);
    const dialog = screen.getByRole('dialog', { name: base.title });

    // -- Then --
    expect(within(dialog).getByRole('button', { name: 'Exit walkthru' })).toBeInTheDocument();
  });
});
