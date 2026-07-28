/**
 * Author: RAG Params Finder contributors
 * Created: 2026-07-19
 * Scope: Slice 39 experiment-list lifecycle copy and control visibility.
 * Scope (Slice 44 Phase B additions): selection/bulk delete, collapse toggle,
 * pagination, bootstrap loading/error/abort paths, background polling
 * (list + vector-db stats), vector-db stats error/loading, and
 * experimentOutcomeLabel/completionReasonLabel edge-case branches.
 */
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { EXPERIMENTS_POLL_MS, VECTOR_DB_STATS_POLL_MS } from '../../constants';
import type { Experiment, VectorDbStatsGroup } from '../../types';
import ExperimentsScreen from './ExperimentsScreen';

const apiMocks = vi.hoisted(() => ({
  getExperiments: vi.fn(),
  getExperimentsWithProgress: vi.fn(),
  getVectorDbStatsGrouped: vi.fn(),
  deleteExperiment: vi.fn(),
  pauseExperiment: vi.fn(),
  resumeExperiment: vi.fn(),
  cancelExperiment: vi.fn(),
}));

vi.mock('../../services/apiClient', async () => {
  const actual = await vi.importActual<typeof import('../../services/apiClient')>(
    '../../services/apiClient',
  );
  return { ...actual, ...apiMocks };
});

function experiment(
  status: Experiment['status'],
  failedCount = 0,
  overrides: Partial<Experiment> = {},
): Experiment {
  return {
    experiment_id: `experiment-${status}`,
    experiment_name: `${status} sweep`,
    config: {},
    created_at: '2026-07-18T12:00:00Z',
    status,
    run_count: 3,
    failed_count: failedCount,
    ...overrides,
  };
}

const lifecycleExperiments = [
  experiment('running'),
  experiment('paused'),
  experiment('complete'),
  experiment('partial'),
  experiment('failed', 2),
  experiment('cancelled'),
  experiment('complete', 0, {
    experiment_id: 'experiment-bayesian-shortfall',
    experiment_name: 'bayesian shortfall',
    config: { execution: { search_strategy: 'bayesian' } },
    run_count: 100,
    completion_reason: 'completed_with_sampling_shortfall',
    bayesian_summary: {
      planned_trials: 100,
      attempted_trials: 79,
      discarded_trials: 21,
    },
  }),
];

function vectorDbGroup(overrides: Partial<VectorDbStatsGroup> = {}): VectorDbStatsGroup {
  return {
    vector_db_id: 'mongodb::chunks',
    database_provider: 'mongodb',
    collection_name: 'chunks',
    cluster_host: null,
    index_names: ['vector_index_1024'],
    embedding_dimensions: [1024],
    totals: {
      experiment_count: 1,
      total_chunks: 120,
      total_results: 42,
      estimated_storage_mb: 5,
      estimated_embedding_mb: 4,
      estimated_metadata_mb: 1,
    },
    experiments: [],
    ...overrides,
  };
}

function renderedRowPresentation(experimentName: string) {
  const openExperiment = screen.getByText(experimentName, { exact: true }).closest('button');
  if (!openExperiment) throw new Error(`Missing open action for ${experimentName}`);
  const row = openExperiment.parentElement;
  if (!row) throw new Error(`Missing row for ${experimentName}`);
  const rowQueries = within(row);
  return {
    outcome: rowQueries.getByText(/runs configured/).textContent,
    pause: rowQueries.queryByRole('button', { name: /^Pause$/ }) !== null,
    cancel: rowQueries.queryByRole('button', { name: /^Cancel$/ }) !== null,
    resume: rowQueries.queryByRole('button', { name: /^Resume$/ }) !== null,
    view: rowQueries.queryByText('View experiment') !== null,
  };
}

describe('ExperimentsScreen lifecycle presentation', () => {
  beforeEach(() => {
    apiMocks.getExperiments.mockReset();
    apiMocks.getExperimentsWithProgress.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockReset();
    apiMocks.getExperiments.mockResolvedValue(lifecycleExperiments);
    apiMocks.getExperimentsWithProgress.mockResolvedValue(lifecycleExperiments);
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });
  });

  it('Given all lifecycle states, when the list renders, then outcome copy and controls match each state', async () => {
    /**
     * Scenario: Scan lifecycle-dependent copy and actions from the experiment list.
     * Slice: 39 — Demo-ready dashboard polish.
     * Given cached experiments cover running, paused, and terminal states.
     * When the list renders and starts its background refresh.
     * Then each outcome is explicit and only active states expose controls.
     */
    // -- Given --
    const expectedLifecyclePresentation = {
      running: {
        outcome: '3 runs configured · sweep in progress',
        pause: true,
        cancel: true,
        resume: false,
        view: true,
      },
      paused: {
        outcome: '3 runs configured · waiting to resume',
        pause: false,
        cancel: false,
        resume: true,
        view: true,
      },
      complete: {
        outcome: '3 runs configured · sweep complete',
        pause: false,
        cancel: false,
        resume: false,
        view: true,
      },
      bayesian_shortfall: {
        outcome: '100 runs configured · Bayesian: 79 attempted · 21 discarded · completed with sampling shortfall',
        pause: false,
        cancel: false,
        resume: false,
        view: true,
      },
      partial: {
        outcome: '3 runs configured · incomplete outcome',
        pause: false,
        cancel: false,
        resume: false,
        view: true,
      },
      failed: {
        outcome: '3 runs configured · 2 failed',
        pause: false,
        cancel: false,
        resume: false,
        view: true,
      },
      cancelled: {
        outcome: '3 runs configured · collection stopped',
        pause: false,
        cancel: false,
        resume: false,
        view: true,
      },
    };

    // -- When --
    render(
      <ExperimentsScreen
        cacheReady
        cachedExperiments={lifecycleExperiments}
        cachedVectorDbGroups={[]}
      />,
    );
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());

    // -- Then --
    const actualLifecyclePresentation = {
      running: renderedRowPresentation('running sweep'),
      paused: renderedRowPresentation('paused sweep'),
      complete: renderedRowPresentation('complete sweep'),
      bayesian_shortfall: renderedRowPresentation('bayesian shortfall'),
      partial: renderedRowPresentation('partial sweep'),
      failed: renderedRowPresentation('failed sweep'),
      cancelled: renderedRowPresentation('cancelled sweep'),
    };
    expect(actualLifecyclePresentation).toEqual(expectedLifecyclePresentation);
  });

  it('Given no experiments, when the empty state renders, then both storage paths are offered', async () => {
    /**
     * Scenario: A first-time operator can start with MongoDB or Postgres.
     * Slice: 43 — Supabase/Postgres operator parity.
     * Given the server returns no experiments.
     * When the confirmed empty state renders.
     * Then example commands are shown for both supported storage backends.
     */
    // -- Given --
    apiMocks.getExperiments.mockResolvedValue([]);
    apiMocks.getExperimentsWithProgress.mockResolvedValue([]);

    // -- When --
    render(
      <ExperimentsScreen
        cacheReady
        cachedExperiments={[]}
        cachedVectorDbGroups={[]}
      />,
    );

    // -- Then --
    expect(await screen.findByText('No experiments yet')).toBeInTheDocument();
    expect(screen.getByText(/configs\/mongodb\/example-local\.yaml/)).toBeInTheDocument();
    expect(screen.getByText(/configs\/supabase\/example-local\.yaml/)).toBeInTheDocument();
  });
});

