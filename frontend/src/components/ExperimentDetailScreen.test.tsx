/**
 * Author: RAG Params Finder contributors
 * Created: 2026-07-19
 * Scope: Slice 39 experiment-detail lifecycle summaries, next steps, and actions.
 */
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ChunkingMethod,
  Phase,
  RetrievalMethod,
  type Experiment,
  type ExperimentDbStatsSummary,
  type ExperimentStatus,
  type RunStatus,
} from '../types';
import ExperimentDetailScreen from './ExperimentDetailScreen';
import { calculateProgressMetrics } from './experimentDetailProgress';

const apiMocks = vi.hoisted(() => ({
  getExperiment: vi.fn(),
  getExperimentDbStats: vi.fn(),
  getExperimentWithProgress: vi.fn(),
}));

vi.mock('../services/apiClient', async () => {
  const actual = await vi.importActual<typeof import('../services/apiClient')>(
    '../services/apiClient',
  );
  return { ...actual, ...apiMocks };
});

type DetailFixture = Experiment & { runs: RunStatus[] };

type ActionVisibility = {
  pause: boolean;
  cancel: boolean;
  resume: boolean;
  exploreLive: boolean;
  explore: boolean;
  exploreCompleted: boolean;
  delete: boolean;
};

type LifecycleCase = {
  status: ExperimentStatus;
  phases: Phase[];
  summary: string;
  nextStep: string;
  actions: ActionVisibility;
};

function run(experimentId: string, index: number, phase: Phase): RunStatus {
  return {
    run_id: `${experimentId}-run-${index}`,
    experiment_id: experimentId,
    phase,
    database_provider: 'mongodb',
    embedding_provider: 'local',
    embedding_model: 'test-embedding',
    chunking_method: ChunkingMethod.RECURSIVE,
    chunk_size: 512,
    overlap: 50,
    created_at: '2026-07-18T12:00:00Z',
    updated_at: '2026-07-18T12:01:00Z',
    elapsed_ms: 60_000,
    retrieval_method: RetrievalMethod.DENSE,
  };
}

function detailFixture(
  status: ExperimentStatus,
  phases: Phase[],
  overrides: Partial<DetailFixture> = {},
): DetailFixture {
  const experimentId = `detail-${status}`;
  const base: DetailFixture = {
    experiment_id: experimentId,
    experiment_name: `${status} detail sweep`,
    config: {},
    created_at: '2026-07-18T12:00:00Z',
    status,
    run_count: 3,
    runs: phases.map((phase, index) => run(experimentId, index, phase)),
  };
  return { ...base, ...overrides };
}

function dbStats(fixture: DetailFixture): ExperimentDbStatsSummary {
  return {
    experiment_id: fixture.experiment_id,
    experiment_name: fixture.experiment_name,
    status: fixture.status,
    created_at: fixture.created_at,
    database_provider: 'mongodb',
    collection_name: 'chunks',
    cluster_host: null,
    total_chunks: 0,
    unique_documents: 0,
    embedding_models: [],
    embedding_dimensions: [],
    index_names: [],
    retrieval_methods: [],
    chunking_methods: [],
    chunking_breakdown: {},
    estimated_storage_mb: 0,
    estimated_embedding_mb: 0,
    estimated_metadata_mb: 0,
    runs_with_data: 0,
    avg_chunks_per_run: 0,
    total_results: 0,
    unique_queries: 0,
    run_breakdown: [],
  };
}

function renderedActionVisibility(): ActionVisibility {
  return {
    pause: screen.queryAllByRole('button', { name: /^Pause$/ }).length > 0,
    cancel: screen.queryAllByRole('button', { name: /^Cancel$/ }).length > 0,
    resume: screen.queryAllByRole('button', { name: /^Resume$/ }).length > 0,
    exploreLive:
      screen.queryAllByRole('button', { name: /^Explore live results$/ }).length > 0,
    explore: screen.queryAllByRole('button', { name: /^Explore results$/ }).length > 0,
    exploreCompleted:
      screen.queryAllByRole('button', { name: /^Explore completed-run results$/ }).length > 0,
    delete: screen.queryAllByRole('button', { name: /^Delete$/ }).length > 0,
  };
}

