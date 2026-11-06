/**
 * Tests for the pure list-screen explanation sentences.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67G - experiments count, pagination, planned runs, failed and Bayesian counts.
 */
import { describe, expect, it } from 'vitest';
import type { Experiment } from '../../../types';
import {
  bayesianCountsExplain,
  experimentsCountExplain,
  failedRunsExplain,
  pageRange,
  paginationExplain,
  plannedRunsExplain,
} from './explainLabels';

const exp = (overrides: Record<string, unknown>): Experiment =>
  ({ experiment_id: 'e1', experiment_name: 'n', status: 'complete', ...overrides }) as unknown as Experiment;

describe('explainLabels', () => {
  it('Given the same inputs, when called twice, then every sentence is identical', () => {
    /**
     * Scenario: Determinism - fixed templates, no clock or randomness.
     * Slice: 67G - list explanations
     */
    // -- Given --
    const build = () => [
      experimentsCountExplain(120),
      paginationExplain(2, 10, 120),
      plannedRunsExplain(exp({ run_count: 12 })),
      failedRunsExplain(2, 12),
      bayesianCountsExplain(20, 12, 3),
    ];

    // -- When / Then --
    expect(build()).toEqual(build());
  });

  it.each([
    [1, 'experiment is'],
    [120, 'experiments are'],
  ])('Given %i stored experiments, when explained, then it says stored experiments, not runs', (total, phrase) => {
    /**
     * Scenario: The headline number is a count of stored experiments, not of runs.
     * Slice: 67G - "120 experiments"
     */
    // -- Given / When --
    const text = experimentsCountExplain(total);

    // -- Then --
    expect(text).toContain(`${total} ${phrase} stored`);
    expect(text).toContain('not a count of runs');
  });

  it.each([
    [1, 10, 120, { start: 1, end: 10 }],
    [2, 10, 120, { start: 11, end: 20 }],
    [3, 50, 120, { start: 101, end: 120 }],
    [1, 25, 7, { start: 1, end: 7 }],
  ])('Given page %i of size %i over %i, when ranged, then it is %j', (page, perPage, total, expected) => {
    /**
     * Scenario: The last page is clamped to the total.
     * Slice: 67G - pagination
     */
    // -- Given / When / Then --
    expect(pageRange(page, perPage, total)).toEqual(expected);
  });

  it('Given page 2 of 10 per page over 120, when explained, then range, total and page size are stated', () => {
    /**
     * Scenario: Pagination counts experiments and states the page size.
     * Slice: 67G - pagination
     */
    // -- Given / When --
    const text = paginationExplain(2, 10, 120);

    // -- Then --
    expect(text).toBe('Showing 11–20 of 120 experiments, 10 per page. Pagination counts experiments, not runs.');
  });

  it('Given a grid experiment, when planned runs are explained, then the run count is the plan', () => {
    /**
     * Scenario: A grid sweep plans run_count runs.
     * Slice: 67G - planned vs executed
     */
    // -- Given / When --
    const text = plannedRunsExplain(exp({ run_count: 12 }));

    // -- Then --
    expect(text).toContain('12 runs are planned');
    expect(text).toContain('not how many have run');
  });

  it('Given one planned grid run, when explained, then the singular is used', () => {
    /**
     * Scenario: Singular noun for one run.
     * Slice: 67G - planned runs
     */
    // -- Given / When / Then --
    expect(plannedRunsExplain(exp({ run_count: 1 }))).toContain('1 run is planned');
  });

  it('Given a run count that is not known yet, when explained, then it says so', () => {
    /**
     * Scenario: run_count is null before the server reports it.
     * Slice: 67G - planned runs
     */
    // -- Given / When / Then --
    expect(plannedRunsExplain(exp({ run_count: null }))).toBe(
      'The server has not reported how many runs this experiment plans yet.',
    );
  });

  it('Given a Bayesian experiment whose run_count differs from planned trials, when explained, then planned trials win', () => {
    /**
     * Scenario: Bayesian rows state planned trials, not run_count.
     * Slice: 67G - planned vs executed
     */
    // -- Given --
    const bayesian = exp({
      run_count: 25,
      config: { execution: { search_strategy: 'bayesian' } },
      bayesian_summary: { planned_trials: 20 },
    });

    // -- When --
    const text = plannedRunsExplain(bayesian);

    // -- Then --
    expect(text).toContain('20 Bayesian trials are planned');
    expect(text).not.toContain('25');
  });

  it('Given one planned Bayesian trial, when explained, then the singular is used', () => {
    /**
     * Scenario: Singular noun for one trial.
     * Slice: 67G - planned trials
     */
    // -- Given --
    const bayesian = exp({
      run_count: 1,
      config: { execution: { search_strategy: 'bayesian' } },
      bayesian_summary: { planned_trials: 1 },
    });

    // -- When / Then --
    expect(plannedRunsExplain(bayesian)).toContain('1 Bayesian trial is planned');
  });

  it.each([
    [2, 12, '2 of the 12 planned runs ended in failure.'],
    [1, 12, '1 of the 12 planned runs ended in failure.'],
    [3, null, '3 runs ended in failure.'],
    [1, null, '1 run ended in failure.'],
  ])('Given %i failed of %s, when explained, then "%s"', (failed, runCount, expected) => {
    /**
     * Scenario: Failed count is stated against the plan when the plan is known.
     * Slice: 67G - "N failed"
     */
    // -- Given / When / Then --
    expect(failedRunsExplain(failed, runCount)).toBe(expected);
  });

  it('Given planned 20, attempted 12, discarded 3, when explained, then not started is subtracted exactly once', () => {
    /**
     * Scenario: 20 - 12 - 3 = 5, never 20 - 12 - 3 - 3.
     * Slice: 67G - double subtraction
     */
    // -- Given / When --
    const text = bayesianCountsExplain(20, 12, 3);

    // -- Then --
    expect(text).toContain('Total 20 = 12 attempted + 3 discarded + 5 not started.');
  });
});
