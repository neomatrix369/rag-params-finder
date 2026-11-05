/**
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67 static guard — dashboard numbers and explanations come from pure functions.
 */
import { describe, expect, it } from 'vitest';

const SOURCES = import.meta.glob(
  [
    '/src/utils/sweepFormula.ts',
    '/src/components/chrome/FormulaLine.tsx',
    '/src/utils/experimentStatus.ts',
    '/src/components/experiment/experimentDetailProgress.ts',
    '/src/components/walkthru/scoreLabels.ts',
    '/src/components/stats/estimateLabels.ts',
    '/src/components/screens/ExperimentDetailScreen.tsx',
    '/src/components/screens/ExperimentsScreen.tsx',
    '/src/components/explore/ExplorePanels.tsx',
  ],
  { query: '?raw', import: 'default', eager: true },
) as Record<string, string>;

const read = (relative: string): string => {
  const source = SOURCES[`/${relative}`];
  if (source === undefined) throw new Error(`guard source not found: ${relative}`);
  return source;
};

/** Modules whose output must depend only on their arguments (extend as 67B-67D add helpers). */
const PURE_MODULES = [
  'src/utils/sweepFormula.ts',
  'src/components/chrome/FormulaLine.tsx',
  'src/utils/experimentStatus.ts',
  'src/components/experiment/experimentDetailProgress.ts',
  'src/components/walkthru/scoreLabels.ts',
  'src/components/stats/estimateLabels.ts',
];

const NON_DETERMINISTIC = /\b(Date\.now|new Date\(\s*\)|Math\.random|performance\.now|fetch\(|localStorage|sessionStorage|window\.|document\.)/;

/** Screens must render counts produced elsewhere, never multiply them in JSX. */
const SCREENS = [
  'src/components/screens/ExperimentDetailScreen.tsx',
  'src/components/explore/ExplorePanels.tsx',
  'src/components/screens/ExperimentsScreen.tsx',
];
const JSX_COUNT_ARITHMETIC = /\.length\s*[*×]|[*×]\s*[\w.?]+\.length\b|\.filter\([^\n]*\)\.length|\/\s*[\w.?]+\)?\s*\*\s*100/;

describe('deterministic numbers guard', () => {
  it.each(PURE_MODULES)('Given %s, when scanned, then it reads no clock, randomness, storage, network or DOM', (file) => {
    /**
     * Scenario: a pure module cannot drift between renders or machines.
     * Slice: 67 — standing requirement: deterministic numbers and explanations.
     */
    // -- Given --
    const source = read(file);

    // -- When / Then --
    expect(source).not.toMatch(NON_DETERMINISTIC);
  });

  it.each(SCREENS)('Given %s, when scanned, then no count is multiplied, filtered-and-counted or turned into a percentage inline', (file) => {
    /**
     * Scenario: every shown count is derived by a named pure function, not inline arithmetic.
     * Slice: 67 — 'no count is computed as JSX arithmetic' oracle.
     */
    // -- Given --
    const source = read(file);

    // -- When / Then --
    expect(source).not.toMatch(JSX_COUNT_ARITHMETIC);
  });
});
