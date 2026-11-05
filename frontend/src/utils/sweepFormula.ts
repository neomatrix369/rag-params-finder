import type { SweepSummary } from '../types';

/**
 * Pure builders for the Cartesian "configurations" formula line (Slice 67A).
 * Mirrors `expand_sweep`: paddings [] → [0], no retrievers → one dense retriever.
 */
export interface FormulaTerm {
  count: number;
  /** Singular label; `pluralize` adds the "s". */
  label: string;
}

export interface SweepFormula {
  terms: FormulaTerm[];
  /** Singular unit of the product, e.g. "configuration". */
  unit: string;
}

export type SweepFormulaSource = Pick<
  SweepSummary,
  'models' | 'chunking_methods' | 'chunk_sizes' | 'overlaps' | 'paddings' | 'retrievers' | 'retrieval_methods'
>;

/** Regular plurals only (adds "s"); every current label fits. */
export function pluralize(count: number, label: string): string {
  return `${count} ${label}${count === 1 ? '' : 's'}`;
}

export function formulaProduct(terms: FormulaTerm[]): number {
  return terms.reduce((product, term) => product * term.count, 1);
}

const atLeastOne = (items: unknown[] | undefined): number => items?.length || 1;

/** An empty `retrievers` falls back to the legacy list, like the backend's migration. */
const retrieverList = (summary: SweepFormulaSource): unknown[] | undefined =>
  summary.retrievers?.length ? summary.retrievers : summary.retrieval_methods;

export function sweepFormulaFromSummary(summary: SweepFormulaSource): SweepFormula {
  const terms: FormulaTerm[] = [
    { count: summary.models.length, label: 'model' },
    { count: summary.chunking_methods.length, label: 'chunking method' },
    { count: summary.chunk_sizes.length, label: 'size' },
    { count: summary.overlaps.length, label: 'overlap' },
    { count: atLeastOne(summary.paddings), label: 'padding' },
    { count: atLeastOne(retrieverList(summary)), label: 'retriever' },
  ];
  return { terms, unit: 'configuration' };
}