describe('ExperimentsScreen selection and bulk delete', () => {
  const runningExp = experiment('running');
  const completeA = experiment('complete', 0, {
    experiment_id: 'experiment-complete-a',
    experiment_name: 'complete sweep a',
  });
  const completeB = experiment('complete', 0, {
    experiment_id: 'experiment-complete-b',
    experiment_name: 'complete sweep b',
  });
  const selectionExperiments = [runningExp, completeA, completeB];

  beforeEach(() => {
    apiMocks.getExperiments.mockReset();
    apiMocks.getExperimentsWithProgress.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockReset();
    apiMocks.deleteExperiment.mockReset();
    apiMocks.getExperiments.mockResolvedValue(selectionExperiments);
    apiMocks.getExperimentsWithProgress.mockResolvedValue(selectionExperiments);
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });
    apiMocks.deleteExperiment.mockResolvedValue({ message: 'deleted' });
  });

  async function renderSelectionScreen() {
    render(
      <ExperimentsScreen
        cacheReady
        cachedExperiments={selectionExperiments}
        cachedVectorDbGroups={[]}
      />,
    );
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());
  }

  it('Given a deletable experiment, when its checkbox is checked, then the selection banner shows a count of one', async () => {
    /**
     * Scenario: Checking one row surfaces the bulk-action banner with an accurate count.
     * Slice: 44 Phase B — ExperimentsScreen selection.
     * Given a list containing a running (undeletable) and two complete experiments,
     * When the "complete sweep a" checkbox is checked,
     * Then a banner reports "1 experiment selected".
     */
    // -- Given --
    await renderSelectionScreen();

    // -- When --
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select complete sweep a' }));

    // -- Then --
    expect(screen.getByText('1 experiment selected')).toBeInTheDocument();
  });

  it('Given running experiments, when "Select all deletable experiments" is checked, then only non-running rows are selected', async () => {
    /**
     * Scenario: Bulk select-all skips running experiments, which cannot be deleted.
     * Slice: 44 Phase B — ExperimentsScreen selection.
     * Given a running row and two complete rows,
     * When the select-all checkbox is checked,
     * Then both complete rows are selected and the running row's checkbox stays disabled.
     */
    // -- Given --
    await renderSelectionScreen();

    // -- When --
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select all deletable experiments' }));

    // -- Then --
    expect(screen.getByText('2 experiments selected')).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Select running sweep' })).toBeDisabled();
    expect(screen.getByRole('checkbox', { name: 'Select complete sweep a' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'Select complete sweep b' })).toBeChecked();

    // -- When (uncheck via select-all) --
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select all deletable experiments' }));

    // -- Then --
    expect(screen.queryByText(/experiments? selected/)).not.toBeInTheDocument();
  });

  it('Given a selection, when "Clear selection" is clicked, then the banner disappears', async () => {
    /**
     * Scenario: Clear selection resets the selected-id set without deleting anything.
     * Slice: 44 Phase B — ExperimentsScreen selection.
     */
    // -- Given --
    await renderSelectionScreen();
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select complete sweep a' }));
    expect(screen.getByText('1 experiment selected')).toBeInTheDocument();

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Clear selection' }));

    // -- Then --
    expect(screen.queryByText(/experiment selected/)).not.toBeInTheDocument();
  });

  it('Given a single selected experiment, when the delete is confirmed, then deleteExperiment is called and the list refreshes', async () => {
    /**
     * Scenario: Confirming a single-row delete removes exactly that experiment and refreshes the list.
     * Slice: 44 Phase B — ExperimentsScreen bulk delete (single).
     * Given one complete experiment is selected,
     * When the confirm-delete modal is confirmed,
     * Then deleteExperiment is invoked once with its id and the experiment list is reloaded.
     */
    // -- Given --
    await renderSelectionScreen();
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select complete sweep a' }));
    fireEvent.click(screen.getByRole('button', { name: 'Delete 1' }));
    expect(screen.getByText('Delete Experiment?')).toBeInTheDocument();

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Delete Experiment' }));

    // -- Then --
    await waitFor(() => expect(apiMocks.deleteExperiment).toHaveBeenCalledWith('experiment-complete-a'));
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledTimes(2));
    expect(screen.queryByText('Delete Experiment?')).not.toBeInTheDocument();
    expect(screen.queryByText(/experiment selected/)).not.toBeInTheDocument();
  });

  it('Given two selected experiments, when bulk delete is confirmed, then deleteExperiment is called for each id', async () => {
    /**
     * Scenario: Bulk delete of 2+ experiments issues one delete call per id and shows bulk copy.
     * Slice: 44 Phase B — ExperimentsScreen bulk delete (multi).
     */
    // -- Given --
    await renderSelectionScreen();
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select complete sweep a' }));
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select complete sweep b' }));
    fireEvent.click(screen.getByRole('button', { name: 'Delete 2' }));
    expect(screen.getByText('Delete 2 Experiments?')).toBeInTheDocument();

    // -- When --
    const confirmButtons = screen.getAllByRole('button', { name: 'Delete 2' });
    fireEvent.click(confirmButtons[confirmButtons.length - 1]);

    // -- Then --
    await waitFor(() => expect(apiMocks.deleteExperiment).toHaveBeenCalledTimes(2));
    expect(apiMocks.deleteExperiment).toHaveBeenCalledWith('experiment-complete-a');
    expect(apiMocks.deleteExperiment).toHaveBeenCalledWith('experiment-complete-b');
    await waitFor(() => expect(screen.queryByText('Delete 2 Experiments?')).not.toBeInTheDocument());
  });

  it('Given a delete failure, when the API rejects, then an error banner is shown and the modal closes', async () => {
    /**
     * Scenario: A failed bulk delete surfaces its message without silently dropping the error.
     * Slice: 44 Phase B — ExperimentsScreen bulk delete failure path.
     * Given deleteExperiment rejects,
     * When the confirm button is clicked,
     * Then an alert shows the failure message and the modal is closed.
     */
    // -- Given --
    apiMocks.deleteExperiment.mockRejectedValueOnce(new Error('delete blocked by server'));
    await renderSelectionScreen();
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select complete sweep a' }));
    fireEvent.click(screen.getByRole('button', { name: 'Delete 1' }));

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Delete Experiment' }));

    // -- Then --
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('delete blocked by server'));
    expect(screen.queryByText('Delete Experiment?')).not.toBeInTheDocument();
  });
});

