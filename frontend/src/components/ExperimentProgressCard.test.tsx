/**
 * Tests for ExperimentProgressCard variants and percent clamping.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 Phase B — compact/default, ringSize override, clamp
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ExperimentProgressCard from './ExperimentProgressCard';

describe('ExperimentProgressCard', () => {
  it('Given default variant, when rendered, then percent is announced', () => {
    /**
     * Scenario: Progress ring exposes aria-valuenow.
     * Slice: 44 Phase B — ExperimentProgressCard
     */
    // -- Given / When --
    render(
      <ExperimentProgressCard title="Progress" subtitle="1 of 2 runs" percent={50} />,
    );

    // -- Then --
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '50');
    expect(screen.getByText('Progress')).toBeInTheDocument();
  });

  it('Given compact variant and overshoot percent, when rendered, then value clamps to 100', () => {
    /**
     * Scenario: Compact card clamps percent above 100.
     * Slice: 44 Phase B — ExperimentProgressCard
     */
    // -- Given / When --
    render(
      <ExperimentProgressCard
        title="Done"
        subtitle={<span>complete</span>}
        percent={150}
        variant="compact"
        ringSize={40}
        className="extra"
      />,
    );

    // -- Then --
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
  });

  it('Given negative percent, when rendered, then value clamps to 0', () => {
    /**
     * Scenario: Negative percent clamps to zero.
     * Slice: 44 Phase B — ExperimentProgressCard
     */
    // -- Given / When --
    render(<ExperimentProgressCard title="Start" subtitle="0 of 2" percent={-5} />);

    // -- Then --
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
  });
});
