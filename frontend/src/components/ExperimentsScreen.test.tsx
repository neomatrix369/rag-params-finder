/**
 * Author: RAG Params Finder contributors
 * Created: 2026-07-19
 * Scope: Slice 39 experiment-list lifecycle copy and control visibility.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Experiment } from '../types';
import ExperimentsScreen from './ExperimentsScreen';

const apiMocks = vi.hoisted(() => ({
  getExperiments: vi.fn(),
  getExperimentsWithProgress: vi.fn(),
  getVectorDbStatsGrouped: vi.fn(),
}));

vi.mock('../services/apiClient', async () => {
  const actual = await vi.importActual<typeof import('../services/apiClient')>(
    '../services/apiClient',
  );
  return { ...actual, ...apiMocks };
});

function experiment(status: Experiment['status'], failedCount = 0): Experiment {
  return {
    experiment_id: `experiment-${status}`,
    experiment_name: `${status} sweep`,
    config: {},
    created_at: '2026-07-18T12:00:00Z',
    status,
    run_count: 3,
    failed_count: failedCount,
  };
}

const lifecycleExperiments = [
  experiment('running'),
  experiment('paused'),
  experiment('complete'),
  experiment('partial'),
  experiment('failed', 2),
  experiment('cancelled'),
];

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
      partial: renderedRowPresentation('partial sweep'),
      failed: renderedRowPresentation('failed sweep'),
      cancelled: renderedRowPresentation('cancelled sweep'),
    };
    expect(actualLifecyclePresentation).toEqual(expectedLifecyclePresentation);
  });
});