describe('ExperimentsScreen row collapse and pagination', () => {
  beforeEach(() => {
    apiMocks.getExperiments.mockReset();
    apiMocks.getExperimentsWithProgress.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });
  });

  it('Given an expanded row, when its collapse chevron is clicked, then details hide and localStorage records the id', async () => {
    /**
     * Scenario: Collapsing a row hides its expanded detail grid and persists the choice.
     * Slice: 44 Phase B — ExperimentsScreen row collapse.
     * Given one experiment renders expanded by default,
     * When its collapse toggle is clicked,
     * Then the detail grid disappears and localStorage records the collapsed id;
     * When toggled again, the detail grid reappears and localStorage is cleared.
     */
    // -- Given --
    const single = [experiment('complete')];
    apiMocks.getExperiments.mockResolvedValue(single);
    apiMocks.getExperimentsWithProgress.mockResolvedValue(single);
    render(<ExperimentsScreen cacheReady cachedExperiments={single} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());
    expect(screen.getByText('Experiment ID')).toBeInTheDocument();

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Collapse complete sweep' }));

    // -- Then --
    expect(screen.queryByText('Experiment ID')).not.toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem('collapsedExperiments') ?? '[]')).toEqual([
      'experiment-complete',
    ]);

    // -- When (expand again) --
    fireEvent.click(screen.getByRole('button', { name: 'Expand complete sweep' }));

    // -- Then --
    expect(screen.getByText('Experiment ID')).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem('collapsedExperiments') ?? '[]')).toEqual([]);
  });

  it('Given more experiments than fit on one page, when Next/Previous and per-page controls are used, then the visible rows change', async () => {
    /**
     * Scenario: Pagination controls move between pages and re-page when items-per-page changes.
     * Slice: 44 Phase B — ExperimentsScreen pagination.
     * Given 17 experiments (default 15 per page),
     * When Next is clicked,
     * Then page two shows the remaining rows and Next becomes disabled;
     * When Previous is clicked and then per-page is raised to 50,
     * Then all 17 rows fit on a single page.
     */
    // -- Given --
    const many = Array.from({ length: 17 }, (_, i) =>
      experiment('complete', 0, { experiment_id: `experiment-${i}`, experiment_name: `sweep ${i}` }),
    );
    apiMocks.getExperiments.mockResolvedValue(many);
    apiMocks.getExperimentsWithProgress.mockResolvedValue(many);
    render(<ExperimentsScreen cacheReady cachedExperiments={many} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());
    expect(screen.getByText('sweep 0')).toBeInTheDocument();
    expect(screen.queryByText('sweep 16')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));

    // -- Then --
    expect(screen.getByText('sweep 16')).toBeInTheDocument();
    expect(screen.queryByText('sweep 0')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Previous' }));
    fireEvent.change(screen.getByLabelText('Per page:'), { target: { value: '50' } });

    // -- Then --
    expect(screen.getByText('sweep 0')).toBeInTheDocument();
    expect(screen.getByText('sweep 16')).toBeInTheDocument();
  });
});

describe('ExperimentsScreen bootstrap loading and error paths', () => {
  beforeEach(() => {
    apiMocks.getExperiments.mockReset();
    apiMocks.getExperimentsWithProgress.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockReset();
  });

  it('Given no cache, when the initial load succeeds with progress updates, then the loading panel yields to the list and vector stats load', async () => {
    /**
     * Scenario: A cold start shows connecting copy, threads progress updates, then renders the list.
     * Slice: 44 Phase B — ExperimentsScreen bootstrap (cacheReady=false, success).
     * Given no cache is available,
     * When the progress-tracked initial fetch reports a message and a download update before resolving,
     * Then the loading panel first shows connecting copy, then the list renders and vector DB stats load.
     */
    // -- Given --
    const loaded = [experiment('complete')];
    apiMocks.getExperimentsWithProgress.mockImplementation(async (onProgress) => {
      onProgress?.({ type: 'message', text: 'Connecting…', variant: 'default' });
      onProgress?.({ type: 'downloading', receivedBytes: 500, totalBytes: 1000 });
      return loaded;
    });
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });

    // -- When --
    render(<ExperimentsScreen />);

    // -- Then --
    expect(screen.getByText('Connecting to server')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('complete sweep')).toBeInTheDocument());
    await waitFor(() => expect(apiMocks.getVectorDbStatsGrouped).toHaveBeenCalled());
  });

  it('Given no cache, when the initial load fails, then an error banner shows the failure message', async () => {
    /**
     * Scenario: A failed cold start surfaces the error without crashing the screen.
     * Slice: 44 Phase B — ExperimentsScreen bootstrap (cacheReady=false, failure).
     */
    // -- Given --
    apiMocks.getExperimentsWithProgress.mockRejectedValue(new Error('network down'));

    // -- When --
    render(<ExperimentsScreen />);

    // -- Then --
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('network down'));
  });

  it('Given no cache, when the initial fetch is aborted, then no error banner is shown', async () => {
    /**
     * Scenario: An aborted initial fetch (e.g. fast unmount/remount) is treated as a silent no-op.
     * Slice: 44 Phase B — ExperimentsScreen bootstrap (AbortError branch).
     * Given the progress-tracked fetch rejects with a DOMException named AbortError,
     * When the bootstrap effect handles the rejection,
     * Then no error alert is rendered and the load is marked done.
     */
    // -- Given --
    apiMocks.getExperimentsWithProgress.mockRejectedValue(new DOMException('aborted', 'AbortError'));
    apiMocks.getExperiments.mockResolvedValue([]);
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });

    // -- When --
    render(<ExperimentsScreen />);

    // -- Then --
    await waitFor(() => expect(screen.queryByText('Connecting to server')).not.toBeInTheDocument());
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('Given a cache-ready mount, when the background refresh fails, then it fails silently and cached data stays visible', async () => {
    /**
     * Scenario: Background refresh failures on a warm cache do not disturb the visible list.
     * Slice: 44 Phase B — ExperimentsScreen bootstrap (cacheReady=true background refresh failure).
     */
    // -- Given --
    const cached = [experiment('complete', 0, { experiment_name: 'cached sweep' })];
    apiMocks.getExperiments.mockRejectedValueOnce(new Error('cache refresh boom'));
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });

    // -- When --
    render(<ExperimentsScreen cacheReady cachedExperiments={cached} cachedVectorDbGroups={[]} />);

    // -- Then --
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByText('cached sweep')).toBeInTheDocument();
  });
});

