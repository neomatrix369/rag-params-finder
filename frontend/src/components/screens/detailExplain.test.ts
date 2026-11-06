/**
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67G-A - fixed-template explanation sentences for the Detail screen cards.
 */
import { describe, expect, it } from 'vitest';
import {
  bayesianTrialsExplain,
  discardedExplain,
  durationExplain,
  exploreHint,
  failedExplain,
  inProgressExplain,
  interruptedExplain,
  notStartedExplain,
  successfulExplain,
  totalExplain,
} from './detailExplain';

describe('detailExplain', () => {
  it('Given a grid sweep, when Total is explained, then it names planned runs and the number', () => {
    /**
     * Scenario: Total tile on a grid sweep.
     * Slice: 67G-A. Given grid and 120 planned, When explained, Then planned runs and 120 appear.
     */
    // -- Given / When --
    const sentence = totalExplain(false, 120);
    // -- Then --
    expect(sentence).toBe('Planned runs: one run per configuration in the sweep (120 planned).');
  });

  it('Given a Bayesian sweep, when Total is explained, then it names planned trials, not the grid', () => {
    /**
     * Scenario: Total tile on a Bayesian sweep.
     * Slice: 67G-A. Given Bayesian and 20 planned, When explained, Then trials and 20 appear.
     */
    // -- Given / When --
    const sentence = totalExplain(true, 20);
    // -- Then --
    expect(sentence).toBe("Planned trials: the Bayesian sampler's budget (20 trials), not the full grid.");
  });

  it.each([
    [successfulExplain(3), 'Runs executed to the end with results stored: 3.'],
    [failedExplain(2), 'Runs executed that stopped on an error: 2. Counted as finished work in the progress ring and ETA.'],
    [interruptedExplain(1), 'Runs executed that were cut short (cancel, pause or server restart): 1. Counted as finished work in the progress ring and ETA.'],
    [inProgressExplain(4), 'Runs executing right now: 4.'],
    [discardedExplain(5), 'Trials the Bayesian sampler dropped before running: 5. Shown apart from Not started.'],
    [notStartedExplain(false, 7), 'Planned runs not executed yet: 7.'],
    [notStartedExplain(true, 6), 'Planned trials minus attempted minus discarded by the sampler: 6.'],
  ])('Given fixed counts, when explained, then the template is exact (%#)', (actual, expected) => {
    /**
     * Scenario: status tiles share one template per tile.
     * Slice: 67G-A. Given a count, When explained, Then the exact sentence is produced.
     */
    // -- Then --
    expect(actual).toBe(expected);
  });

  it('Given running, paused and finished sweeps, when Duration is explained, then each state says why', () => {
    /**
     * Scenario: Duration is a dash while the sweep is live.
     * Slice: 67G-A. Given each lifecycle state, When explained, Then the reason differs.
     */
    // -- Given / When --
    const live = durationExplain(true);
    const done = durationExplain(false);
    // -- Then --
    expect(live).toBe('Shown once the sweep has stopped; a dash while it runs or is paused.');
    expect(done).toBe('Time from the first run created to the last run updated; falls back to started to completed.');
  });

  it('Given a planned count and a grid size, when the Bayesian trials are explained, then both numbers appear', () => {
    /**
     * Scenario: the "X/Y trials" header.
     * Slice: 67G-A. Given 20 and 98, When explained, Then both numbers and the search rule appear.
     */
    // -- Given / When --
    const sentence = bayesianTrialsExplain(20, 98);
    // -- Then --
    expect(sentence).toBe(
      '20 planned trials out of 98 configurations in the full grid; the sampler searches chunk size × overlap and does not run the whole grid.',
    );
  });

  it('Given no recorded grid size, when the Bayesian trials are explained, then it says so', () => {
    /**
     * Scenario: older experiments without grid_equivalent_count.
     * Slice: 67G-A. Given undefined, When explained, Then the grid size is reported as not recorded.
     */
    // -- Given / When --
    const sentence = bayesianTrialsExplain(20, undefined);
    // -- Then --
    expect(sentence).toBe('20 planned trials; the full-grid size is not recorded.');
  });

  it('Given each lifecycle state, when the Explore hint is requested, then only live and paused have one', () => {
    /**
     * Scenario: replaces the native title on the Explore button.
     * Slice: 67G-A. Given running, paused, finished, Then hint, hint, undefined.
     */
    // -- Then --
    expect(exploreHint(true, false)).toBe('Opens Search Explorer with data stored so far; more results appear as runs finish.');
    expect(exploreHint(false, true)).toBe('Explore results from completed runs; resume to continue the sweep.');
    expect(exploreHint(false, false)).toBeUndefined();
  });

  it('Given the same input, when called twice, then the output is identical', () => {
    /**
     * Scenario: Determinism.
     * Slice: 67G-A. Same input, same sentence.
     */
    // -- Then --
    expect(totalExplain(false, 9)).toBe(totalExplain(false, 9));
  });
});