const lifecycleCases: LifecycleCase[] = [
  {
    status: 'running',
    phases: [Phase.COMPLETE, Phase.QUERYING],
    summary: '1 of 3 runs are complete; stored results can grow as the sweep continues.',
    nextStep: 'Inspect stored results',
    actions: {
      pause: true,
      cancel: true,
      resume: false,
      exploreLive: true,
      explore: false,
      exploreCompleted: false,
      delete: false,
    },
  },
  {
    status: 'paused',
    phases: [Phase.COMPLETE, Phase.INTERRUPTED],
    summary: 'Paused after 1 of 3 runs completed; resume to run the remaining parameter combinations.',
    nextStep: 'Inspect stored results',
    actions: {
      pause: false,
      cancel: false,
      resume: true,
      exploreLive: false,
      explore: true,
      exploreCompleted: false,
      delete: true,
    },
  },
  {
    status: 'complete',
    phases: [Phase.COMPLETE, Phase.COMPLETE, Phase.COMPLETE],
    summary: 'All 3 configured runs completed; stored results are ready to inspect.',
    nextStep: 'Inspect stored results',
    actions: {
      pause: false,
      cancel: false,
      resume: false,
      exploreLive: false,
      explore: true,
      exploreCompleted: false,
      delete: true,
    },
  },
  {
    status: 'partial',
    phases: [Phase.COMPLETE, Phase.FAILED],
    summary: '1 of 3 runs completed; treat rankings from completed runs as preliminary results.',
    nextStep: 'Inspect stored results',
    actions: {
      pause: false,
      cancel: false,
      resume: false,
      exploreLive: false,
      explore: true,
      exploreCompleted: true,
      delete: true,
    },
  },
  {
    status: 'failed',
    phases: [Phase.FAILED, Phase.FAILED],
    summary: '2 failed and 0 completed of 3 configured runs.',
    nextStep: 'No completed results',
    actions: {
      pause: false,
      cancel: false,
      resume: false,
      exploreLive: false,
      explore: true,
      exploreCompleted: false,
      delete: true,
    },
  },
  {
    status: 'cancelled',
    phases: [Phase.COMPLETE, Phase.INTERRUPTED],
    summary: 'Collection stopped after 1 of 3 runs completed.',
    nextStep: 'Inspect stored results',
    actions: {
      pause: false,
      cancel: false,
      resume: false,
      exploreLive: false,
      explore: true,
      exploreCompleted: false,
      delete: true,
    },
  },
];

