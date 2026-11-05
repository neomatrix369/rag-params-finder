/**
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67A — pure builders for the Cartesian "configurations" formula line.
 */
import { describe, expect, it } from 'vitest';
import { BAYESIAN_SWEEP_NOTE, formulaProduct, pluralize, sweepFormulaFromSummary, sweepNote } from './sweepFormula';

describe('pluralize labels in use', () => {
  it.each([
    ['model', 'models'],
    ['chunking method', 'chunking methods'],
    ['size', 'sizes'],
    ['overlap', 'overlaps'],
    ['padding', 'paddings'],
    ['retriever', 'retrievers'],
    ['configuration', 'configurations'],
    ['run', 'runs'],
    ['result', 'results'],
    ['golden query', 'golden queries'],
    ['key', 'keys'],
  ])('Given the label "%s", when pluralized, then it reads "%s" and the singular is unchanged', (label, plural) => {
    /**
     * Scenario: every label the formulas use keeps its plural; "key" is the vowel + y control.
     * Slice: 67E - locks the consonant + y rule against regressions on today's labels.
     */
    // -- Given / When --
    const many = pluralize(2, label);
    const one = pluralize(1, label);

    // -- Then --
    expect(many).toBe(`2 ${plural}`);
    expect(one).toBe(`1 ${label}`);
  });
});

describe('pluralize', () => {
  it('Given a count of 1, when pluralized, then the singular label is kept', () => {
    /**
     * Scenario: one pluralizer serves every term.
     * Slice: 67A — FormulaLine pluralization.
     */
    // -- When / Then --
    expect(pluralize(1, 'model')).toBe('1 model');
    expect(pluralize(5, 'chunking method')).toBe('5 chunking methods');
    expect(pluralize(0, 'padding')).toBe('0 paddings');
  });
});

describe('sweepFormulaFromSummary', () => {
  it('Given 1x5x3x2x1x4 dimensions, when built, then the product is 120 and every term is present', () => {
    /**
     * Scenario: the owner-quoted sweep reads as one Cartesian line that equals the Total tile.
     * Slice: 67A — Detail header formula.
     */
    // -- Given --
    const summary = {
      models: ['m'],
      chunking_methods: ['a', 'b', 'c', 'd', 'e'],
      chunk_sizes: [1, 2, 3],
      overlaps: [0, 1],
      paddings: [0],
      retrievers: ['dense', 'sparse', 'hybrid', 'reranker'],
    };

    // -- When --
    const formula = sweepFormulaFromSummary(summary);

    // -- Then --
    expect(formula.terms.map((t) => t.count)).toEqual([1, 5, 3, 2, 1, 4]);
    expect(formulaProduct(formula.terms)).toBe(120);
    expect(formula.unit).toBe('configuration');
  });

  it('Given empty paddings, when built, then the padding factor is 1, never 0', () => {
    /**
     * Scenario: the backend treats paddings [] as [0], so the UI must too.
     * Slice: 67A — empty-padding oracle.
     */
    // -- Given --
    const summary = {
      models: ['m'],
      chunking_methods: ['a'],
      chunk_sizes: [1],
      overlaps: [0],
      paddings: [] as number[],
      retrievers: ['dense'],
    };

    // -- When --
    const formula = sweepFormulaFromSummary(summary);

    // -- Then --
    expect(formula.terms.find((t) => t.label === 'padding')).toEqual({ count: 1, label: 'padding' });
    expect(formulaProduct(formula.terms)).toBe(1);
  });

  it('Given a legacy summary with retrieval_methods only, when built, then they supply the retriever factor', () => {
    /**
     * Scenario: older experiments lack `retrievers`.
     * Slice: 67A — retrievers ?? retrieval_methods fallback.
     */
    // -- Given --
    const summary = {
      models: ['m'],
      chunking_methods: ['a'],
      chunk_sizes: [1, 2],
      overlaps: [0],
      retrieval_methods: ['dense', 'sparse'],
    };

    // -- When --
    const formula = sweepFormulaFromSummary(summary);

    // -- Then --
    expect(formula.terms.find((t) => t.label === 'retriever')?.count).toBe(2);
    expect(formulaProduct(formula.terms)).toBe(4);
  });

  it('Given neither retrievers nor retrieval_methods, when built, then one default dense retriever is assumed', () => {
    /**
     * Scenario: expand_sweep falls back to a single dense retriever.
     * Slice: 67A — retriever default.
     */
    // -- Given --
    const summary = { models: ['m'], chunking_methods: ['a'], chunk_sizes: [1], overlaps: [0] };

    // -- When --
    const formula = sweepFormulaFromSummary(summary);

    // -- Then --
    expect(formula.terms.find((t) => t.label === 'retriever')).toEqual({ count: 1, label: 'retriever' });
    expect(formulaProduct(formula.terms)).toBe(1);
  });

  it('Given an empty retrievers list and legacy retrieval_methods, when built, then the legacy list supplies the factor', () => {
    /**
     * Scenario: `[] ?? x` would keep the empty list and under-count; the backend migrates legacy methods.
     * Slice: 67A — empty retrievers fallback.
     */
    // -- Given --
    const summary = {
      models: ['m'],
      chunking_methods: ['a'],
      chunk_sizes: [1],
      overlaps: [0],
      retrievers: [] as string[],
      retrieval_methods: ['dense', 'sparse'],
    };

    // -- When --
    const formula = sweepFormulaFromSummary(summary);

    // -- Then --
    expect(formula.terms.find((t) => t.label === 'retriever')?.count).toBe(2);
  });
});

describe('formulaProduct', () => {
  it('Given any set of terms, when multiplied, then the result equals the product of the counts', () => {
    /**
     * Scenario: the displayed total can never drift from its terms.
     * Slice: 67A — FormulaLine invariant.
     */
    // -- When / Then --
    expect(formulaProduct([{ count: 2, label: 'a' }, { count: 3, label: 'b' }])).toBe(6);
    expect(formulaProduct([])).toBe(1);
  });
});

describe('determinism', () => {
  it('Given the same summary, when built twice, then both formulas are deeply equal', () => {
    /**
     * Scenario: numbers and explanations are pure functions of their input.
     * Slice: 67 — standing requirement: deterministic numbers and explanations.
     */
    // -- Given --
    const summary = {
      models: ['m'],
      chunking_methods: ['a', 'b'],
      chunk_sizes: [1, 2, 3],
      overlaps: [0],
      retrievers: ['dense', 'hybrid'],
    };

    // -- When --
    const first = sweepFormulaFromSummary(summary);
    const second = sweepFormulaFromSummary(structuredClone(summary));

    // -- Then --
    expect(second).toEqual(first);
  });

  it('Given a strategy, when the note is requested, then only Bayesian has one and it is the fixed sentence', () => {
    /**
     * Scenario: the explanation is a fixed string chosen by strategy, never assembled at render time.
     * Slice: 67 — deterministic explanations.
     */
    // -- When / Then --
    expect(sweepNote('bayesian')).toBe(BAYESIAN_SWEEP_NOTE);
    expect(sweepNote('grid')).toBeNull();
    expect(sweepNote(undefined)).toBeNull();
  });
});
