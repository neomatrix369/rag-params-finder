/**
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67G-B - on grid, Bayesian, failed, partial and empty-padding fixtures the Detail
 * Total tile, the Detail header formula and the Explorer planned total are the same number.
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { detailFixture, type DetailFixture } from '../../test/helpers/experimentDetail';
import { buildConfig, buildDetailedResult } from '../../test/helpers/explore';
import { Phase, type ExploreResponse, type SweepPlan, type SweepSummary } from '../../types';
import ExperimentDetailScreen from './ExperimentDetailScreen';
import SearchExplorerScreen from './SearchExplorerScreen';

const apiMocks = vi.hoisted(() => ({
  getExperiment: vi.fn(),
  getExperimentDbStats: vi.fn(),
  getExperimentWithProgress: vi.fn(),
  getExperimentExploreWithProgress: vi.fn(),
  getExperimentExplore: vi.fn(),
  getVectorDbStatsGrouped: vi.fn(),
}));

vi.mock('../../services/apiClient', async () => {
  const actual = await vi.importActual<typeof import('../../services/apiClient')>('../../services/apiClient');
  return { ...actual, ...apiMocks };
});

const summary: SweepSummary = {
  database_provider: 'mongodb',
  embedding_provider: 'local',
  models: ['m1', 'm2'],
  chunking_methods: ['fixed', 'recursive'],
  chunk_sizes: [256, 512],
  overlaps: [20],
  paddings: [],
  retrievers: ['dense'],
};

const gridPlan = (plannedRuns: number): SweepPlan => ({
  dimension_counts: { models: 2, chunking_methods: 2, chunk_sizes: 2, overlaps: 1, paddings: 1, retrievers: 1 },
  full_grid_count: 8,
  searchable_space: null,
  planned_runs: plannedRuns,
  search_strategy: 'grid',
  warnings: [],
});

const repeat = (phase: Phase, times: number): Phase[] => Array<Phase>(times).fill(phase);

interface AgreementCase {
  name: string;
  fixture: DetailFixture;
  planned: number;
  noun: 'runs' | 'trials';
  headerProduct: boolean;
}

const CASES: AgreementCase[] = [
  {
    name: 'complete grid',
    fixture: detailFixture('complete', repeat(Phase.COMPLETE, 8), { run_count: 8, sweep_summary: summary, sweep_plan: gridPlan(8) }),
    planned: 8,
    noun: 'runs',
    headerProduct: true,
  },
  {
    name: 'grid with failed runs',
    fixture: detailFixture('partial', [...repeat(Phase.COMPLETE, 6), ...repeat(Phase.FAILED, 2)], {
      run_count: 8,
      sweep_summary: summary,
      sweep_plan: gridPlan(8),
    }),
    planned: 8,
    noun: 'runs',
    headerProduct: true,
  },
  {
    name: 'partial grid (only 5 runs started)',
    fixture: detailFixture('partial', repeat(Phase.COMPLETE, 5), { run_count: 8, sweep_summary: summary, sweep_plan: gridPlan(8) }),
    planned: 8,
    noun: 'runs',
    headerProduct: true,
  },
  {
    name: 'empty padding list',
    fixture: detailFixture('complete', repeat(Phase.COMPLETE, 8), {
      run_count: 8,
      sweep_summary: { ...summary, paddings: [] },
      sweep_plan: gridPlan(8),
    }),
    planned: 8,
    noun: 'runs',
    headerProduct: true,
  },
  {
    name: 'partial Bayesian whose run_count differs',
    fixture: detailFixture('partial', [...repeat(Phase.COMPLETE, 8), ...repeat(Phase.FAILED, 3), ...repeat(Phase.INTERRUPTED, 2)], {
      config: { execution: { search_strategy: 'bayesian' } },
      run_count: 25,
      sweep_summary: summary,
      sweep_plan: { ...gridPlan(20), search_strategy: 'bayesian', searchable_space: 4 },
      bayesian_summary: { planned_trials: 20, attempted_trials: 13, discarded_trials: 4 },
    }),
    planned: 20,
    noun: 'trials',
    headerProduct: false,
  },
];

const exploreResponse = (experimentId: string): ExploreResponse => ({
  experiment_id: experimentId,
  experiment_name: 'agreement',
  query_count: 1,
  total_matches: 1,
  queries: ['q'],
  best_params: buildConfig(1, { tied_count: 1 }),
  ranked_configs: [buildConfig(1), buildConfig(2)],
  detailed_results: [buildDetailedResult(1)],
});

describe('planned total agreement (Detail header, Total tile, Explorer)', () => {
  beforeEach(() => {
    apiMocks.getExperimentDbStats.mockResolvedValue({ db_stats: null });
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it.each(CASES)(
    'Given the $name fixture, when Detail and Explorer render, then the Total tile and the Explorer M both equal the planned total',
    async ({ fixture, planned, noun, headerProduct }) => {
      /**
       * Scenario: one planned total across screens.
       * Slice: 67G-B - the Explorer reads sweep_plan; the Detail screen reads run_count / planned_trials.
       */
      // -- Given --
      apiMocks.getExperiment.mockResolvedValue(fixture);
      const totalTile = (): string | null | undefined =>
        screen.getByText('Total', { selector: 'div' }).previousElementSibling?.textContent;

      // -- When: Detail --
      render(
        <ExperimentDetailScreen experimentId={fixture.experiment_id} initialExperiment={fixture} onBack={vi.fn()} onExplore={vi.fn()} />,
      );
      await waitFor(() => expect(apiMocks.getExperiment).toHaveBeenCalled());

      // -- Then --
      expect(totalTile()).toBe(String(planned));
      if (headerProduct) {
        expect(
          screen.getByText(`2 models × 2 chunking methods × 2 sizes × 1 overlap × 1 padding × 1 retriever = ${planned} configurations`),
        ).toBeInTheDocument();
      }
      cleanup();

      // -- When: Explorer --
      apiMocks.getExperimentExploreWithProgress.mockResolvedValue(exploreResponse(fixture.experiment_id));
      render(<SearchExplorerScreen experimentId={fixture.experiment_id} onBack={vi.fn()} />);

      // -- Then --
      await screen.findByText(`(2 of ${planned} planned ${noun} have results)`);
    },
  );
});
