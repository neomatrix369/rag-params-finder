/**
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67A — shared FormulaLine rendering.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import FormulaLine from './FormulaLine';

describe('FormulaLine', () => {
  it('Given terms 1 model x 5 methods x 4 retrievers, when rendered, then the product line is printed', () => {
    /**
     * Scenario: product of the terms equals the printed total.
     * Slice: 67A — FormulaLine fixtures.
     */
    // -- Given / When --
    render(
      <FormulaLine
        unit="configuration"
        terms={[
          { count: 1, label: 'model' },
          { count: 5, label: 'chunking method' },
          { count: 4, label: 'retriever' },
        ]}
      />,
    );

    // -- Then --
    expect(screen.getByTestId('formula-line')).toHaveTextContent(
      '1 model × 5 chunking methods × 4 retrievers = 20 configurations',
    );
  });

  it('Given an explicit total of 1, when rendered, then the unit is singular', () => {
    /**
     * Scenario: the explicit total wins and pluralizes once.
     * Slice: 67A — FormulaLine singular unit.
     */
    // -- Given / When --
    render(<FormulaLine unit="configuration" total={1} terms={[{ count: 1, label: 'model' }]} />);

    // -- Then --
    expect(screen.getByTestId('formula-line')).toHaveTextContent('1 model = 1 configuration');
  });
});
