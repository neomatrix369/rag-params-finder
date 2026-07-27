/**
 * Author: RAG Params Finder contributors
 * Created: 2026-07-19
 * Scope: Slice 39 experiment-detail lifecycle summaries, next steps, and actions.
 */
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DETAIL_POLL_MS, VECTOR_DB_STATS_POLL_MS } from '../constants';
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
  deleteExperiment: vi.fn(),
  pauseExperiment: vi.fn(),
  resumeExperiment: vi.fn(),
  cancelExperiment: vi.fn(),
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

function run(
  experimentId: string,
  index: number,
  phase: Phase,
  overrides: Partial<RunStatus> = {},
): RunStatus {
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
    ...overrides,
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

function dbStatsResponse(fixture: DetailFixture): { db_stats: ExperimentDbStatsSummary } {
  return { db_stats: dbStats(fixture) };
}

function resetAllApiMocks() {
  apiMocks.getExperiment.mockReset();
  apiMocks.getExperimentDbStats.mockReset();
  apiMocks.getExperimentWithProgress.mockReset();
  apiMocks.deleteExperiment.mockReset();
  apiMocks.pauseExperiment.mockReset();
  apiMocks.resumeExperiment.mockReset();
  apiMocks.cancelExperiment.mockReset();
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

describe('ExperimentDetailScreen delete flow', () => {
  beforeEach(() => {
    resetAllApiMocks();
  });

  it('Given the delete modal is open, when Cancel is clicked, then it closes without deleting', async () => {
    /**
     * Scenario: Cancelling the delete confirmation must not call deleteExperiment.
     * Slice: 44 Phase B — ExperimentDetailScreen ConfirmDeleteModal onClose wiring.
     */
    // -- Given --
    const fixture = detailFixture('complete', [Phase.COMPLETE, Phase.COMPLETE, Phase.COMPLETE]);
    apiMocks.getExperiment.mockResolvedValue(fixture);
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
    fireEvent.click(screen.getByRole('button', { name: /^Delete$/ }));
    expect(screen.getByText('Delete Experiment?')).toBeInTheDocument();

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    // -- Then --
    expect(screen.queryByText('Delete Experiment?')).not.toBeInTheDocument();
    expect(apiMocks.deleteExperiment).not.toHaveBeenCalled();
  });

  it('Given a confirmed delete, when it succeeds, then deleteExperiment is called and onBack fires', async () => {
    /**
     * Scenario: Confirming delete removes the experiment and returns to the list.
     * Slice: 44 Phase B — ExperimentDetailScreen handleDelete success path.
     */
    // -- Given --
    const fixture = detailFixture('complete', [Phase.COMPLETE, Phase.COMPLETE, Phase.COMPLETE]);
    apiMocks.getExperiment.mockResolvedValue(fixture);
    apiMocks.deleteExperiment.mockResolvedValue({ status: 'deleted', message: 'ok' });
    const onBack = vi.fn();
    render(
      <ExperimentDetailScreen
        experimentId={fixture.experiment_id}
        initialExperiment={fixture}
        initialDbStats={dbStats(fixture)}
        onBack={onBack}
        onExplore={vi.fn()}
      />,
    );
    await waitFor(() => expect(apiMocks.getExperiment).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByRole('button', { name: /^Delete$/ }));

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Delete Experiment' }));

    // -- Then --
    await waitFor(() => expect(apiMocks.deleteExperiment).toHaveBeenCalledWith(fixture.experiment_id));
    await waitFor(() => expect(onBack).toHaveBeenCalledOnce());
  });

  it('Given a confirmed delete, when it fails, then an error banner shows the failure and the modal closes', async () => {
    /**
     * Scenario: A delete failure must surface its message without silently failing.
     * Slice: 44 Phase B — ExperimentDetailScreen handleDelete failure path.
     */
    // -- Given --
    const fixture = detailFixture('complete', [Phase.COMPLETE, Phase.COMPLETE, Phase.COMPLETE]);
    apiMocks.getExperiment.mockResolvedValue(fixture);
    apiMocks.deleteExperiment.mockRejectedValue(new Error('delete blocked by server'));
    const onBack = vi.fn();
    render(
      <ExperimentDetailScreen
        experimentId={fixture.experiment_id}
        initialExperiment={fixture}
        initialDbStats={dbStats(fixture)}
        onBack={onBack}
        onExplore={vi.fn()}
      />,
    );
    await waitFor(() => expect(apiMocks.getExperiment).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByRole('button', { name: /^Delete$/ }));

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Delete Experiment' }));

    // -- Then --
    await waitFor(() => expect(screen.getByText('delete blocked by server')).toBeInTheDocument());
    expect(screen.queryByText('Delete Experiment?')).not.toBeInTheDocument();
    expect(onBack).not.toHaveBeenCalled();
  });
});

describe('ExperimentDetailScreen control-button wiring', () => {
  beforeEach(() => {
    resetAllApiMocks();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('Given a running experiment, when Pause succeeds, then refreshDetailAfterControl re-fetches and updates the badge', async () => {
    /**
     * Scenario: A successful pause action re-fetches the experiment and reflects its new status.
     * Slice: 44 Phase B — ExperimentDetailScreen refreshDetailAfterControl wiring (success path).
     */
    // -- Given --
    const runningFixture = detailFixture('running', [Phase.QUERYING]);
    const pausedFixture = detailFixture('paused', [Phase.INTERRUPTED], {
      experiment_id: runningFixture.experiment_id,
      experiment_name: runningFixture.experiment_name,
    });
    apiMocks.getExperiment
      .mockResolvedValueOnce(runningFixture)
      .mockResolvedValueOnce(pausedFixture);
    apiMocks.pauseExperiment.mockResolvedValue({ status: 'paused', message: 'ok' });
    render(
      <ExperimentDetailScreen
        experimentId={runningFixture.experiment_id}
        initialExperiment={runningFixture}
        initialDbStats={dbStats(runningFixture)}
        onBack={vi.fn()}
        onExplore={vi.fn()}
      />,
    );
    await waitFor(() => expect(apiMocks.getExperiment).toHaveBeenCalledTimes(1));

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: /^Pause$/ }));

    // -- Then --
    await waitFor(() => expect(apiMocks.pauseExperiment).toHaveBeenCalledWith(runningFixture.experiment_id));
    await waitFor(() => expect(apiMocks.getExperiment).toHaveBeenCalledTimes(2));
    expect(await screen.findByRole('button', { name: /^Resume$/ })).toBeInTheDocument();
  });

  it('Given a running experiment, when Pause fails, then the error banner shows the failure message', async () => {
    /**
     * Scenario: A failed pause action surfaces its message through onError into the page-level banner.
     * Slice: 44 Phase B — ExperimentDetailScreen onError wiring (control-button failure path).
     */
    // -- Given --
    const runningFixture = detailFixture('running', [Phase.QUERYING]);
    apiMocks.getExperiment.mockResolvedValue(runningFixture);
    apiMocks.pauseExperiment.mockRejectedValue(new Error('pause rejected by server'));
    render(
      <ExperimentDetailScreen
        experimentId={runningFixture.experiment_id}
        initialExperiment={runningFixture}
        initialDbStats={dbStats(runningFixture)}
        onBack={vi.fn()}
        onExplore={vi.fn()}
      />,
    );
    await waitFor(() => expect(apiMocks.getExperiment).toHaveBeenCalledOnce());

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: /^Pause$/ }));

    // -- Then --
    await waitFor(() => expect(screen.getByText('pause rejected by server')).toBeInTheDocument());
  });
});