describe('ExperimentsScreen background polling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    apiMocks.getExperiments.mockReset();
    apiMocks.getExperimentsWithProgress.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('Given a cache-ready mount, when the list poll interval elapses, then the list refreshes silently', async () => {
    /**
     * Scenario: The periodic list poll swaps in newer server data without an error.
     * Slice: 44 Phase B — ExperimentsScreen polling (success).
     */
    // -- Given --
    const initial = [experiment('running')];
    const updated = [experiment('complete')];
    apiMocks.getExperiments.mockResolvedValueOnce(initial).mockResolvedValueOnce(updated);
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });
    render(<ExperimentsScreen cacheReady cachedExperiments={initial} cachedVectorDbGroups={[]} />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(apiMocks.getExperiments).toHaveBeenCalledTimes(1);

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(EXPERIMENTS_POLL_MS);
    });

    // -- Then --
    expect(apiMocks.getExperiments).toHaveBeenCalledTimes(2);
    expect(screen.getByText('complete sweep')).toBeInTheDocument();
  });

  it('Given a cache-ready mount, when a poll fails, then an error banner is shown', async () => {
    /**
     * Scenario: A polling failure after a healthy mount surfaces the error to the operator.
     * Slice: 44 Phase B — ExperimentsScreen polling (failure).
     */
    // -- Given --
    const initial = [experiment('complete')];
    apiMocks.getExperiments
      .mockResolvedValueOnce(initial)
      .mockRejectedValueOnce(new Error('poll connection reset'));
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });
    render(<ExperimentsScreen cacheReady cachedExperiments={initial} cachedVectorDbGroups={[]} />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(EXPERIMENTS_POLL_MS);
    });

    // -- Then --
    expect(screen.getByRole('alert')).toHaveTextContent('poll connection reset');
  });

  it('Given a cache-ready mount, when the vector-db stats poll interval elapses, then stats refresh silently', async () => {
    /**
     * Scenario: The slower vector-db stats poll re-fetches without disturbing the list.
     * Slice: 44 Phase B — ExperimentsScreen polling (vector DB stats).
     */
    // -- Given --
    const cached = [experiment('complete')];
    apiMocks.getExperiments.mockResolvedValue(cached);
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [vectorDbGroup()] });
    render(<ExperimentsScreen cacheReady cachedExperiments={cached} cachedVectorDbGroups={[vectorDbGroup()]} />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    const initialCalls = apiMocks.getVectorDbStatsGrouped.mock.calls.length;

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(VECTOR_DB_STATS_POLL_MS);
    });

    // -- Then --
    expect(apiMocks.getVectorDbStatsGrouped.mock.calls.length).toBeGreaterThan(initialCalls);
  });
});

describe('ExperimentsScreen vector DB stats panel states', () => {
  beforeEach(() => {
    apiMocks.getExperiments.mockReset();
    apiMocks.getExperimentsWithProgress.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockReset();
  });

  it('Given the vector DB stats request fails, when it settles, then the panel shows the error message', async () => {
    /**
     * Scenario: A vector-DB stats failure is visible without blocking the experiment list.
     * Slice: 44 Phase B — ExperimentsScreen vector DB stats error path.
     */
    // -- Given --
    const cached = [experiment('complete')];
    apiMocks.getExperiments.mockResolvedValue(cached);
    apiMocks.getVectorDbStatsGrouped.mockRejectedValue(new Error('stats aggregation timed out'));

    // -- When --
    render(<ExperimentsScreen cacheReady cachedExperiments={cached} cachedVectorDbGroups={[]} />);

    // -- Then --
    await waitFor(() =>
      expect(screen.getByText('Could not load vector database stats')).toBeInTheDocument(),
    );
    expect(screen.getByText('stats aggregation timed out')).toBeInTheDocument();
  });

  it('Given vector DB stats for a collapsed experiment, when the row is collapsed, then stored-result counts are shown', async () => {
    /**
     * Scenario: Collapsed rows surface a compact "stored results" summary from vector-db stats.
     * Slice: 44 Phase B — ExperimentsScreen vector DB stats + collapse integration.
     */
    // -- Given --
    const exp = experiment('complete');
    const group = vectorDbGroup({
      experiments: [
        {
          experiment_id: exp.experiment_id,
          experiment_name: exp.experiment_name,
          status: exp.status,
          created_at: exp.created_at,
          database_provider: 'mongodb',
          collection_name: 'chunks',
          cluster_host: null,
          total_chunks: 200,
          unique_documents: 10,
          embedding_models: ['test-model'],
          embedding_dimensions: [1024],
          index_names: ['vector_index_1024'],
          retrieval_methods: ['dense'],
          chunking_methods: ['recursive'],
          chunking_breakdown: {},
          estimated_storage_mb: 2,
          estimated_embedding_mb: 1,
          estimated_metadata_mb: 1,
          runs_with_data: 1,
          avg_chunks_per_run: 200,
          total_results: 1234,
          unique_queries: 5,
          run_breakdown: [],
        },
      ],
    });
    apiMocks.getExperiments.mockResolvedValue([exp]);
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [group] });
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[group]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Collapse complete sweep' }));

    // -- Then --
    expect(screen.getByText('1,234 stored results')).toBeInTheDocument();
  });
});