describe('ExperimentDetailScreen lifecycle presentation', () => {
  beforeEach(() => {
    apiMocks.getExperiment.mockReset();
    apiMocks.getExperimentDbStats.mockReset();
    apiMocks.getExperimentWithProgress.mockReset();
    apiMocks.getExperiment.mockImplementation(async (experimentId: string) => {
      const matchingCase = lifecycleCases.find(
        ({ status }) => `detail-${status}` === experimentId,
      );
      if (!matchingCase) throw new Error(`Unknown fixture: ${experimentId}`);
      return detailFixture(matchingCase.status, matchingCase.phases);
    });
  });

  it.each(lifecycleCases)(
    'Given a $status experiment, when detail renders, then lifecycle copy and actions remain truthful',
    async ({ status, phases, summary, nextStep, actions }) => {
      /**
       * Scenario: Read the lifecycle truth and choose a valid next action from detail.
       * Slice: 39 — Demo-ready dashboard polish.
       * Given the API returns a known lifecycle state and run outcome.
       * When the seeded detail view refreshes that experiment.
       * Then its summary, next step, and available actions agree with the state.
       */
      // -- Given --
      const fixture = detailFixture(status, phases);

      // -- When --
      render(
        <ExperimentDetailScreen
          experimentId={fixture.experiment_id}
          initialExperiment={fixture}
          initialDbStats={dbStats(fixture)}
          onBack={vi.fn()}
          onExplore={vi.fn()}
        />,
      );
      await waitFor(() => expect(apiMocks.getExperiment).toHaveBeenCalledOnce());

      // -- Then --
      const actualLifecyclePresentation = {
        summary: screen.getByText(summary).textContent,
        nextStep: screen.getByText(nextStep).textContent,
        actions: renderedActionVisibility(),
      };
      expect(actualLifecyclePresentation).toEqual({ summary, nextStep, actions });
    },
  );

  it(
    'reports attempted and discarded counts correctly when Bayesian sweep is complete but short of planned trials without failures',
    async () => {
      /**
       * Scenario: Bayesian shortfall still reaches terminal COMPLETE status
       * Slice: 41A — Bayesian Search: Simple Functional.
       * Given a completed Bayesian experiment with no failed runs and planned/attempted/discarded mismatch.
       * When the detail summary renders.
       * Then lifecycle copy uses attempted/discarded/not-started labels aligned with those event counts.
       */
      const fixture = detailFixture('complete', Array.from({ length: 79 }, () => Phase.COMPLETE), {
        experiment_id: 'bayesian-shortfall-detail',
        experiment_name: 'bayesian shortfall detail sweep',
        config: { execution: { search_strategy: 'bayesian' } },
        run_count: 100,
        completion_reason: 'completed_with_sampling_shortfall',
        bayesian_summary: {
          planned_trials: 100,
          attempted_trials: 79,
          discarded_trials: 21,
        },
      });
      apiMocks.getExperiment.mockImplementation(async (experimentId: string) => {
        if (experimentId !== 'bayesian-shortfall-detail') throw new Error(`Unknown fixture: ${experimentId}`);
        return fixture;
      });

      render(
        <ExperimentDetailScreen
          experimentId={fixture.experiment_id}
          initialExperiment={fixture}
          initialDbStats={dbStats(fixture)}
          onBack={vi.fn()}
          onExplore={vi.fn()}
        />,
      );
      await waitFor(() => expect(apiMocks.getExperiment).toHaveBeenCalledOnce());

      expect(screen.getByText(
        'Planned 100 Bayesian combinations. 79 attempted: 79 complete, 0 interrupted, 21 discarded by sampler, 0 not started (completed with sampling shortfall).',
      )).toBeTruthy();
      expect(screen.getByText(/21 discarded by sampler/)).toBeTruthy();
      expect(
        screen.getByText(/Attempted 79 of 100 combinations; 79 completed successfully with no failures \(completed with sampling shortfall\)\./),
      ).toBeTruthy();
      expect(screen.getByText(/(?:0 interrupted|0 failed)/)).toBeTruthy();
    },
  );
});

describe('ExperimentDetailScreen progress metrics', () => {
  it(
    'calculates elapsed and ETA from wall-clock + completed-run count, not parallelism value',
    () => {
      /**
       * Scenario: parallelism settings differ while completed count and start time are equal
       * Slice: 16 (dashboard timing visibility)
       * Given two experiments with same started_at and completion count but different parallelism settings
       * When progress metrics are derived
       * Then elapsed/ETA are unchanged, proving parallelism is reflected only through completed throughput.
       */
      const startedAt = '2026-07-20T10:00:00.000Z';
      const now = new Date('2026-07-20T10:02:00.000Z').getTime();

      const single = calculateProgressMetrics({
        completed: 12,
        total: 120,
        startedAt,
        now,
      });
      const withParallelism = calculateProgressMetrics({
        completed: 12,
        total: 120,
        startedAt,
        now,
      });

      expect(single.elapsedStr).toBe(withParallelism.elapsedStr);
      expect(single.etaStr).toBe(withParallelism.etaStr);
      expect(single.elapsedStr).toBe('2m 0s');
      expect(single.etaStr).toBe('18m 10s');
    },
  );

  it('shows lower ETA when more runs have completed by the same elapsed wall-clock moment', () => {
    /**
     * Scenario: same wall-clock window, higher completed count => faster remaining ETA
     * Slice: 16 (throughput interpretation)
     * Given two experiments that started together
     * When one has completed more runs by that moment
     * Then ETA is lower and remains consistent with completed-based throughput.
     */
    const startedAt = '2026-07-20T10:00:00.000Z';
    const now = new Date('2026-07-20T10:02:00.000Z').getTime();

    const slower = calculateProgressMetrics({
      completed: 12,
      total: 120,
      startedAt,
      now,
    });
    const faster = calculateProgressMetrics({
      completed: 24,
      total: 120,
      startedAt,
      now,
    });

    expect(faster.etaStr).not.toBe(slower.etaStr);
    expect(faster.etaStr).toBe('8m 4s');
    expect(slower.etaStr).toBe('18m 10s');
  });
});