describe('ExperimentDetailScreen hydration without a seed', () => {
  beforeEach(() => {
    resetAllApiMocks();
  });

  it('Given no seed experiment, when the progress-tracked load succeeds, then the loading panel yields to the detail view', async () => {
    /**
     * Scenario: Navigating directly to a detail URL (no cached seed) loads via getExperimentWithProgress.
     * Slice: 44 Phase B — ExperimentDetailScreen hydrate (no-seed, progress success path).
     */
    // -- Given --
    const fixture = detailFixture('complete', [Phase.COMPLETE]);
    apiMocks.getExperimentWithProgress.mockImplementation(async (_id, onProgress) => {
      onProgress?.({ type: 'message', text: 'Connecting…', variant: 'default' });
      onProgress?.({ type: 'downloading', receivedBytes: 50, totalBytes: 100 });
      return fixture;
    });
    apiMocks.getExperimentDbStats.mockResolvedValue(dbStatsResponse(fixture));

    // -- When --
    render(<ExperimentDetailScreen experimentId={fixture.experiment_id} onBack={vi.fn()} onExplore={vi.fn()} />);

    // -- Then --
    expect(screen.getByText('Loading experiment detail')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(fixture.experiment_name)).toBeInTheDocument());
    expect(apiMocks.getExperimentWithProgress).toHaveBeenCalledOnce();
  });

  it('Given no seed experiment, when the load fails, then the "Could not load" error view renders', async () => {
    /**
     * Scenario: A failed no-seed load must show the dedicated error screen with the failure message.
     * Slice: 44 Phase B — ExperimentDetailScreen hydrate (no-seed, failure path).
     */
    // -- Given --
    apiMocks.getExperimentWithProgress.mockRejectedValue(new Error('experiment not found'));

    // -- When --
    render(<ExperimentDetailScreen experimentId="missing-experiment" onBack={vi.fn()} onExplore={vi.fn()} />);

    // -- Then --
    await waitFor(() => expect(screen.getByText('Could not load')).toBeInTheDocument());
    expect(screen.getByText('experiment not found')).toBeInTheDocument();
  });

  it('Given no seed experiment, when the load is aborted, then no error is shown and the screen renders nothing further', async () => {
    /**
     * Scenario: An aborted no-seed load (e.g. fast unmount/remount) is a silent no-op.
     * Slice: 44 Phase B — ExperimentDetailScreen hydrate (no-seed, AbortError branch).
     */
    // -- Given --
    apiMocks.getExperimentWithProgress.mockRejectedValue(new DOMException('aborted', 'AbortError'));

    // -- When --
    const { container } = render(
      <ExperimentDetailScreen experimentId="aborted-experiment" onBack={vi.fn()} onExplore={vi.fn()} />,
    );

    // -- Then --
    await waitFor(() => expect(screen.queryByText('Loading experiment detail')).not.toBeInTheDocument());
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(container).toBeEmptyDOMElement();
  });
});

