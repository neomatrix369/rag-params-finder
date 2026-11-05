/**
 * Tests for ProgressSubtitle wording under the finished-run rule.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67D finding E — failed and interrupted runs count as finished
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ProgressSubtitle from './ProgressSubtitle';

describe('ProgressSubtitle', () => {
  it('Given only complete runs, when rendered, then keeps the "completed" wording', () => {
    /**
     * Scenario: No failed or interrupted runs leaves the original sentence unchanged.
     * Slice: 67D finding E
     */
    // -- Given / When --
    render(<ProgressSubtitle completed={2} total={4} />);

    // -- Then --
    expect(screen.getByText('2 of 4 runs completed')).toBeInTheDocument();
  });

  it('Given failed and interrupted runs, when rendered, then states the finished breakdown', () => {
    /**
     * Scenario: Finished count includes failed and interrupted runs, with the split spelled out.
     * Slice: 67D finding E
     */
    // -- Given / When --
    render(<ProgressSubtitle completed={2} failed={1} interrupted={1} total={8} />);

    // -- Then --
    expect(
      screen.getByText('4 of 8 runs finished (2 complete, 1 failed, 1 interrupted)'),
    ).toBeInTheDocument();
  });
});
