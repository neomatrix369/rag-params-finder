/**
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67A — shared FormulaLine rendering and the observed-total contract.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import FormulaLine from './FormulaLine';

const terms = [
  { count: 1, label: 'model' },
  { count: 5, label: 'chunking method' },
  { count: 4, label: 'retriever' },
];

describe('FormulaLine', () => {
  it('Given terms 1 model x 5 methods x 4 retrievers, when rendered, then the line ends in their product', () => {
    /**
     * Scenario: with no observed total the printed total is always the product of the terms.
     * Slice: 67A — FormulaLine derived-total invariant.
     */
    // -- Given / When --
    render(<FormulaLine unit="configuration" terms={terms} />);

    // -- Then --
    expect(
      screen.getByText('1 model × 5 chunking methods × 4 retrievers = 20 configurations'),
    ).toBeInTheDocument();
  });

  it('Given an observed total that differs from the product, when rendered, then the line says observed instead of printing a false equality', () => {
    /**
     * Scenario: the Explorer passes a count seen in results; it must not read as the product.
     * Slice: 67A — observed-total contract (removed in 67D).
     */
    // -- Given / When --
    render(<FormulaLine unit="configuration" terms={terms} observedTotal={17} />);

    // -- Then --
    expect(
      screen.getByText('1 model × 5 chunking methods × 4 retrievers = 17 configurations (observed)'),
    ).toBeInTheDocument();
  });

  it('Given an observed total equal to the product, when rendered, then no observed qualifier appears and the unit is singular for 1', () => {
    /**
     * Scenario: an agreeing observed total is just the product.
     * Slice: 67A — observed-total contract, equal case.
     */
    // -- Given / When --
    render(<FormulaLine unit="configuration" terms={[{ count: 1, label: 'model' }]} observedTotal={1} />);

    // -- Then --
    expect(screen.getByText('1 model = 1 configuration')).toBeInTheDocument();
    expect(screen.queryByText(/observed/)).not.toBeInTheDocument();
  });
});