describe('ExperimentDetailScreen detail polling', () => {
  beforeEach(() => {
    resetAllApiMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('Given a running experiment, when the poll interval elapses, then the detail view refreshes silently', async () => {
    /**
     * Scenario: The live-poll interval swaps in newer server data while the experiment is running.
     * Slice: 44 Phase B — ExperimentDetailScreen startDetailPollIfRunning (success path).
     */
    // -- Given --
    const runningFixture = detailFixture('running', [Phase.QUERYING]);
    const stillRunningFixture = detailFixture('running', [Phase.QUERYING, Phase.COMPLETE], {
      experiment_id: runningFixture.experiment_id,
      experiment_name: runningFixture.experiment_name,
    });
    apiMocks.getExperiment
      .mockResolvedValueOnce(runningFixture)
      .mockResolvedValueOnce(stillRunningFixture);
    apiMocks.getExperimentDbStats.mockResolvedValue(dbStatsResponse(runningFixture));
    render(
      <ExperimentDetailScreen
        experimentId={runningFixture.experiment_id}
        initialExperiment={runningFixture}
        initialDbStats={dbStats(runningFixture)}
        onBack={vi.fn()}
        onExplore={vi.fn()}
      />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(apiMocks.getExperiment).toHaveBeenCalledTimes(1);

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DETAIL_POLL_MS);
    });

    // -- Then --
    expect(apiMocks.getExperiment).toHaveBeenCalledTimes(2);
    expect(screen.getByText('1 of 3 runs are complete; stored results can grow as the sweep continues.')).toBeInTheDocument();
  });

  it('Given a running experiment, when a poll fails, then a transient error message is shown', async () => {
    /**
     * Scenario: A polling failure surfaces a generic transient-error message without crashing the view.
     * Slice: 44 Phase B — ExperimentDetailScreen startDetailPollIfRunning (failure path).
     */
    // -- Given --
    const runningFixture = detailFixture('running', [Phase.QUERYING]);
    apiMocks.getExperiment
      .mockResolvedValueOnce(runningFixture)
      .mockRejectedValueOnce(new Error('poll connection reset'));
    apiMocks.getExperimentDbStats.mockResolvedValue(dbStatsResponse(runningFixture));
    render(
      <ExperimentDetailScreen
        experimentId={runningFixture.experiment_id}
        initialExperiment={runningFixture}
        initialDbStats={dbStats(runningFixture)}
        onBack={vi.fn()}
        onExplore={vi.fn()}
      />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DETAIL_POLL_MS);
    });

    // -- Then --
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Could not refresh experiment — transient network or server error.',
    );
  });

  it('Given a running experiment, when a poll returns a terminal status, then polling stops', async () => {
    /**
     * Scenario: Once the polled status is terminal, no further poll requests should be made.
     * Slice: 44 Phase B — ExperimentDetailScreen startDetailPollIfRunning (terminal stop branch).
     */
    // -- Given --
    const runningFixture = detailFixture('running', [Phase.QUERYING]);
    const completedFixture = detailFixture('complete', [Phase.COMPLETE], {
      experiment_id: runningFixture.experiment_id,
      experiment_name: runningFixture.experiment_name,
    });
    apiMocks.getExperiment
      .mockResolvedValueOnce(runningFixture)
      .mockResolvedValueOnce(completedFixture);
    apiMocks.getExperimentDbStats.mockResolvedValue(dbStatsResponse(runningFixture));
    render(
      <ExperimentDetailScreen
        experimentId={runningFixture.experiment_id}
        initialExperiment={runningFixture}
        initialDbStats={dbStats(runningFixture)}
        onBack={vi.fn()}
        onExplore={vi.fn()}
      />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DETAIL_POLL_MS);
    });
    expect(apiMocks.getExperiment).toHaveBeenCalledTimes(2);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DETAIL_POLL_MS * 3);
    });

    // -- Then --
    expect(apiMocks.getExperiment).toHaveBeenCalledTimes(2);
  });
});