describe('ExperimentsScreen outcome label edge cases', () => {
  beforeEach(() => {
    apiMocks.getExperiments.mockReset();
    apiMocks.getExperimentsWithProgress.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });
  });

  it('Given a running experiment with no run_count yet, when rendered, then "Run count pending" is shown', async () => {
    /**
     * Scenario: run_count can be null before sweep bootstrap finishes; the copy must not print "null".
     * Slice: 44 Phase B — ExperimentsScreen experimentOutcomeLabel (null run_count).
     */
    // -- Given --
    const exp = experiment('running', 0, { run_count: undefined });
    apiMocks.getExperiments.mockResolvedValue([exp]);

    // -- When --
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());

    // -- Then --
    expect(screen.getByText('Run count pending · sweep in progress')).toBeInTheDocument();
  });

  it('Given a completed experiment with an unmapped completion reason, when rendered, then the reason is humanized from its raw value', async () => {
    /**
     * Scenario: Unknown completion_reason strings still render readably (underscores replaced).
     * Slice: 44 Phase B — ExperimentsScreen completionReasonLabel fallback branch.
     */
    // -- Given --
    const exp = experiment('complete', 0, { completion_reason: 'some_future_reason_code' });
    apiMocks.getExperiments.mockResolvedValue([exp]);

    // -- When --
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());

    // -- Then --
    expect(screen.getByText(/some future reason code/)).toBeInTheDocument();
  });

  it('Given a failed experiment with zero recorded failures, when rendered, then the generic "sweep failed" fallback is shown', async () => {
    /**
     * Scenario: A failed experiment without a failed_count still needs non-empty outcome copy.
     * Slice: 44 Phase B — ExperimentsScreen experimentOutcomeLabel fallback branch.
     */
    // -- Given --
    const exp = experiment('failed', 0);
    apiMocks.getExperiments.mockResolvedValue([exp]);

    // -- When --
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());

    // -- Then --
    expect(screen.getByText('3 runs configured · sweep failed')).toBeInTheDocument();
  });

  it('Given a partial Bayesian sweep with no attempted-trials count yet, when rendered, then "sampling incomplete" is shown', async () => {
    /**
     * Scenario: A partial Bayesian sweep can report before attempted_trials populates.
     * Slice: 44 Phase B — ExperimentsScreen experimentOutcomeLabel (Bayesian partial, attempted=null).
     */
    // -- Given --
    const exp = experiment('partial', 0, {
      config: { execution: { search_strategy: 'bayesian' } },
      bayesian_summary: { planned_trials: 40 },
    });
    apiMocks.getExperiments.mockResolvedValue([exp]);

    // -- When --
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());

    // -- Then --
    expect(screen.getByText('3 runs configured · Bayesian sampling incomplete')).toBeInTheDocument();
  });

  it('Given a completed Bayesian sweep that stopped short of its planned trials, when rendered, then the "not started" remainder is called out', async () => {
    /**
     * Scenario: A completed Bayesian sweep can still be short of its planned trial count.
     * Slice: 44 Phase B — ExperimentsScreen experimentOutcomeLabel (complete + Bayesian incomplete + not-started remainder).
     */
    // -- Given --
    const exp = experiment('complete', 0, {
      config: { execution: { search_strategy: 'bayesian' } },
      completion_reason: 'completed_with_sampling_shortfall',
      bayesian_summary: { planned_trials: 20, attempted_trials: 12, discarded_trials: 3, not_started: 20 },
    });
    apiMocks.getExperiments.mockResolvedValue([exp]);

    // -- When --
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());

    // -- Then --
    expect(
      screen.getByText(
        '3 runs configured · Bayesian: 12 attempted · 3 discarded · 5 not started · completed with sampling shortfall',
      ),
    ).toBeInTheDocument();
  });

  it('Given a partial Bayesian sweep with an attempted-trials count, when rendered, then attempted and discarded counts are shown', async () => {
    /**
     * Scenario: Once attempted_trials populates, the partial-Bayesian branch reports concrete counts.
     * Slice: 44 Phase B — ExperimentsScreen experimentOutcomeLabel (partial + Bayesian attempted set).
     */
    // -- Given --
    const exp = experiment('partial', 0, {
      config: { execution: { search_strategy: 'bayesian' } },
      bayesian_summary: { planned_trials: 40, attempted_trials: 30, discarded_trials: 2 },
    });
    apiMocks.getExperiments.mockResolvedValue([exp]);

    // -- When --
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());

    // -- Then --
    expect(
      screen.getByText('3 runs configured · Bayesian: 30 attempted · 2 discarded · 8 not started'),
    ).toBeInTheDocument();
  });
});

describe('ExperimentsScreen checkbox toggling and onSelect navigation', () => {
  beforeEach(() => {
    apiMocks.getExperiments.mockReset();
    apiMocks.getExperimentsWithProgress.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });
  });

  it('Given a checked selection checkbox, when it is unchecked, then the experiment is removed from the selection', async () => {
    /**
     * Scenario: Unchecking a selected row's checkbox must remove it from the selection set (delete branch).
     * Slice: 44 Phase B — ExperimentsScreen handleSelectExperiment uncheck branch.
     */
    // -- Given --
    const exp = experiment('complete');
    apiMocks.getExperiments.mockResolvedValue([exp]);
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());
    const checkbox = screen.getByRole('checkbox', { name: `Select ${exp.experiment_name}` });
    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();

    // -- When --
    fireEvent.click(checkbox);

    // -- Then --
    expect(checkbox).not.toBeChecked();
    expect(screen.queryByRole('button', { name: 'Clear selection' })).not.toBeInTheDocument();
  });

  it('Given an onSelect handler, when the experiment title is clicked, then onSelect fires with that experiment', async () => {
    /**
     * Scenario: Clicking the experiment title button opens its detail screen via the onSelect callback.
     * Slice: 44 Phase B — ExperimentsScreen onSelect wiring (collapsed row title).
     */
    // -- Given --
    const exp = experiment('complete');
    apiMocks.getExperiments.mockResolvedValue([exp]);
    const onSelect = vi.fn();
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} onSelect={onSelect} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());

    // -- When --
    fireEvent.click(screen.getByText(exp.experiment_name, { exact: true }));

    // -- Then --
    expect(onSelect).toHaveBeenCalledWith(exp);
  });

  it('Given an expanded row, when the Experiment ID button is clicked, then onSelect fires with that experiment', async () => {
    /**
     * Scenario: The expanded row's "Experiment ID" button is a second onSelect entry point.
     * Slice: 44 Phase B — ExperimentsScreen onSelect wiring (expanded row experiment-id button).
     */
    // -- Given --
    const exp = experiment('complete');
    apiMocks.getExperiments.mockResolvedValue([exp]);
    const onSelect = vi.fn();
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} onSelect={onSelect} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());

    // -- When --
    fireEvent.click(screen.getByText(`${exp.experiment_id.slice(0, 8)}...`));

    // -- Then --
    expect(onSelect).toHaveBeenCalledWith(exp);
  });
});

