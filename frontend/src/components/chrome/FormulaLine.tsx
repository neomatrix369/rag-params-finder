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
  className?: string;
}

/** Renders `2 models × 3 sizes = 6 configurations`; the total is the product of the terms. */
export default function FormulaLine({ terms, unit, observedTotal, className }: FormulaLineProps) {
  const product = formulaProduct(terms);
  const factors = terms.map((term) => pluralize(term.count, term.label)).join(' × ');
  const isObserved = observedTotal !== undefined && observedTotal !== product;
  return (
    <span className={className}>
      {factors} = {pluralize(isObserved ? observedTotal : product, unit)}
      {isObserved ? ' (observed)' : ''}
    </span>
  );
}