describe('ExperimentDetailScreen db-stats polling', () => {
  beforeEach(() => {
    resetAllApiMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('Given no initial db stats, when the load starts, then a loading placeholder shows until stats arrive', async () => {
    /**
     * Scenario: Without a seeded db-stats summary, the card shows a loading placeholder first.
     * Slice: 44 Phase B — ExperimentDetailScreen loadDbStats (initial showLoading path).
     */
    // -- Given --
    const fixture = detailFixture('complete', [Phase.COMPLETE]);
    apiMocks.getExperiment.mockResolvedValue(fixture);
    apiMocks.getExperimentDbStats.mockResolvedValue(dbStatsResponse(fixture));

    // -- When --
    render(
      <ExperimentDetailScreen
        experimentId={fixture.experiment_id}
        initialExperiment={fixture}
        onBack={vi.fn()}
        onExplore={vi.fn()}
      />,
    );

    // -- Then --
    expect(screen.getByText('Loading vector database stats…')).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(apiMocks.getExperimentDbStats).toHaveBeenCalledWith(fixture.experiment_id);
  });

  it('Given seeded db stats, when the poll interval elapses, then stats refresh silently', async () => {
    /**
     * Scenario: The slower vector-db stats poll re-fetches without disturbing the rest of the view.
     * Slice: 44 Phase B — ExperimentDetailScreen loadDbStats poll (silent refresh path).
     */
    // -- Given --
    const fixture = detailFixture('complete', [Phase.COMPLETE]);
    apiMocks.getExperiment.mockResolvedValue(fixture);
    apiMocks.getExperimentDbStats.mockResolvedValue(dbStatsResponse(fixture));
    render(
      <ExperimentDetailScreen
        experimentId={fixture.experiment_id}
        initialExperiment={fixture}
        initialDbStats={dbStats(fixture)}
        onBack={vi.fn()}
        onExplore={vi.fn()}
      />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    const callsBefore = apiMocks.getExperimentDbStats.mock.calls.length;

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(VECTOR_DB_STATS_POLL_MS);
    });

    // -- Then --
    expect(apiMocks.getExperimentDbStats.mock.calls.length).toBeGreaterThan(callsBefore);
  });
});

describe('ExperimentDetailScreen metadata and configuration rendering', () => {
  beforeEach(() => {
    resetAllApiMocks();
  });

  it('Given a Voyage-embedding experiment, when rendered, then rate-limit metadata is shown with thousands separators', async () => {
    /**
     * Scenario: Voyage rate-limit fields are provider-gated and large numbers are humanized.
     * Slice: 44 Phase B — ExperimentDetailScreen Environment section (Voyage provider + MetadataItem TPM/RPM formatting).
     */
    // -- Given --
    const fixture = detailFixture('complete', [Phase.COMPLETE], {
      config: { embedding: { provider: 'voyage' } },
      env_params: {
        server_url: 'http://localhost:8001',
        voyage_rpm_limit: 300,
        voyage_tpm_limit: 1_000_000,
        recover_on_boot: false,
      },
    });
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(screen.getByText('300')).toBeInTheDocument();
    expect(screen.getByText('1,000,000')).toBeInTheDocument();
  });

  it('Given a Voyage retrieval provider (not embedding), when rendered, then rate-limit metadata is still shown', async () => {
    /**
     * Scenario: The Voyage-gate is an OR across embedding.provider and retrieval.retrieval_provider.
     * Slice: 44 Phase B — ExperimentDetailScreen Environment section (retrieval-provider Voyage gate).
     */
    // -- Given --
    const fixture = detailFixture('complete', [Phase.COMPLETE], {
      config: { embedding: { provider: 'local' }, retrieval: { retrieval_provider: 'voyage' } },
      env_params: {
        server_url: 'http://localhost:8001',
        voyage_rpm_limit: 120,
        voyage_tpm_limit: 500_000,
        recover_on_boot: true,
      },
    });
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.getByText('500,000')).toBeInTheDocument();
  });

  it('Given a dirty git checkout, when rendered, then the commit metadata is flagged as dirty', async () => {
    /**
     * Scenario: git_dirty must annotate both the header chip and the metadata value.
     * Slice: 44 Phase B — ExperimentDetailScreen Git & Timeline section (git_dirty flag).
     */
    // -- Given --
    const fixture = detailFixture('complete', [Phase.COMPLETE], {
      git_commit: 'abc1234567',
      git_dirty: true,
    });
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(screen.getByText('abc12345 (dirty)')).toBeInTheDocument();
  });

  it('Given data paths, when rendered, then each path is shown by its basename', async () => {
    /**
     * Scenario: Data-source chips must show only the filename, not the full path.
     * Slice: 44 Phase B — ExperimentDetailScreen Data Sources section.
     */
    // -- Given --
    const fixture = detailFixture('complete', [Phase.COMPLETE], {
      data_paths: ['/input_data/papers/report.pdf', '/input_data/notes/summary.md'],
    });
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(screen.getByText('report.pdf')).toBeInTheDocument();
    expect(screen.getByText('summary.md')).toBeInTheDocument();
  });
});

