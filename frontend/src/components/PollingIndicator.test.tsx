/**
 * Tests for PollingIndicator delayed show / hide behavior.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 Phase B — showDelay, minVisible, reserveSpace, tone
 */
import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PollingIndicator from './PollingIndicator';

describe('PollingIndicator', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('Given active poll, when showDelay elapses, then Syncing becomes visible', () => {
    /**
     * Scenario: Indicator appears after showDelayMs.
     * Slice: 44 Phase B — PollingIndicator
     */
    // -- Given --
    render(<PollingIndicator active showDelayMs={100} minVisibleMs={50} />);

    // -- When --
    expect(screen.getByRole('status', { hidden: true })).toHaveAttribute('aria-hidden', 'true');
    act(() => {
      vi.advanceTimersByTime(100);
    });

    // -- Then --
    expect(screen.getByRole('status', { hidden: true })).toHaveAttribute('aria-hidden', 'false');
    expect(screen.getByText('Syncing...')).toBeInTheDocument();
  });

  it('Given inactive and reserveSpace false, when rendered, then nothing is mounted', () => {
    /**
     * Scenario: Non-reserving idle indicator returns null.
     * Slice: 44 Phase B — PollingIndicator
     */
    // -- Given / When --
    const { container } = render(
      <PollingIndicator active={false} reserveSpace={false} tone="dark" />,
    );

    // -- Then --
    expect(container.firstChild).toBeNull();
  });

  it('Given visible indicator, when deactivated, then hide waits for minVisibleMs', () => {
    /**
     * Scenario: Minimum visible time prevents flicker on hide.
     * Slice: 44 Phase B — PollingIndicator
     */
    // -- Given --
    const { rerender } = render(
      <PollingIndicator active showDelayMs={0} minVisibleMs={200} />,
    );
    act(() => {
      vi.advanceTimersByTime(0);
    });
    expect(screen.getByRole('status', { hidden: true })).toHaveAttribute('aria-hidden', 'false');

    // -- When --
    rerender(<PollingIndicator active={false} showDelayMs={0} minVisibleMs={200} />);
    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(screen.getByRole('status', { hidden: true })).toHaveAttribute('aria-hidden', 'false');
    act(() => {
      vi.advanceTimersByTime(100);
    });

    // -- Then --
    expect(screen.getByRole('status', { hidden: true })).toHaveAttribute('aria-hidden', 'true');
  });
});
