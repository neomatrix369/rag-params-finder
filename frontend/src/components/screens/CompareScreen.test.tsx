/**
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-66 dashboard - CompareScreen loading, error + retry, empty, populated and abort-on-unmount.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { makeWalkthruRun } from '../../test/helpers/walkthruResults';
import type { CompareResponse } from '../../types';
import CompareScreen from './CompareScreen';

const apiMocks = vi.hoisted(() => ({ getCompare: vi.fn() }));

vi.mock('../../services/apiClient', async () => {
  const actual = await vi.importActual<typeof import('../../services/apiClient')>('../../services/apiClient');
  return { ...actual, ...apiMocks };
});

const populated: CompareResponse = {
  groups: [
    {
      group_id: 'g-a',
      runs: [
        makeWalkthruRun({ run_id: 'r1', group_id: 'g-a', store: 'redis', rank: 1 }),
        makeWalkthruRun({ run_id: 'r2', group_id: 'g-a', store: 'postgres', rank: 2 }),
      ],
    },
  ],
  stores: ['redis', 'postgres'],
  group_count: 1,
  run_count: 2,
  cross_store_group_count: 1,
};

describe('CompareScreen', () => {
  beforeEach(() => {
    apiMocks.getCompare.mockReset();
  });

  it('Given a pending request, when the screen mounts, then it shows loading and fetched once', () => {
    /**
     * Scenario: Fetch happens on mount and a status message covers the wait.
     * Slice: 66 - compare loading state.
     */
    // -- Given --
    apiMocks.getCompare.mockReturnValue(new Promise(() => {}));

    // -- When --
    render(<CompareScreen onBack={() => {}} />);

    // -- Then --
    expect(screen.getByRole('status')).toHaveTextContent('Loading sweep comparison');
    expect(apiMocks.getCompare).toHaveBeenCalledOnce();
  });

  it('Given a failing request, when Retry is clicked, then it refetches and shows the result', async () => {
    /**
     * Scenario: An error is shown with a Retry that recovers.
     * Slice: 66 - compare error state.
     */
    // -- Given --
    apiMocks.getCompare.mockRejectedValueOnce(new Error('boom')).mockResolvedValueOnce(populated);
    render(<CompareScreen onBack={() => {}} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));

    // -- Then --
    expect(await screen.findByTestId('group-g-a')).toBeInTheDocument();
    expect(apiMocks.getCompare).toHaveBeenCalledTimes(2);
  });

  it('Given a non-Error rejection, when it fails, then a generic message is shown', async () => {
    /**
     * Scenario: Unknown rejection values still produce a readable error.
     * Slice: 66 - compare error fallback copy.
     */
    // -- Given --
    apiMocks.getCompare.mockRejectedValue('nope');

    // -- When --
    render(<CompareScreen onBack={() => {}} />);

    // -- Then --
    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to load sweep comparison');
  });

  it('Given zero runs, when loaded, then the empty state shows and no leaderboard', async () => {
    /**
     * Scenario: No completed sweeps yields a plain empty message.
     * Slice: 66 - compare empty state.
     */
    // -- Given --
    apiMocks.getCompare.mockResolvedValue({ groups: [], stores: [], group_count: 0, run_count: 0, cross_store_group_count: 0 });

    // -- When --
    render(<CompareScreen onBack={() => {}} />);

    // -- Then --
    expect(await screen.findByText('No completed sweeps to compare yet')).toBeInTheDocument();
    expect(screen.queryByLabelText('Cross-store leaderboard')).not.toBeInTheDocument();
  });

  it('Given runs, when loaded, then the leaderboard shows with no suggested pick and Back works', async () => {
    /**
     * Scenario: The populated view reuses the leaderboard without suggestion and can select a run.
     * Slice: 66 - compare populated state.
     */
    // -- Given --
    const onBack = vi.fn();
    apiMocks.getCompare.mockResolvedValue(populated);

    // -- When --
    render(<CompareScreen onBack={onBack} />);

    // -- Then --
    expect(await screen.findByLabelText('Cross-store leaderboard')).toBeInTheDocument();
    expect(screen.queryByText('Suggested pick')).not.toBeInTheDocument();
    expect(screen.getByText(/normalised within each group/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Select redis run r1' }));
    expect(screen.getByRole('button', { name: 'Select redis run r1' })).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(screen.getByRole('button', { name: 'Back to experiments' }));
    expect(onBack).toHaveBeenCalledOnce();
  });

  it('Given an in-flight request, when unmounted, then the request is aborted and no error shows', async () => {
    /**
     * Scenario: Leaving the screen aborts the fetch.
     * Slice: 66 - compare abort on unmount.
     */
    // -- Given --
    let signal: AbortSignal | undefined;
    apiMocks.getCompare.mockImplementation((s: AbortSignal) => {
      signal = s;
      return new Promise((_, reject) => s.addEventListener('abort', () => reject(new Error('aborted'))));
    });
    const { unmount } = render(<CompareScreen onBack={() => {}} />);

    // -- When --
    unmount();

    // -- Then --
    await waitFor(() => expect(signal?.aborted).toBe(true));
  });
});