describe('ExperimentDetailScreen sweep-dimensions rendering', () => {
  beforeEach(() => {
    resetAllApiMocks();
  });

  it('Given a Bayesian sweep with paddings and unified retrievers, when rendered, then their dimension badges appear', async () => {
    /**
     * Scenario: Bayesian strategy, paddings, and the unified `retrievers` field each add their own badge.
     * Slice: 44 Phase B — ExperimentDetailScreen Sweep Dimensions (Bayesian/paddings/retrievers badges).
     */
    // -- Given --
    const fixture = detailFixture('complete', [Phase.COMPLETE], {
      config: { execution: { search_strategy: 'bayesian' } },
      sweep_summary: {
        database_provider: 'mongodb',
        embedding_provider: 'voyage',
        models: ['voyage-3.5-lite'],
        chunking_methods: ['recursive'],
        chunk_sizes: [256, 512],
        overlaps: [25, 50],
        paddings: [0, 10],
        retrievers: ['dense', 'hybrid'],
      },
    });
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(screen.getByText('Bayesian Strategy')).toBeInTheDocument();
    expect(screen.getByText('chunk_size × overlap')).toBeInTheDocument();
    expect(screen.getByText('Paddings')).toBeInTheDocument();
    expect(screen.getByText('Retrievers', { selector: 'span' })).toBeInTheDocument();
    expect(screen.getByText('hybrid')).toBeInTheDocument();
  });

  it('Given a legacy sweep summary without unified retrievers, when rendered, then the retrieval-method fallback badges appear', async () => {
    /**
     * Scenario: Older experiments lack `retrievers` and fall back to retrieval_methods + retrieval_provider.
     * Slice: 44 Phase B — ExperimentDetailScreen Sweep Dimensions (legacy retrieval fallback badges).
     */
    // -- Given --
    const fixture = detailFixture('complete', [Phase.COMPLETE], {
      sweep_summary: {
        database_provider: 'mongodb',
        embedding_provider: 'local',
        models: ['all-MiniLM-L6-v2'],
        chunking_methods: ['fixed'],
        chunk_sizes: [512],
        overlaps: [50],
        retrieval_methods: ['sparse', 'hybrid'],
        retrieval_provider: 'voyage',
      },
    });
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(screen.getByText('Retrieval')).toBeInTheDocument();
    expect(screen.getByText('Retrieval Provider')).toBeInTheDocument();
    expect(screen.getByText('sparse')).toBeInTheDocument();
  });

  it('Given a Bayesian sweep with a full bayesian_summary, when rendered, then the Bayesian Summary card shows its metrics', async () => {
    /**
     * Scenario: The Bayesian Summary card surfaces best-trial metrics alongside sampler diagnostics.
     * Slice: 44 Phase B — ExperimentDetailScreen Bayesian Summary CollapsibleCard.
     */
    // -- Given --
    const fixture = detailFixture('complete', [Phase.COMPLETE], {
      config: { execution: { search_strategy: 'bayesian' } },
      run_count: 40,
      grid_equivalent_count: 400,
      sweep_summary: {
        database_provider: 'mongodb',
        embedding_provider: 'local',
        models: ['all-MiniLM-L6-v2'],
        chunking_methods: ['recursive'],
        chunk_sizes: [256, 512],
        overlaps: [25, 50],
      },
      bayesian_summary: {
        best_query_avg_score: 0.87,
        best_chunk_size: 512,
        best_overlap: 25,
        best_embedding_model: 'all-MiniLM-L6-v2',
        attempted_trials: 40,
        discarded_trials: 3,
        termination_reason: 'max_trials_reached',
      },
    });
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(screen.getByText('Bayesian Summary')).toBeInTheDocument();
    expect(screen.getByText('40/400 trials')).toBeInTheDocument();
    expect(screen.getByText('max_trials_reached')).toBeInTheDocument();
  });
});

