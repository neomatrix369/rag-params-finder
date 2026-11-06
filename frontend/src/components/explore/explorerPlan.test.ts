/**
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67G-B - the Explorer's planned total and formula come from the server's sweep_plan.
 */
import { describe, expect, it } from 'vitest';
import type { SweepPlan, SweepSummary } from '../../types';
import { explorerPlan, type ExplorerPlanSource } from './explorerPlan';

const summary: SweepSummary = {
  database_provider: 'mongodb',
  embedding_provider: 'local',
  models: ['m'],
  chunking_methods: ['fixed', 'recursive'],
  chunk_sizes: [256, 512],
  overlaps: [20],
  paddings: [],
  retrievers: ['dense', 'sparse'],
};

const plan = (overrides: Partial<SweepPlan> = {}): SweepPlan => ({
  dimension_counts: { models: 1, chunking_methods: 2, chunk_sizes: 2, overlaps: 1, paddings: 1, retrievers: 2 },
  full_grid_count: 8,
  searchable_space: null,
  planned_runs: 8,
  search_strategy: 'grid',
  warnings: [],
  ...overrides,
});

describe('explorerPlan', () => {
  it('Given a grid sweep_plan, when planned, then M is full_grid_count and the formula comes from the summary', () => {
    /**
     * Scenario: the Explorer denominator is the server plan, not the count of completed configs.
     * Slice: 67G-B.
     */
    // -- Given --
    const source: ExplorerPlanSource = { sweep_plan: plan(), sweep_summary: summary, run_count: 3 };

    // -- When --
    const result = explorerPlan(source);

    // -- Then --
    expect(result.plannedTotal).toBe(8);
    expect(result.isBayesian).toBe(false);
    expect(result.note).toBeNull();
    expect(result.formula?.terms.map((t) => t.count)).toEqual([1, 2, 2, 1, 1, 2]);
  });

  it('Given a Bayesian sweep_plan, when planned, then M is planned_runs (not the grid) and the note says the grid is not run in full', () => {
    /**
     * Scenario: Bayesian M = planned trials; the grid product is context only.
     * Slice: 67G-B.
     */
    // -- Given --
    const source: ExplorerPlanSource = {
      sweep_plan: plan({ search_strategy: 'bayesian', planned_runs: 5, full_grid_count: 8, searchable_space: 4 }),
      sweep_summary: summary,
      run_count: 99,
    };

    // -- When --
    const result = explorerPlan(source);

    // -- Then --
    expect(result.plannedTotal).toBe(5);
    expect(result.isBayesian).toBe(true);
    expect(result.note).toMatch(/not run in full/);
  });

  it.each([
    ['grid', { run_count: 12 }, 12, false],
    ['bayesian via config', { run_count: 25, config: { execution: { search_strategy: 'bayesian' } }, bayesian_summary: { planned_trials: 20 } }, 20, true],
    ['bayesian without summary', { run_count: 7, config: { execution: { search_strategy: 'bayesian' } } }, 7, true],
  ] as Array<[string, ExplorerPlanSource, number, boolean]>)(
    'Given an old response without sweep_plan (%s), when planned, then it falls back to what the Detail screen shows',
    (_name, source, expected, bayesian) => {
      /**
       * Scenario: experiments created before 67B carry no plan; the Explorer must agree with the Detail screen.
       * Slice: 67G-B.
       */
      // -- When --
      const result = explorerPlan(source);

      // -- Then --
      expect(result.plannedTotal).toBe(expected);
      expect(result.isBayesian).toBe(bayesian);
      expect(result.formula).toBeNull();
    },
  );

  it('Given nothing is known, when planned, then the total is null rather than a guess', () => {
    /**
     * Scenario: no plan and no run_count means no denominator.
     * Slice: 67G-B.
     */
    // -- When / Then --
    expect(explorerPlan(null).plannedTotal).toBeNull();
    expect(explorerPlan({}).plannedTotal).toBeNull();
  });
});
