/**
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 — pause/resume/cancel control visibility and API wiring.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ExperimentControlButtons from './ExperimentControlButtons';

const apiMocks = vi.hoisted(() => ({
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

describe('ExperimentControlButtons', () => {
  beforeEach(() => {
    apiMocks.pauseExperiment.mockReset();
    apiMocks.resumeExperiment.mockReset();
    apiMocks.cancelExperiment.mockReset();
    apiMocks.pauseExperiment.mockResolvedValue({ status: 'paused', message: 'ok' });
    apiMocks.resumeExperiment.mockResolvedValue({ status: 'running', message: 'ok' });
    apiMocks.cancelExperiment.mockResolvedValue({ status: 'cancelled', message: 'ok' });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  it('Given complete status, when rendered, then no controls are shown', () => {
    /**
     * Scenario: Terminal experiments hide pause/resume/cancel.
     * Slice: 44 — frontend coverage gate (ExperimentControlButtons).
     * Given status=complete,
     * When controls render,
     * Then the control group is absent.
     */
    // -- Given / When --
    render(<ExperimentControlButtons experimentId="exp-complete" status="complete" />);

    // -- Then --
    expect(screen.queryByRole('group', { name: 'Experiment controls' })).toBeNull();
  });

  it('Given running status, when Pause is confirmed, then pauseExperiment is called', async () => {
    /**
     * Scenario: Pause control posts to the API after browser confirm.
     * Slice: 44 — frontend coverage gate (ExperimentControlButtons).
     * Given a running experiment and confirm()=true,
     * When Pause is clicked,
     * Then pauseExperiment is invoked with the experiment id.
     */
    // -- Given --
    const onStatusChange = vi.fn();
    render(
      <ExperimentControlButtons
        experimentId="exp-running"
        status="running"
        onStatusChange={onStatusChange}
      />,
    );

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: /^Pause$/ }));

    // -- Then --
    await waitFor(() => {
      expect(apiMocks.pauseExperiment).toHaveBeenCalledWith('exp-running');
    });
    expect(onStatusChange).toHaveBeenCalled();
  });

  it('Given paused status, when Resume is clicked, then resumeExperiment is called', async () => {
    /**
     * Scenario: Resume control posts without a confirm dialog.
     * Slice: 44 — frontend coverage gate (ExperimentControlButtons).
     * Given a paused experiment,
     * When Resume is clicked,
     * Then resumeExperiment is invoked.
     */
    // -- Given --
    render(<ExperimentControlButtons experimentId="exp-paused" status="paused" />);

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: /^Resume$/ }));

    // -- Then --
    await waitFor(() => {
      expect(apiMocks.resumeExperiment).toHaveBeenCalledWith('exp-paused');
    });
  });

  it('Given running status and API error, when Cancel fails, then onError receives the message', async () => {
    /**
     * Scenario: Control failures surface through onError.
     * Slice: 44 — frontend coverage gate (ExperimentControlButtons).
     * Given cancelExperiment rejects,
     * When Cancel is confirmed,
     * Then onError is called with the error message.
     */
    // -- Given --
    const onError = vi.fn();
    apiMocks.cancelExperiment.mockRejectedValueOnce(new Error('cancel blocked'));
    render(
      <ExperimentControlButtons
        experimentId="exp-running"
        status="running"
        onError={onError}
      />,
    );

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: /^Cancel$/ }));

    // -- Then --
    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('cancel blocked');
    });
  });
});