describe('ExperimentDetailScreen terminal-outcome sections', () => {
  beforeEach(() => {
    resetAllApiMocks();
  });

  it('Given a partial Bayesian sweep, when rendered, then the Bayesian-specific summary sentence is shown', async () => {
    /**
     * Scenario: A partial Bayesian sweep reports attempted/discarded/not-started counts distinctly from grid sweeps.
     * Slice: 44 Phase B — ExperimentDetailScreen sweepSummary (partial + Bayesian branch).
     */
    // -- Given --
    const fixture = detailFixture('partial', [Phase.COMPLETE, Phase.FAILED], {
      config: { execution: { search_strategy: 'bayesian' } },
      run_count: 20,
      bayesian_summary: { planned_trials: 20, attempted_trials: 15, discarded_trials: 2 },
    });
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(
      screen.getByText(
        'Planned 20 Bayesian combinations. 15 attempted: 1 complete, 1 failed, 0 interrupted, 2 discarded by sampler, 3 not started.',
      ),
    ).toBeInTheDocument();
  });

  it('Given a partial Bayesian sweep discarded by sampler pruning, when rendered, then the pruning-specific note is shown', async () => {
    /**
     * Scenario: termination_reason "sampler_candidate_exhaustion" gets a distinct explanatory note.
     * Slice: 44 Phase B — ExperimentDetailScreen partial outcome section (sampler pruning termination_reason branch).
     */
    // -- Given --
    const fixture = detailFixture('partial', [Phase.COMPLETE, Phase.FAILED], {
      config: { execution: { search_strategy: 'bayesian' } },
      run_count: 20,
      bayesian_summary: {
        planned_trials: 20,
        attempted_trials: 15,
        discarded_trials: 2,
        termination_reason: 'sampler_candidate_exhaustion',
      },
    });
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(screen.getByText(/were discarded by Bayesian sampler pruning\./)).toBeInTheDocument();
  });

  it('Given a partial Bayesian sweep discarded for another reason, when rendered, then the generic exploration note is shown', async () => {
    /**
     * Scenario: Any other (or missing) termination_reason falls back to a generic exploration note.
     * Slice: 44 Phase B — ExperimentDetailScreen partial outcome section (non-pruning termination_reason branch).
     */
    // -- Given --
    const fixture = detailFixture('partial', [Phase.COMPLETE, Phase.FAILED], {
      config: { execution: { search_strategy: 'bayesian' } },
      run_count: 20,
      bayesian_summary: { planned_trials: 20, attempted_trials: 15, discarded_trials: 2 },
    });
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(screen.getByText(/discarded while exploring candidate trials\./)).toBeInTheDocument();
  });

  it('Given a cancelled experiment, when rendered, then the cancellation summary panel is shown', async () => {
    /**
     * Scenario: The cancelled-terminal-outcome panel reports how many runs finished before cancellation.
     * Slice: 44 Phase B — ExperimentDetailScreen terminal outcome (cancelled section).
     */
    // -- Given --
    const fixture = detailFixture('cancelled', [Phase.COMPLETE, Phase.INTERRUPTED]);
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(screen.getByText('Experiment Cancelled')).toBeInTheDocument();
    expect(screen.getByText('1 of 3 run(s) completed before cancellation.')).toBeInTheDocument();
  });

  it('Given a paused experiment with never-started runs, when rendered, then the paused panel calls out the remaining count', async () => {
    /**
     * Scenario: The paused panel highlights runs that have not started yet, alongside completed-run counts.
     * Slice: 44 Phase B — ExperimentDetailScreen terminal outcome (paused section, neverStarted > 0 branch).
     */
    // -- Given --
    const fixture = detailFixture('paused', [Phase.COMPLETE, Phase.INTERRUPTED], { run_count: 5 });
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(screen.getByText('Experiment Paused')).toBeInTheDocument();
    expect(screen.getByText('1 of 5 run(s) completed. 3 not started yet.')).toBeInTheDocument();
  });
});

