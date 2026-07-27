/**
 * Tests for experimentDetailProgress time formatting helpers.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 Phase B — ETA/elapsed and formatTimeWithUnits branches
 */
import { describe, expect, it } from 'vitest';
import { calculateProgressMetrics, formatTimeWithUnits } from './experimentDetailProgress';

describe('experimentDetailProgress', () => {
  it.each([
    { secs: 12, expected: '12s' },
    { secs: 90, expected: '1m 30s' },
    { secs: 3725, expected: '1h 2m 5s' },
  ])('Given $secs seconds, when formatted, then returns $expected', ({ secs, expected }) => {
    /**
     * Scenario: Time formatter covers seconds, minutes, and hours.
     * Slice: 44 Phase B — experimentDetailProgress
     */
    // -- Given / When --
    const actual = formatTimeWithUnits(secs);

    // -- Then --
    expect(actual).toBe(expected);
  });

  it('Given started run with progress, when metrics calculated, then elapsed and eta are set', () => {
    /**
     * Scenario: ETA uses average time per completed run.
     * Slice: 44 Phase B — experimentDetailProgress
     */
    // -- Given --
    const startedAt = new Date(1_000_000).toISOString();
    const now = 1_000_000 + 20_000;

    // -- When --
    const actual = calculateProgressMetrics({
      completed: 2,
      total: 4,
      startedAt,
      now,
    });

    // -- Then --
    expect(actual.elapsedStr).not.toBe('—');
    expect(actual.etaStr).not.toBe('—');
  });

  it('Given no start or zero completed, when metrics calculated, then dashes are returned', () => {
    /**
     * Scenario: Missing start leaves elapsed/eta unknown.
     * Slice: 44 Phase B — experimentDetailProgress
     */
    // -- Given / When --
    const actual = calculateProgressMetrics({ completed: 0, total: 4 });

    // -- Then --
    expect(actual).toEqual({ elapsedStr: '—', etaStr: '—' });
  });
});
