/**
 * Tests for the Walkthru overlay (callout + spotlight + controls).
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part C2 - overlay rendering, control handlers, visible Autoplay toggle,
 *        centred-vs-spotlight placement, prefers-reduced-motion.
 */
import { fireEvent, render, screen } from '@testing-library/react';
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
  paused: false,
  autoplay: false,
  isFirst: true,
  isLast: false,
  onNext: () => undefined,
  onBack: () => undefined,
  onTogglePause: () => undefined,
  onSetAutoplay: () => undefined,
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
  it('Given a mid-walkthru step, when rendered, then the dialog, step counter and controls are present', () => {
    /**
     * Scenario: A presenter steps through the Walkthru with Back / Pause / Next.
     * Slice: 56 Part C2 - overlay controls
     */
    // -- Given --
    const onNext = vi.fn();
    const onBack = vi.fn();
    const onTogglePause = vi.fn();
    render(<WalkthruOverlay {...base} index={1} isFirst={false} />);

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    fireEvent.click(screen.getByRole('button', { name: 'Back' }));
    fireEvent.click(screen.getByRole('button', { name: 'Pause' }));

    // -- Then --
    expect(screen.getByRole('dialog', { name: base.title })).toBeInTheDocument();
    expect(screen.getByText('Step 2 of 5')).toBeInTheDocument();
    render(<WalkthruOverlay {...base} index={1} isFirst={false} onNext={onNext} onBack={onBack} onTogglePause={onTogglePause} />);
    fireEvent.click(screen.getAllByRole('button', { name: 'Next' })[1]);
    fireEvent.click(screen.getAllByRole('button', { name: 'Back' })[1]);
    fireEvent.click(screen.getAllByRole('button', { name: 'Pause' })[1]);
    expect(onNext).toHaveBeenCalled();
    expect(onBack).toHaveBeenCalled();
    expect(onTogglePause).toHaveBeenCalled();
  });

  it('Given Autoplay is off, when the toggle is flipped, then onSetAutoplay(true) fires', () => {
    /**
     * Scenario: The Autoplay toggle is visible and starts unchecked.
     * Slice: 56 Part C2 - Autoplay OFF by default + visible toggle
     */
    // -- Given --
    const onSetAutoplay = vi.fn();
    render(<WalkthruOverlay {...base} onSetAutoplay={onSetAutoplay} />);
    const toggle = screen.getByRole('checkbox', { name: 'Autoplay' });

    // -- Then: visible and unchecked --
    expect(toggle).toBeInTheDocument();
    expect(toggle).not.toBeChecked();

    // -- When --
    fireEvent.click(toggle);

    // -- Then --
    expect(onSetAutoplay).toHaveBeenCalledWith(true);
  });

  it('Given the first step, when rendered, then Back is disabled and Pause is shown', () => {
    /**
     * Scenario: Nothing to go back to on step 1.
     * Slice: 56 Part C2 - first-step controls
     */
    // -- Given / When --
    render(<WalkthruOverlay {...base} />);

    // -- Then --
    expect(screen.getByRole('button', { name: 'Back' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Pause' })).toBeInTheDocument();
  });

  it('Given paused, when rendered, then the toggle reads Resume', () => {
    /**
     * Scenario: The pause control reflects the paused state.
     * Slice: 56 Part C2 - pause label
     */
    // -- Given / When --
    render(<WalkthruOverlay {...base} paused />);

    // -- Then --
    expect(screen.getByRole('button', { name: 'Resume' })).toBeInTheDocument();
  });

  it('Given the last step, when rendered, then Finish exits and Next/Pause are gone', () => {
    /**
     * Scenario: The final step offers Finish instead of Next.
     * Slice: 56 Part C2 - last-step controls
     */
    // -- Given --
    const onExit = vi.fn();
    render(<WalkthruOverlay {...base} index={4} isFirst={false} isLast onExit={onExit} />);

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Finish' }));

    // -- Then --
    expect(onExit).toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: 'Next' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Pause' })).toBeNull();
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
});