describe('ExperimentDetailScreen runs table pagination', () => {
  beforeEach(() => {
    resetAllApiMocks();
  });

  it('Given more runs than fit on one page, when Next and per-page controls are used, then the visible run rows change', async () => {
    /**
     * Scenario: The runs table paginates independently from the experiments-list screen.
     * Slice: 44 Phase B — ExperimentDetailScreen Pagination (runs table).
     */
    // -- Given --
    const experimentId = 'detail-complete';
    const runs = Array.from({ length: 20 }, (_, i) =>
      run(experimentId, i, Phase.COMPLETE, { embedding_model: `model-${i}` }),
    );
    const fixture: DetailFixture = {
      experiment_id: experimentId,
      experiment_name: 'complete detail sweep',
      config: {},
      created_at: '2026-07-18T12:00:00Z',
      status: 'complete',
      run_count: 20,
      runs,
    };
    apiMocks.getExperiment.mockResolvedValue(fixture);
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
    expect(screen.getByText('model-0')).toBeInTheDocument();
    expect(screen.queryByText('model-15')).not.toBeInTheDocument();

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));

    // -- Then --
    expect(screen.getByText('model-15')).toBeInTheDocument();
    expect(screen.queryByText('model-0')).not.toBeInTheDocument();

    // -- When --
    fireEvent.change(screen.getByLabelText('Per page:'), { target: { value: '25' } });

    // -- Then --
    expect(screen.getByText('model-0')).toBeInTheDocument();
    expect(screen.getByText('model-19')).toBeInTheDocument();
  });
});

describe('ExperimentDetailScreen interrupted and failed run details', () => {
  beforeEach(() => {
    resetAllApiMocks();
  });

  it('Given interrupted runs with and without error messages, when rendered, then each shows the right diagnostic text', async () => {
    /**
     * Scenario: Interrupted runs show their own error_message when present, or a generic fallback otherwise.
     * Slice: 44 Phase B — ExperimentDetailScreen Interrupted Runs section (error_message present/fallback).
     */
    // -- Given --
    const experimentId = 'detail-partial';
    const runs = [
      run(experimentId, 0, Phase.INTERRUPTED, { error_message: 'Timed out waiting for embeddings API' }),
      run(experimentId, 1, Phase.INTERRUPTED, {}),
    ];
    const fixture: DetailFixture = {
      experiment_id: experimentId,
      experiment_name: 'partial detail sweep',
      config: {},
      created_at: '2026-07-18T12:00:00Z',
      status: 'partial',
      run_count: 2,
      runs,
    };
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(screen.getByText('Timed out waiting for embeddings API')).toBeInTheDocument();
    expect(screen.getByText('Run was interrupted before completion')).toBeInTheDocument();
  });

  it('Given failed runs with and without error messages, when rendered, then each shows the right diagnostic text and elapsed time', async () => {
    /**
     * Scenario: Failed runs show their own error_message and elapsed time when available, or fallbacks otherwise.
     * Slice: 44 Phase B — ExperimentDetailScreen Failed Runs section (error_message + elapsed_ms branches).
     */
    // -- Given --
    const experimentId = 'detail-failed';
    const runs = [
      run(experimentId, 0, Phase.FAILED, { error_message: 'Chunker crashed on malformed PDF', elapsed_ms: 4500 }),
      run(experimentId, 1, Phase.FAILED, { error_message: undefined, elapsed_ms: 0 }),
    ];
    const fixture: DetailFixture = {
      experiment_id: experimentId,
      experiment_name: 'failed detail sweep',
      config: {},
      created_at: '2026-07-18T12:00:00Z',
      status: 'failed',
      run_count: 2,
      runs,
    };
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(screen.getByText('Chunker crashed on malformed PDF')).toBeInTheDocument();
    expect(screen.getAllByText(/4\.5s/).length).toBeGreaterThan(0);
    expect(screen.getByText('No error message recorded')).toBeInTheDocument();
  });
});

describe('ExperimentDetailScreen duration formatting edge cases', () => {
  beforeEach(() => {
    resetAllApiMocks();
  });

  it('Given runs that completed in under a second, when the duration is computed, then it is shown in milliseconds', async () => {
    /**
     * Scenario: Sub-second run windows must render as "Nms", not "0s" or a rounded unit string.
     * Slice: 44 Phase B — ExperimentDetailScreen formatDuration (ms < 1000 branch).
     */
    // -- Given --
    const experimentId = 'detail-fast';
    const runs = [
      run(experimentId, 0, Phase.COMPLETE, { created_at: '2026-07-18T12:00:00.000Z', updated_at: '2026-07-18T12:00:00.500Z' }),
    ];
    const fixture: DetailFixture = {
      experiment_id: experimentId,
      experiment_name: 'fast detail sweep',
      config: {},
      created_at: '2026-07-18T12:00:00Z',
      status: 'complete',
      run_count: 1,
      runs,
    };
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(screen.getByText('500ms')).toBeInTheDocument();
  });

  it('Given runs without usable timestamps, when the duration is computed, then it falls back to the experiment-level window or a dash', async () => {
    /**
     * Scenario: When no run has a parseable created_at/updated_at pair, duration falls back to the
     * experiment-level started_at/completed_at, and renders "—" when those are also missing.
     * Slice: 44 Phase B — ExperimentDetailScreen formatDurationFromRuns (fallback + parseSafeTimestamp branches).
     */
    // -- Given --
    const experimentId = 'detail-no-timestamps';
    const runs = [
      run(experimentId, 0, Phase.COMPLETE, { created_at: '', updated_at: 'not-a-date' }),
    ];
    const fixture: DetailFixture = {
      experiment_id: experimentId,
      experiment_name: 'timestampless detail sweep',
      config: {},
      created_at: '2026-07-18T12:00:00Z',
      status: 'complete',
      run_count: 1,
      runs,
    };
    apiMocks.getExperiment.mockResolvedValue(fixture);

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
    expect(screen.getByText('—', { selector: 'div.text-2xl, div.text-lg' })).toBeInTheDocument();
  });
});

