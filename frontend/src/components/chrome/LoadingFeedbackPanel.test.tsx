/**
 * Tests for LoadingFeedbackPanel transfer lane and activity feed.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 Phase B — progress bar, indeterminate pulse, themes, feed variants
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import LoadingFeedbackPanel from './LoadingFeedbackPanel';

describe('LoadingFeedbackPanel', () => {
  it('Given known totals mid-transfer, when rendered, then percent and bytes are shown', () => {
    /**
     * Scenario: Determinate payload progress shows percent.
     * Slice: 44 Phase B — LoadingFeedbackPanel
     *
     * Given 50 of 100 bytes received,
     * When the panel renders,
     * Then the progressbar announces 50% transferred.
     */
    // -- Given / When --
    render(
      <LoadingFeedbackPanel
        title="Loading experiments"
        feed={[{ id: '1', text: 'GET /experiments', variant: 'default' }]}
        receivedBytes={50}
        totalBytes={100}
      />,
    );

    // -- Then --
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuetext', '50% transferred');
    expect(screen.getByText('Loading experiments')).toBeInTheDocument();
    expect(screen.getByText('— GET /experiments')).toBeInTheDocument();
  });

  it('Given waiting for first byte, when rendered, then indeterminate lane is shown', () => {
    /**
     * Scenario: Pre-byte stall shows waiting caption.
     * Slice: 44 Phase B — LoadingFeedbackPanel
     *
     * Given receivedBytes null and expectPayloadProgress true,
     * When the panel renders,
     * Then the waiting-for-response valuetext is used.
     */
    // -- Given / When --
    render(
      <LoadingFeedbackPanel
        title="Hydrating"
        subtitle="Please wait"
        footer="Tip"
        feed={[{ id: 'w', text: 'stall', variant: 'warning' }]}
        receivedBytes={null}
        totalBytes={null}
        theme="dark"
      />,
    );

    // -- Then --
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuetext', 'waiting for response');
    expect(screen.getByText('Please wait')).toBeInTheDocument();
    expect(screen.getByText('Tip')).toBeInTheDocument();
    expect(screen.getByText('— stall')).toHaveClass('text-amber-200');
  });

  it('Given zero bytes with known total, when rendered, then reading-body caption appears', () => {
    /**
     * Scenario: Zero-byte start with Content-Length still shows lane.
     * Slice: 44 Phase B — LoadingFeedbackPanel
     *
     * Given 0 of 2048 bytes,
     * When rendered,
     * Then the summary mentions reading body.
     */
    // -- Given / When --
    render(
      <LoadingFeedbackPanel
        title="Download"
        feed={[]}
        receivedBytes={0}
        totalBytes={2048}
      />,
    );

    // -- Then --
    expect(screen.getByText(/reading body/i)).toBeInTheDocument();
  });

  it('Given expectPayloadProgress false and no bytes, when rendered, then payload lane is hidden', () => {
    /**
     * Scenario: Error-only diagnostics omit the transfer lane.
     * Slice: 44 Phase B — LoadingFeedbackPanel
     *
     * Given expectPayloadProgress=false and null bytes,
     * When rendered,
     * Then no progressbar is present.
     */
    // -- Given / When --
    render(
      <LoadingFeedbackPanel
        title="Failed"
        feed={[{ id: 'e', text: 'error', variant: 'default' }]}
        receivedBytes={null}
        totalBytes={null}
        expectPayloadProgress={false}
      />,
    );

    // -- Then --
    expect(screen.queryByRole('progressbar')).toBeNull();
  });

  it('Given unknown total with bytes received, when rendered, then unknown-total caption is shown', () => {
    /**
     * Scenario: Streaming response without Content-Length.
     * Slice: 44 Phase B — LoadingFeedbackPanel
     *
     * Given 512 received and null total,
     * When rendered,
     * Then the caption mentions total unknown.
     */
    // -- Given / When --
    render(
      <LoadingFeedbackPanel
        title="Stream"
        feed={[]}
        receivedBytes={512}
        totalBytes={null}
      />,
    );

    // -- Then --
    expect(screen.getByText(/total unknown/i)).toBeInTheDocument();
  });
});
