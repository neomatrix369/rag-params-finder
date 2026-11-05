import { formulaProduct, pluralize, type FormulaTerm } from '../../utils/sweepFormula';

interface FormulaLineProps {
  terms: FormulaTerm[];
  /** Singular unit of the total, e.g. "configuration". */
  unit: string;
  /** Overrides the product when the total is observed rather than derived. */
  total?: number;
  className?: string;
}

/** Renders `2 models × 3 sizes = 6 configurations` — the total is the product of the terms. */
export default function FormulaLine({ terms, unit, total, className }: FormulaLineProps) {
  const value = total ?? formulaProduct(terms);
  const factors = terms.map((term) => pluralize(term.count, term.label)).join(' × ');
  return (
    <span className={className} data-testid="formula-line">
      {factors} = {pluralize(value, unit)}
    </span>
  );
}