describe('ExperimentDetailScreen stall and post-control polling', () => {
  beforeEach(() => {
    resetAllApiMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('Given a stalled no-seed hydrate, when the stall threshold elapses, then Still waiting appears', async () => {
    /**
     * Scenario: Slow detail hydrate surfaces stall feed copy.
     * Slice: 44 Phase B — ExperimentDetailScreen createStallWatcher onWarning
     */
    // -- Given --
    vi.useFakeTimers();
    apiMocks.getExperimentWithProgress.mockImplementationOnce(
      () => new Promise<DetailFixture>(() => undefined),
    );
    render(
      <ExperimentDetailScreen experimentId="detail-stall" onBack={vi.fn()} onExplore={vi.fn()} />,
    );
    expect(screen.getByText('Loading experiment detail')).toBeInTheDocument();

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    // -- Then --
    expect(screen.getByText(/Still waiting/)).toBeInTheDocument();
  });

  it('Given a pending hydrate, when the screen unmounts before settle, then resolve is a no-op', async () => {
    /**
     * Scenario: Late hydrate after unmount is dropped by aliveRef.
     * Slice: 44 Phase B — ExperimentDetailScreen hydrate aliveRef guard
     */
    // -- Given --
    const fixture = detailFixture('complete', [Phase.COMPLETE]);
    let resolveLate: (value: DetailFixture) => void = () => undefined;
    apiMocks.getExperimentWithProgress.mockImplementationOnce(
      () =>
        new Promise<DetailFixture>((resolve) => {
          resolveLate = resolve;
        }),
    );
    const { unmount } = render(
      <ExperimentDetailScreen experimentId={fixture.experiment_id} onBack={vi.fn()} onExplore={vi.fn()} />,
    );

    // -- When --
    unmount();
    await act(async () => {
      resolveLate(fixture);
    });

    // -- Then --
    expect(apiMocks.getExperimentWithProgress).toHaveBeenCalledTimes(1);
  });

  it('Given a paused experiment, when Resume succeeds and status is running, then detail polling restarts', async () => {
    /**
     * Scenario: refreshDetailAfterControl restarts poll when refreshed status is still running.
     * Slice: 44 Phase B — ExperimentDetailScreen refreshDetailAfterControl running branch
     */
    // -- Given --
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const pausedFixture = detailFixture('paused', [Phase.INTERRUPTED]);
    const runningFixture = detailFixture('running', [Phase.QUERYING], {
      experiment_id: pausedFixture.experiment_id,
      experiment_name: pausedFixture.experiment_name,
    });
    apiMocks.getExperiment
      .mockResolvedValueOnce(pausedFixture)
      .mockResolvedValueOnce(runningFixture);
    apiMocks.resumeExperiment.mockResolvedValue({ status: 'running', message: 'ok' });
    apiMocks.getExperimentDbStats.mockResolvedValue(dbStatsResponse(pausedFixture));
    render(
      <ExperimentDetailScreen
        experimentId={pausedFixture.experiment_id}
        initialExperiment={pausedFixture}
        initialDbStats={dbStats(pausedFixture)}
        onBack={vi.fn()}
        onExplore={vi.fn()}
      />,
    );
    await waitFor(() => expect(apiMocks.getExperiment).toHaveBeenCalledTimes(1));

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: /^Resume$/ }));

    // -- Then --
    await waitFor(() => expect(apiMocks.resumeExperiment).toHaveBeenCalledWith(pausedFixture.experiment_id));
    await waitFor(() => expect(apiMocks.getExperiment).toHaveBeenCalledTimes(2));
    expect(await screen.findByRole('button', { name: /^Pause$/ })).toBeInTheDocument();
  });
});
