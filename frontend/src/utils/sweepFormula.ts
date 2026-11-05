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
  total: number;
  /** Singular unit of the total, e.g. "configuration". */
  unit: string;
}

export interface SweepFormulaSource {
  models: unknown[];
  chunking_methods: unknown[];
  chunk_sizes: unknown[];
  overlaps: unknown[];
  paddings?: unknown[];
  retrievers?: unknown[];
  retrieval_methods?: unknown[];
}

export function pluralize(count: number, label: string): string {
  return `${count} ${label}${count === 1 ? '' : 's'}`;
}

export function formulaProduct(terms: FormulaTerm[]): number {
  return terms.reduce((product, term) => product * term.count, 1);
}

const atLeastOne = (items: unknown[] | undefined): number => items?.length || 1;

export function sweepFormulaFromSummary(summary: SweepFormulaSource): SweepFormula {
  const terms: FormulaTerm[] = [
    { count: summary.models.length, label: 'model' },
    { count: summary.chunking_methods.length, label: 'chunking method' },
    { count: summary.chunk_sizes.length, label: 'size' },
    { count: summary.overlaps.length, label: 'overlap' },
    { count: atLeastOne(summary.paddings), label: 'padding' },
    { count: atLeastOne(summary.retrievers ?? summary.retrieval_methods), label: 'retriever' },
  ];
  return { terms, total: formulaProduct(terms), unit: 'configuration' };
}
