/**
 * Tests for experimentDetailProgress time formatting helpers.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 Phase B — ETA/elapsed and formatTimeWithUnits branches
 */
import { describe, expect, it } from 'vitest';
import {
  progressSentence,
  calculateProgressMetrics,
  calculateProgressPercent,
  countFinishedRuns,
  FINISHED_RUN_RULE,
  formatTimeWithUnits,
} from './experimentDetailProgress';

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
    const actual = calculateProgressMetrics({ completed: 0, total: 4, now: 0 });

    // -- Then --
    expect(actual).toEqual({ elapsedStr: '—', etaStr: '—' });
  });

  it('Given failed and interrupted runs, when finished runs counted, then all three phases count', () => {
    /**
     * Scenario: A failed or interrupted run is finished work (it will not complete later).
     * Slice: 67D finding E — progress and ETA rule
     */
    // -- Given --
    const summary = { complete: 3, failed: 2, interrupted: 1 };

    // -- When --
    const actual = countFinishedRuns(summary);

    // -- Then --
    expect(actual).toBe(6);
    expect(FINISHED_RUN_RULE).toMatch(/failed/);
    expect(FINISHED_RUN_RULE).toMatch(/interrupted/);
  });

  it('Given failed and interrupted runs, when percent calculated, then they advance the ring', () => {
    /**
     * Scenario: 2 complete + 1 failed + 1 interrupted of 8 expected is 50%, not 25%.
     * Slice: 67D finding E — progress ring
     */
    // -- Given --
    const summary = { complete: 2, failed: 1, interrupted: 1, expected: 8 };

    // -- When --
    const actual = calculateProgressPercent(summary);

    // -- Then --
    expect(actual).toBe(50);
  });

  it('Given zero expected runs, when percent calculated, then returns 0', () => {
    /**
     * Scenario: Empty plan never divides by zero.
     * Slice: 67D finding E — progress ring
     */
    // -- Given / When --
    const actual = calculateProgressPercent({ complete: 0, failed: 0, interrupted: 0, expected: 0 });

    // -- Then --
    expect(actual).toBe(0);
  });

  it('Given only failed runs, when ETA calculated, then ETA is shown instead of a dash', () => {
    /**
     * Scenario: 2 failed runs in 20s of 4 total leave 2 runs at 10s each, ETA about 20s.
     * Slice: 67D finding E — ETA
     */
    // -- Given --
    const startedAt = new Date(1_000_000).toISOString();
    const now = 1_000_000 + 20_000;

    // -- When --
    const actual = calculateProgressMetrics({ completed: 0, failed: 2, total: 4, startedAt, now });

    // -- Then --
    expect(actual.elapsedStr).toBe('20s');
    expect(actual.etaStr).toBe('20s');
  });

  it('Given complete, failed and interrupted runs, when ETA calculated, then all count as finished', () => {
    /**
     * Scenario: 1 complete + 1 failed + 2 interrupted of 8 in 40s: 10s per run, 4 left, ETA 40.4s.
     * Slice: 67D finding E — ETA
     */
    // -- Given --
    const startedAt = new Date(1_000_000).toISOString();
    const now = 1_000_000 + 40_000;

    // -- When --
    const actual = calculateProgressMetrics({
      completed: 1,
      failed: 1,
      interrupted: 2,
      total: 8,
      startedAt,
      now,
    });

    // -- Then --
    expect(actual.etaStr).toBe('40s');
  });

  it('Given identical input, when metrics and percent are calculated twice, then outputs are identical', () => {
    /**
     * Scenario: Determinism — pure functions of their arguments, clock injected via now.
     * Slice: 67D finding E — standing determinism requirement
     */
    // -- Given --
    const input = {
      completed: 1,
      failed: 1,
      interrupted: 1,
      total: 9,
      startedAt: new Date(5_000_000).toISOString(),
      now: 5_000_000 + 30_000,
    };
    const runs = { complete: 1, failed: 1, interrupted: 1, expected: 9 };

    // -- When --
    const first = calculateProgressMetrics(input);
    const second = calculateProgressMetrics(input);

    // -- Then --
    expect(second).toEqual(first);
    expect(calculateProgressPercent(runs)).toBe(calculateProgressPercent(runs));
    expect(FINISHED_RUN_RULE).toBe(FINISHED_RUN_RULE);
  });
});

describe('progress clamps', () => {
  it('Given finished runs above the expected total, when measured, then percent caps at 100 and ETA never goes negative', () => {
    /**
     * Scenario: an under-reported run_count cannot produce >100% or a negative ETA.
     * Slice: 67D — clamp in the pure helpers.
     */
    // -- Given --
    const startedAt = '2026-07-20T10:00:00.000Z';
    const now = new Date('2026-07-20T10:02:00.000Z').getTime();

    // -- When --
    const percent = calculateProgressPercent({ complete: 9, failed: 1, interrupted: 0, expected: 8 });
    const { etaStr } = calculateProgressMetrics({ completed: 9, failed: 1, total: 8, startedAt, now });

    // -- Then --
    expect(percent).toBe(100);
    expect(etaStr).toBe('0s');
  });
});

describe('progressSentence', () => {
  it('Given only complete runs, when worded, then the "completed" sentence is used', () => {
    /**
     * Scenario: no failed or interrupted runs keeps the original wording.
     * Slice: 67D finding E — wording is a named pure function.
     */
    // -- Given / When / Then --
    expect(progressSentence({ complete: 2, total: 4 })).toBe('2 of 4 runs completed');
  });

  it('Given failed and interrupted runs, when worded, then the "finished" sentence spells out the split', () => {
    /**
     * Scenario: finished count includes failed and interrupted runs.
     * Slice: 67D finding E.
     */
    // -- Given / When / Then --
    expect(progressSentence({ complete: 2, failed: 1, interrupted: 1, total: 8 })).toBe(
      '4 of 8 runs finished (2 complete, 1 failed, 1 interrupted)',
    );
  });
});
