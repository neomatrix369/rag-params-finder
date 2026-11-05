import { formulaProduct, pluralize, type FormulaTerm } from '../../utils/sweepFormula';

interface FormulaLineProps {
  terms: FormulaTerm[];
  /** Singular unit of the total, e.g. "configuration". */
  unit: string;
  /**
   * A count observed from results rather than derived from the terms. When it differs from the
   * product the line says "(observed)" instead of printing a false equality. Slice 67D removes it.
   */
  observedTotal?: number;
  /** Number formatter for every count; defaults to plain digits. */
  formatCount?: (count: number) => string;
}

/** Renders `2 models × 3 sizes = 6 configurations`; the total is the product of the terms. */
export default function FormulaLine({ terms, unit, observedTotal, formatCount }: FormulaLineProps) {
  const product = formulaProduct(terms);
  const factors = terms.map((term) => pluralize(term.count, term.label, formatCount)).join(' × ');
  const isObserved = observedTotal !== undefined && observedTotal !== product;
  return (
    <span>
      {factors} = {pluralize(isObserved ? observedTotal : product, unit, formatCount)}
      {isObserved ? ' (observed)' : ''}
    </span>
  );
}
