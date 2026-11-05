/**
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67 static guard — dashboard numbers and explanations come from pure functions.
 */
import { describe, expect, it } from 'vitest';
import { JSX_COUNT_ARITHMETIC, NEW_DATE_WITH_ARGUMENT, NON_DETERMINISTIC } from './deterministicNumbers.patterns';

const SOURCES = import.meta.glob(
  [
    '/src/utils/sweepFormula.ts',
    '/src/components/chrome/FormulaLine.tsx',
    '/src/utils/experimentStatus.ts',
    '/src/components/experiment/experimentDetailProgress.ts',
    '/src/components/experiment/experimentDetail/ProgressSubtitle.tsx',
    '/src/components/explore/scoreCounts.ts',
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
  'src/components/experiment/experimentDetail/ProgressSubtitle.tsx',
  'src/components/explore/scoreCounts.ts',
  'src/components/walkthru/scoreLabels.ts',
  'src/components/stats/estimateLabels.ts',
];

/** Screens must render counts produced elsewhere, never multiply them in JSX. */
const SCREENS = [
  'src/components/screens/ExperimentDetailScreen.tsx',
  'src/components/explore/ExplorePanels.tsx',
  'src/components/screens/ExperimentsScreen.tsx',
  'src/components/experiment/experimentDetail/ProgressSubtitle.tsx',
];

/** Pure parse helpers: the only `new Date(<arg>)` occurrences allowed, with the exact count each may hold. */
const DATE_PARSE_ALLOWANCE: Record<string, number> = {
  'src/components/experiment/experimentDetailProgress.ts': 1, // parseSafeTimestamp
};

describe('deterministic numbers guard', () => {
  it.each(PURE_MODULES)('Given %s, when scanned, then date strings are parsed only through the listed parse helper', (file) => {
    /**
     * Scenario: a clock-free module may still parse a given date string, but only in one named place.
     * Slice: 67D — keeps `new Date(arg)` an explicit, counted exception.
     */
    // -- Given --
    const source = read(file);

    // -- When --
    const parses = source.match(NEW_DATE_WITH_ARGUMENT) ?? [];

    // -- Then --
    // eslint-disable-next-line security/detect-object-injection -- file comes from the literal PURE_MODULES list
    expect(parses.length).toBeLessThanOrEqual(DATE_PARSE_ALLOWANCE[file] ?? 0);
  });

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

  it('Given the exact expressions this slice removed, when the guard patterns run, then they match, and a parse of a given date does not', () => {
    /**
     * Scenario: positive control — the guard can fail; the no-argument Date narrowing is a tested contract.
     * Slice: 67D — falsifying power for the determinism guard.
     */
    // -- Given --
    const removedArithmetic = [
      'percent={(runSummary.complete / runSummary.expected) * 100}',
      "experiments.filter(exp => exp.status !== 'running').length",
      'const n = items.length * x',
    ];
    const clockReads = ['const t = Date.now();', 'const t = new Date();'];

    // -- When / Then --
    removedArithmetic.forEach((expression) => expect(expression).toMatch(JSX_COUNT_ARITHMETIC));
    clockReads.forEach((expression) => expect(expression).toMatch(NON_DETERMINISTIC));
    expect('const start = new Date(startedAt).getTime();').not.toMatch(NON_DETERMINISTIC);
    expect('const start = new Date(startedAt).getTime();').toMatch(NEW_DATE_WITH_ARGUMENT);
  });
});
