/**
 * Tests for ProgressSubtitle wording under the finished-run rule.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67D finding E — failed and interrupted runs count as finished
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { FINISHED_RUN_RULE } from '../experimentDetailProgress';
import ProgressSubtitle from './ProgressSubtitle';

describe('ProgressSubtitle', () => {
  it('Given only complete runs, when rendered, then keeps the "completed" wording', () => {
    /**
     * Scenario: No failed or interrupted runs leaves the original sentence unchanged.
     * Slice: 67D finding E
     */
    // -- Given / When --
    render(<ProgressSubtitle completed={2} total={4} now={0} />);

    // -- Then --
    expect(screen.getByText('2 of 4 runs completed')).toBeInTheDocument();
    expect(screen.queryByText(FINISHED_RUN_RULE)).not.toBeInTheDocument();
  });

  it('Given failed and interrupted runs, when rendered, then states the finished breakdown', () => {
    /**
     * Scenario: Finished count includes failed and interrupted runs, with the split spelled out.
     * Slice: 67D finding E
     */
    // -- Given / When --
    render(<ProgressSubtitle completed={2} failed={1} interrupted={1} total={8} now={0} />);

    // -- Then --
    expect(
      screen.getByText('4 of 8 runs finished (2 complete, 1 failed, 1 interrupted)'),
    ).toBeInTheDocument();
    expect(screen.getByText(FINISHED_RUN_RULE)).toBeInTheDocument();
  });

  it('Given a start time and an injected clock, when rendered, then elapsed and ETA come from that clock', () => {
    /**
     * Scenario: 4 finished runs in 2 minutes of 8 total leaves 4 runs, so ETA is 2 minutes plus the 1% margin.
     * Slice: 67D — clock injected, never read inside the component.
     */
    // -- Given --
    const startedAt = '2026-07-20T10:00:00.000Z';
    const now = new Date('2026-07-20T10:02:00.000Z').getTime();

    // -- When --
    render(<ProgressSubtitle completed={2} failed={1} interrupted={1} total={8} startedAt={startedAt} now={now} />);

    // -- Then --
    expect(screen.getByText('2m 0s')).toBeInTheDocument();
    expect(screen.getByText('2m 1s')).toBeInTheDocument();
  });
});