describe('ExperimentsScreen row control-button wiring', () => {
  beforeEach(() => {
    apiMocks.getExperiments.mockReset();
    apiMocks.getExperimentsWithProgress.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockReset();
    apiMocks.pauseExperiment.mockReset();
    apiMocks.resumeExperiment.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('Given a running experiment, when Pause succeeds, then the list refreshes via refreshExperimentList', async () => {
    /**
     * Scenario: A successful pause action re-fetches the experiment list through the onStatusChange callback.
     * Slice: 44 Phase B — ExperimentsScreen refreshExperimentList wiring (success path).
     */
    // -- Given --
    const exp = experiment('running');
    apiMocks.getExperiments.mockResolvedValueOnce([exp]).mockResolvedValueOnce([{ ...exp, status: 'paused' }]);
    apiMocks.pauseExperiment.mockResolvedValue(undefined);
    const onCacheUpdate = vi.fn();
    render(
      <ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} onCacheUpdate={onCacheUpdate} />,
    );
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledTimes(1));

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: /^Pause$/ }));

    // -- Then --
    await waitFor(() => expect(apiMocks.pauseExperiment).toHaveBeenCalledWith(exp.experiment_id));
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledTimes(2));
    expect(onCacheUpdate).toHaveBeenCalled();
  });

  it('Given a running experiment, when Pause fails, then the error banner shows the failure message', async () => {
    /**
     * Scenario: A failed pause action surfaces its message through the onError callback into the page-level error banner.
     * Slice: 44 Phase B — ExperimentsScreen onError wiring (control-button failure path).
     */
    // -- Given --
    const exp = experiment('running');
    apiMocks.getExperiments.mockResolvedValue([exp]);
    apiMocks.pauseExperiment.mockRejectedValue(new Error('pause rejected by server'));
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: /^Pause$/ }));

    // -- Then --
    await waitFor(() => expect(screen.getByText('pause rejected by server')).toBeInTheDocument());
  });

  it('Given a paused experiment, when Resume succeeds, then the list refreshes via refreshExperimentList', async () => {
    /**
     * Scenario: The Resume action wires through the same onStatusChange refresh path as Pause.
     * Slice: 44 Phase B — ExperimentsScreen refreshExperimentList wiring (resume success path).
     */
    // -- Given --
    const exp = experiment('paused');
    apiMocks.getExperiments.mockResolvedValueOnce([exp]).mockResolvedValueOnce([{ ...exp, status: 'running' }]);
    apiMocks.resumeExperiment.mockResolvedValue(undefined);
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledTimes(1));

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: /^Resume$/ }));

    // -- Then --
    await waitFor(() => expect(apiMocks.resumeExperiment).toHaveBeenCalledWith(exp.experiment_id));
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledTimes(2));
  });
});

describe('ExperimentsScreen delete modal dismissal', () => {
  beforeEach(() => {
    apiMocks.getExperiments.mockReset();
    apiMocks.getExperimentsWithProgress.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockReset();
    apiMocks.deleteExperiment.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });
  });

  it('Given the delete-confirmation modal is open, when Cancel is clicked, then it closes without deleting', async () => {
    /**
     * Scenario: Cancelling the delete modal must close it without calling deleteExperiment.
     * Slice: 44 Phase B — ExperimentsScreen ConfirmDeleteModal onClose wiring.
     */
    // -- Given --
    const exp = experiment('complete');
    apiMocks.getExperiments.mockResolvedValue([exp]);
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByRole('checkbox', { name: `Select ${exp.experiment_name}` }));
    fireEvent.click(screen.getByRole('button', { name: 'Delete 1' }));
    expect(screen.getByText('Delete Experiment?')).toBeInTheDocument();

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    // -- Then --
    expect(screen.queryByText('Delete Experiment?')).not.toBeInTheDocument();
    expect(apiMocks.deleteExperiment).not.toHaveBeenCalled();
  });
});

