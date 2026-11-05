/**
 * Tests for the Walkthru state machine.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part C2 - keys (arrows/Esc), always-on auto-advance, real-button click for
 *        leaderboard step, smoke that ArrowRight from step 1 reaches step 3, and Esc calls onExit.
 */
import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useWalkthru } from './useWalkthru';
import type { WalkthruStep } from './steps';

const STEPS: WalkthruStep[] = [
  { id: 's1', title: 'One', durationS: 2, route: 'walkthru', highlight: 'a', choose: null, body: 'one' },
  { id: 's2', title: 'Two', durationS: 3, route: 'walkthru', highlight: 'b', choose: null, body: 'two' },
  { id: 's3', title: 'Three', durationS: 4, route: 'walkthru', highlight: null, choose: null, body: 'three' },
];

const press = (key: string) =>
  window.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true }));

afterEach(() => vi.useRealTimers());

describe('useWalkthru', () => {
  it('Given a fresh hook, when started, then it is active at step 1', () => {
    /**
     * Scenario: Starting the walkthru lands on the first step.
     * Slice: 56 Part C2 - start
     */
    // -- Given --
    const { result } = renderHook(() => useWalkthru({ steps: STEPS }));

    // -- When --
    act(() => result.current.start());

    // -- Then --
    expect(result.current.active).toBe(true);
    expect(result.current.index).toBe(0);
    expect(result.current.step?.id).toBe('s1');
  });

  it('Given an active Walkthru, when Next is pressed to the end, then it reaches the last step and clamps', () => {
    /**
     * Scenario: Next from the first step walks through to the last and stops there.
     * Slice: 56 Part C2 - smoke: Next reaches the final step
     */
    // -- Given --
    const { result } = renderHook(() => useWalkthru({ steps: STEPS }));
    act(() => result.current.start());

    // -- When --
    act(() => press('ArrowRight'));
    act(() => press('ArrowRight'));
    act(() => press('ArrowRight')); // past the end

    // -- Then --
    expect(result.current.index).toBe(2);
    expect(result.current.isLast).toBe(true);
  });

  it('Given an active Walkthru, when ArrowLeft is pressed, then it steps back and clamps at the first', () => {
    /**
     * Scenario: Back navigation with the left arrow.
     * Slice: 56 Part C2 - keyboard back
     */
    // -- Given --
    const { result } = renderHook(() => useWalkthru({ steps: STEPS }));
    act(() => result.current.start());
    act(() => press('ArrowRight'));

    // -- When --
    act(() => press('ArrowLeft'));
    act(() => press('ArrowLeft')); // past the start

    // -- Then --
    expect(result.current.index).toBe(0);
    expect(result.current.isFirst).toBe(true);
  });

  it('Given focus in a SELECT, when a key is pressed, then the Walkthru ignores it', () => {
    /**
     * Scenario: Keyboard shortcuts never hijack a form control (the run picker is a <select>).
     * Slice: 56 Part C2 - keyboard guard
     */
    // -- Given --
    const { result } = renderHook(() => useWalkthru({ steps: STEPS }));
    act(() => result.current.start());
    const select = document.createElement('select');
    document.body.appendChild(select);

    // -- When --
    act(() => select.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true })));

    // -- Then --
    expect(result.current.index).toBe(0);
    select.remove();
  });

  it('Given an open modal dialog, when Esc is pressed, then the Walkthru stays active (the dialog owns Esc)', () => {
    /**
     * Scenario: The About box is open over the Walkthru; Esc closes only the dialog.
     * Slice: 56 Part C2 - Esc defers to an open modal dialog
     */
    // -- Given --
    const onExit = vi.fn();
    const { result } = renderHook(() => useWalkthru({ steps: STEPS, onExit }));
    act(() => result.current.start());
    const dialog = document.createElement('div');
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    document.body.appendChild(dialog);

    // -- When --
    act(() => press('Escape'));

    // -- Then --
    expect(result.current.active).toBe(true);
    expect(onExit).not.toHaveBeenCalled();

    // -- And when the dialog is gone, Esc exits as usual --
    dialog.remove();
    act(() => press('Escape'));
    expect(result.current.active).toBe(false);
    expect(onExit).toHaveBeenCalledTimes(1);
  });

  it('Given Esc, when pressed, then it exits and calls onExit', () => {
    /**
     * Scenario: Esc leaves the Walkthru and lets the host restore its screen.
     * Slice: 56 Part C2 - Esc restores screen
     */
    // -- Given --
    const onExit = vi.fn();
    const { result } = renderHook(() => useWalkthru({ steps: STEPS, onExit }));
    act(() => result.current.start());

    // -- When --
    act(() => press('Escape'));

    // -- Then --
    expect(result.current.active).toBe(false);
    expect(onExit).toHaveBeenCalledTimes(1);
  });

  it('Given an active Walkthru, when a step duration elapses, then it auto-advances', () => {
    /**
     * Scenario: Auto-advance is always on; each step fires after its own duration_s.
     * Slice: 56 Part C2 - always-on auto-advance
     */
    // -- Given --
    vi.useFakeTimers();
    const { result } = renderHook(() => useWalkthru({ steps: STEPS }));
    act(() => result.current.start());

    // -- When: step 1 is 2 s --
    act(() => vi.advanceTimersByTime(2_000));
    // -- Then --
    expect(result.current.index).toBe(1);

    // -- When: step 2 is 3 s --
    act(() => vi.advanceTimersByTime(3_000));
    // -- Then --
    expect(result.current.index).toBe(2);
  });

  it('Given the last step, when its duration elapses, then exit is called', () => {
    /**
     * Scenario: The last step auto-exits instead of trying to advance past the end.
     * Slice: 56 Part C2 - auto-exit on last step
     */
    // -- Given --
    vi.useFakeTimers();
    const onExit = vi.fn();
    const { result } = renderHook(() => useWalkthru({ steps: STEPS, onExit }));
    act(() => result.current.start());
    // advance to last step (s3)
    act(() => vi.advanceTimersByTime(2_000)); // s1 → s2
    act(() => vi.advanceTimersByTime(3_000)); // s2 → s3

    // -- When: step 3 is 4 s --
    act(() => vi.advanceTimersByTime(4_000));

    // -- Then --
    expect(result.current.active).toBe(false);
    expect(onExit).toHaveBeenCalledTimes(1);
  });

  it('Given the leaderboard step, when its duration elapses, then the suggested button is clicked', () => {
    /**
     * Scenario: The leaderboard step simulates clicking the [data-suggested] Select button.
     * Slice: 56 Part C2 - real-button click for leaderboard step
     */
    // -- Given --
    vi.useFakeTimers();
    const suggestedRow = document.createElement('tr');
    suggestedRow.setAttribute('data-suggested', 'true');
    const btn = document.createElement('button');
    const clickSpy = vi.fn();
    btn.addEventListener('click', clickSpy);
    suggestedRow.appendChild(btn);
    document.body.appendChild(suggestedRow);

    const leaderboardStep: WalkthruStep = {
      id: 'leaderboard', title: 'Leaderboard', durationS: 2, route: 'walkthru',
      highlight: 'leaderboard', choose: { target: 'leaderboard', suggest: 'redis' }, body: 'body',
    };
    const { result } = renderHook(() => useWalkthru({ steps: [leaderboardStep, ...STEPS.slice(0, 1)] }));
    act(() => result.current.start());

    // -- When --
    act(() => vi.advanceTimersByTime(2_000));

    // -- Then --
    expect(clickSpy).toHaveBeenCalledTimes(1);
    suggestedRow.remove();
  });

  it('Given the default options, when started, then the bundled steps drive it', () => {
    /**
     * Scenario: With no steps passed, the hook uses the bundled WALKTHRU_STEPS.
     * Slice: 56 Part C2 - default steps
     */
    // -- Given --
    const { result } = renderHook(() => useWalkthru());

    // -- When --
    act(() => result.current.start());

    // -- Then --
    expect(result.current.total).toBe(5);
    expect(result.current.step?.id).toBe('leaderboard');
  });
});