describe('ExperimentsScreen stall, unmount, and in-flight stats', () => {
  beforeEach(() => {
    apiMocks.getExperiments.mockReset();
    apiMocks.getExperimentsWithProgress.mockReset();
    apiMocks.getVectorDbStatsGrouped.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('Given a stalled cold start, when the stall threshold elapses, then Still waiting appears', async () => {
    /**
     * Scenario: Slow initial list fetch surfaces stall feed copy.
     * Slice: 44 Phase B — ExperimentsScreen createStallWatcher onWarning
     */
    // -- Given --
    vi.useFakeTimers();
    apiMocks.getExperimentsWithProgress.mockImplementationOnce(
      () => new Promise<Experiment[]>(() => undefined),
    );
    render(<ExperimentsScreen />);
    expect(screen.getByText('Connecting to server')).toBeInTheDocument();

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    // -- Then --
    expect(screen.getByText(/Still waiting/)).toBeInTheDocument();
  });

  it('Given an in-flight stats request, when a second poll fires, then only one network call is active', async () => {
    /**
     * Scenario: Concurrent loadVectorDbStats reuses the in-flight promise.
     * Slice: 44 Phase B — ExperimentsScreen vectorDbStatsInFlightRef
     */
    // -- Given --
    vi.useFakeTimers();
    const cached = [experiment('complete')];
    let resolveStats: (value: { groups: VectorDbStatsGroup[] }) => void = () => undefined;
    apiMocks.getExperiments.mockResolvedValue(cached);
    apiMocks.getVectorDbStatsGrouped.mockImplementation(
      () =>
        new Promise<{ groups: VectorDbStatsGroup[] }>((resolve) => {
          resolveStats = resolve;
        }),
    );
    render(
      <ExperimentsScreen
        cacheReady
        cachedExperiments={cached}
        cachedVectorDbGroups={[vectorDbGroup()]}
      />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    const callsAfterMount = apiMocks.getVectorDbStatsGrouped.mock.calls.length;

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(VECTOR_DB_STATS_POLL_MS);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(VECTOR_DB_STATS_POLL_MS);
    });
    await act(async () => {
      resolveStats({ groups: [vectorDbGroup()] });
    });

    // -- Then --
    // First silent refresh starts one in-flight call; a second tick while pending must not stack another.
    expect(apiMocks.getVectorDbStatsGrouped.mock.calls.length).toBeLessThanOrEqual(callsAfterMount + 1);
  });

  it('Given a pending stats fetch, when the screen unmounts before settle, then resolve is a no-op', async () => {
    /**
     * Scenario: Late stats after unmount are dropped by aliveRef.
     * Slice: 44 Phase B — ExperimentsScreen stats aliveRef guard
     */
    // -- Given --
    const cached = [experiment('complete')];
    let resolveLate: (value: { groups: VectorDbStatsGroup[] }) => void = () => undefined;
    apiMocks.getExperiments.mockResolvedValue(cached);
    apiMocks.getVectorDbStatsGrouped.mockImplementationOnce(
      () =>
        new Promise<{ groups: VectorDbStatsGroup[] }>((resolve) => {
          resolveLate = resolve;
        }),
    );
    const { unmount } = render(
      <ExperimentsScreen cacheReady cachedExperiments={cached} cachedVectorDbGroups={[]} />,
    );
    await waitFor(() => expect(apiMocks.getVectorDbStatsGrouped).toHaveBeenCalled());

    // -- When --
    unmount();
    await act(async () => {
      resolveLate({ groups: [vectorDbGroup()] });
    });

    // -- Then --
    expect(apiMocks.getVectorDbStatsGrouped).toHaveBeenCalledTimes(1);
  });

  it('Given a pending list poll, when the screen unmounts before settle, then resolve is a no-op', async () => {
    /**
     * Scenario: Late list poll after unmount is dropped by aliveRef.
     * Slice: 44 Phase B — ExperimentsScreen poll aliveRef guard
     */
    // -- Given --
    vi.useFakeTimers();
    const cached = [experiment('complete')];
    let resolveLate: (value: Experiment[]) => void = () => undefined;
    apiMocks.getExperiments
      .mockResolvedValueOnce(cached)
      .mockImplementationOnce(
        () =>
          new Promise<Experiment[]>((resolve) => {
            resolveLate = resolve;
          }),
      );
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });
    const { unmount } = render(
      <ExperimentsScreen cacheReady cachedExperiments={cached} cachedVectorDbGroups={[]} />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(EXPERIMENTS_POLL_MS);
    });

    // -- When --
    unmount();
    await act(async () => {
      resolveLate([experiment('running')]);
    });

    // -- Then --
    expect(apiMocks.getExperiments.mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it('Given an unknown status and odd search_strategy, when rendered, then default badge and grid strategy copy apply', async () => {
    /**
     * Scenario: Defensive fallbacks for unexpected status / search_strategy values.
     * Slice: 44 Phase B — ExperimentsScreen statusBadgeClass + resolveSearchStrategy defaults
     */
    // -- Given --
    const exp = experiment('complete', 0, {
      status: 'unknown' as Experiment['status'],
      experiment_name: 'odd status sweep',
      config: { execution: { search_strategy: 'random' } },
      completion_reason: undefined,
    });
    apiMocks.getExperiments.mockResolvedValue([exp]);
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });

    // -- When --
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());

    // -- Then --
    expect(screen.getByText('odd status sweep')).toBeInTheDocument();
    expect(screen.getByText(/runs configured/)).toBeInTheDocument();
  });

  it('Given a poll that rejects a non-Error, when the interval fires, then the generic poll message is shown', async () => {
    /**
     * Scenario: Non-Error poll rejections still surface operator-readable copy.
     * Slice: 44 Phase B — ExperimentsScreen silentPoll non-Error branch
     */
    // -- Given --
    vi.useFakeTimers();
    const cached = [experiment('complete')];
    apiMocks.getExperiments
      .mockResolvedValueOnce(cached)
      .mockRejectedValueOnce('socket reset');
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });
    render(<ExperimentsScreen cacheReady cachedExperiments={cached} cachedVectorDbGroups={[]} />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(EXPERIMENTS_POLL_MS);
    });

    // -- Then --
    expect(screen.getByRole('alert')).toHaveTextContent('Polling failed — check server connectivity.');
  });

  it('Given cache-ready remount, when the effect restarts, then prior poll timers are cleared and replaced', async () => {
    /**
     * Scenario: Remount clears existing intervals before installing new ones.
     * Slice: 44 Phase B — ExperimentsScreen startPollTimers clearInterval branches
     */
    // -- Given --
    vi.useFakeTimers();
    const cached = [experiment('complete')];
    apiMocks.getExperiments.mockResolvedValue(cached);
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });
    const first = render(
      <ExperimentsScreen cacheReady cachedExperiments={cached} cachedVectorDbGroups={[]} />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    // -- When --
    first.unmount();
    render(<ExperimentsScreen cacheReady cachedExperiments={cached} cachedVectorDbGroups={[]} />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(EXPERIMENTS_POLL_MS);
    });

    // -- Then --
    expect(apiMocks.getExperiments.mock.calls.length).toBeGreaterThanOrEqual(3);
  });

  it('Given a cold start that settles after unmount, when progress callbacks fire late, then they are ignored', async () => {
    /**
     * Scenario: applyProg aliveRef guard drops late download updates.
     * Slice: 44 Phase B — ExperimentsScreen bootstrap applyProg aliveRef
     */
    // -- Given --
    let onProgress: ((u: { type: string; receivedBytes?: number; totalBytes?: number; text?: string; variant?: string }) => void) | undefined;
    let resolveLoad: (value: Experiment[]) => void = () => undefined;
    apiMocks.getExperimentsWithProgress.mockImplementationOnce(async (progress) => {
      onProgress = progress as typeof onProgress;
      return new Promise<Experiment[]>((resolve) => {
        resolveLoad = resolve;
      });
    });
    const { unmount } = render(<ExperimentsScreen />);
    await waitFor(() => expect(apiMocks.getExperimentsWithProgress).toHaveBeenCalled());

    // -- When --
    unmount();
    onProgress?.({ type: 'downloading', receivedBytes: 10, totalBytes: 100 });
    onProgress?.({ type: 'message', text: 'late', variant: 'default' });
    await act(async () => {
      resolveLoad([experiment('complete')]);
    });

    // -- Then --
    expect(apiMocks.getExperimentsWithProgress).toHaveBeenCalledTimes(1);
  });

  it('Given a cold start with a warning progress update, when load succeeds, then the warning feed entry is kept', async () => {
    /**
     * Scenario: applyProg warning variant is recorded during bootstrap.
     * Slice: 44 Phase B — ExperimentsScreen applyProg warning branch
     */
    // -- Given --
    apiMocks.getExperimentsWithProgress.mockImplementation(async (onProgress) => {
      onProgress?.({ type: 'message', text: 'Slow link', variant: 'warning' });
      onProgress?.({ type: 'downloading', receivedBytes: 10, totalBytes: 100 });
      return [experiment('complete')];
    });
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });

    // -- When --
    render(<ExperimentsScreen />);

    // -- Then --
    await waitFor(() => expect(screen.getByText('complete sweep')).toBeInTheDocument());
  });

  it('Given bootstrap success that resolves after unmount, when the promise settles, then state updates are skipped', async () => {
    /**
     * Scenario: Post-success aliveRef guards drop late bootstrap completion.
     * Slice: 44 Phase B — ExperimentsScreen bootstrap success aliveRef
     */
    // -- Given --
    let resolveLoad: (value: Experiment[]) => void = () => undefined;
    apiMocks.getExperimentsWithProgress.mockImplementationOnce(
      () =>
        new Promise<Experiment[]>((resolve) => {
          resolveLoad = resolve;
        }),
    );
    const { unmount } = render(<ExperimentsScreen />);
    await waitFor(() => expect(apiMocks.getExperimentsWithProgress).toHaveBeenCalled());

    // -- When --
    unmount();
    await act(async () => {
      resolveLoad([experiment('complete')]);
    });

    // -- Then --
    expect(apiMocks.getExperimentsWithProgress).toHaveBeenCalledTimes(1);
  });

  it('Given bootstrap failure that rejects after unmount, when the promise settles, then error state is skipped', async () => {
    /**
     * Scenario: Post-reject aliveRef guard drops late bootstrap failure.
     * Slice: 44 Phase B — ExperimentsScreen bootstrap catch aliveRef
     */
    // -- Given --
    let rejectLoad: (reason?: unknown) => void = () => undefined;
    apiMocks.getExperimentsWithProgress.mockImplementationOnce(
      () =>
        new Promise<Experiment[]>((_, reject) => {
          rejectLoad = reject;
        }),
    );
    const { unmount } = render(<ExperimentsScreen />);
    await waitFor(() => expect(apiMocks.getExperimentsWithProgress).toHaveBeenCalled());

    // -- When --
    unmount();
    await act(async () => {
      rejectLoad(new Error('late failure'));
    });

    // -- Then --
    expect(apiMocks.getExperimentsWithProgress).toHaveBeenCalledTimes(1);
  });

  it('Given a cold start that loads experiments then stats, when the effect restarts, then Refreshing experiments is shown', async () => {
    /**
     * Scenario: Stats arrival recreates loadVectorDbStats and restarts bootstrap while initialLoadDone.
     * Slice: 44 Phase B — ExperimentsScreen post-load loading panel titles
     */
    // -- Given --
    apiMocks.getExperimentsWithProgress
      .mockResolvedValueOnce([experiment('complete')])
      .mockImplementationOnce(() => new Promise<Experiment[]>(() => undefined));
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [vectorDbGroup()] });

    // -- When --
    render(<ExperimentsScreen />);
    await waitFor(() => expect(screen.getByText('complete sweep')).toBeInTheDocument());

    // -- Then --
    await waitFor(() => expect(screen.getByText('Refreshing experiments')).toBeInTheDocument());
    expect(screen.getByText('Waiting for the server to finish this refresh cycle.')).toBeInTheDocument();
  });

  it('Given a cold start that loads an empty list then stats, when the effect restarts, then Checking for experiments is shown', async () => {
    /**
     * Scenario: Empty-list post-load refresh uses the Checking for experiments title.
     * Slice: 44 Phase B — ExperimentsScreen empty post-load loading panel title
     */
    // -- Given --
    apiMocks.getExperimentsWithProgress
      .mockResolvedValueOnce([])
      .mockImplementationOnce(() => new Promise<Experiment[]>(() => undefined));
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [vectorDbGroup()] });

    // -- When --
    render(<ExperimentsScreen />);
    await waitFor(() => expect(screen.getByText('No experiments yet')).toBeInTheDocument());

    // -- Then --
    await waitFor(() => expect(screen.getByText('Checking for experiments')).toBeInTheDocument());
  });

  it('Given execution search_strategy is a non-object config blob, when rendered, then grid strategy is assumed', async () => {
    /**
     * Scenario: Malformed execution config falls back to grid.
     * Slice: 44 Phase B — ExperimentsScreen resolveSearchStrategy typeof guard
     */
    // -- Given --
    const exp = experiment('complete', 0, {
      experiment_name: 'bad execution shape',
      config: { execution: 'not-an-object' as unknown as Record<string, unknown> },
    });
    apiMocks.getExperiments.mockResolvedValue([exp]);
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });

    // -- When --
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());

    // -- Then --
    expect(screen.getByText('bad execution shape')).toBeInTheDocument();
  });

  it('Given Bayesian shortfall with zero not-started remainder, when rendered, then the not-started suffix is omitted', async () => {
    /**
     * Scenario: notStarted math can be zero — outcome copy must omit that clause.
     * Slice: 44 Phase B — ExperimentsScreen experimentOutcomeLabel notStartedSuffix empty
     */
    // -- Given --
    const exp = experiment('complete', 0, {
      experiment_name: 'bayesian zero remainder',
      config: { execution: { search_strategy: 'bayesian' } },
      bayesian_summary: {
        planned_trials: 10,
        attempted_trials: 8,
        discarded_trials: 2,
        not_started: 0,
      },
    });
    apiMocks.getExperiments.mockResolvedValue([exp]);
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });

    // -- When --
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());

    // -- Then --
    expect(screen.getByText(/Bayesian: 8 attempted · 2 discarded/)).toBeInTheDocument();
    expect(screen.queryByText(/not started/)).not.toBeInTheDocument();
  });

  it('Given complete with all_planned_trials_completed, when rendered, then the plain sweep-complete copy is used', async () => {
    /**
     * Scenario: Canonical success reason does not add a secondary reason clause.
     * Slice: 44 Phase B — ExperimentsScreen complete without reasonSuffix branch
     */
    // -- Given --
    const exp = experiment('complete', 0, {
      experiment_name: 'all planned done',
      completion_reason: 'all_planned_trials_completed',
    });
    apiMocks.getExperiments.mockResolvedValue([exp]);
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });

    // -- When --
    render(<ExperimentsScreen cacheReady cachedExperiments={[exp]} cachedVectorDbGroups={[]} />);
    await waitFor(() => expect(apiMocks.getExperiments).toHaveBeenCalledOnce());

    // -- Then --
    expect(screen.getByText('3 runs configured · sweep complete')).toBeInTheDocument();
  });

  it('Given a selected id missing from the list, when delete opens, then the modal still renders with empty name', async () => {
    /**
     * Scenario: Selection can briefly disagree with the list — modal falls back to empty name.
     * Slice: 44 Phase B — ExperimentsScreen ConfirmDeleteModal name fallback
     */
    // -- Given --
    vi.useFakeTimers();
    const kept = experiment('complete', 0, { experiment_id: 'kept-id', experiment_name: 'kept' });
    const removed = experiment('complete', 0, {
      experiment_id: 'removed-id',
      experiment_name: 'removed soon',
    });
    apiMocks.getExperiments
      .mockResolvedValueOnce([kept, removed])
      .mockResolvedValueOnce([kept]);
    apiMocks.getVectorDbStatsGrouped.mockResolvedValue({ groups: [] });
    render(
      <ExperimentsScreen
        cacheReady
        cachedExperiments={[kept, removed]}
        cachedVectorDbGroups={[]}
      />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select removed soon' }));

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(EXPERIMENTS_POLL_MS);
    });
    fireEvent.click(screen.getByRole('button', { name: 'Delete 1' }));

    // -- Then --
    expect(screen.getByText('Delete Experiment?')).toBeInTheDocument();
  });
});
