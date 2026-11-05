/**
 * Tests for the pure Query Results breakdown builders.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67E - runs x golden queries = results; fixed templates, fixed en-US numbers.
 */
import { describe, expect, it } from 'vitest'
import { pluralize } from '../../utils/sweepFormula'
import {
  INFERRED_MARKER,
  RESULTS_ROW_NOTE,
  experimentResultsFormula,
  formatCount,
  groupResultsBreakdown,
  partialRunsNote,
} from './resultsBreakdown'

const stats = (overrides = {}) => ({
  result_runs: 12,
  golden_queries: 40,
  golden_queries_source: 'config' as const,
  total_results: 480,
  ...overrides,
})

describe('experimentResultsFormula', () => {
  it('Given runs, golden count and total, when built, then terms are runs and golden queries with the observed total', () => {
    /**
     * Scenario: A complete payload yields the two-term formula.
     * Slice: 67E - pure builder
     */
    // -- Given / When --
    const formula = experimentResultsFormula(stats())

    // -- Then --
    expect(formula).toEqual({
      terms: [
        { count: 12, label: 'run' },
        { count: 40, label: 'golden query' },
      ],
      unit: 'result',
      observedTotal: 480,
      exact: true,
      observedText: '480 results (observed) · 12 runs × 40 golden queries',
      sourceNote: null,
    })
  })

  it.each([
    ['old payload (fields absent)', { result_runs: undefined, golden_queries: undefined }],
    ['null golden (Redis/ES)', { golden_queries: null, golden_queries_source: null }],
    ['null runs', { result_runs: null }],
    ['NaN golden', { golden_queries: Number.NaN }],
    ['missing total_results', { total_results: undefined }],
    ['null total_results', { total_results: null }],
    ['string total_results', { total_results: '480' }],
  ])('Given %s, when built, then there is no formula', (_name, overrides) => {
    /**
     * Scenario: Missing facts hide the breakdown instead of showing 0 or NaN.
     * Slice: 67E - hide, do not show 0
     */
    // -- Given / When --
    const formula = experimentResultsFormula(stats(overrides))

    // -- Then --
    expect(formula).toBeNull()
  })

  it('Given a stored total that differs from runs x golden, when built, then the formula is not exact', () => {
    /**
     * Scenario: 12 x 40 = 480 but 470 rows are stored.
     * Slice: 67E - no false "="
     */
    // -- Given / When --
    const formula = experimentResultsFormula(stats({ total_results: 470 }))

    // -- Then --
    expect(formula?.exact).toBe(false)
    expect(formula?.observedText).toBe('470 results (observed) · 12 runs × 40 golden queries')
  })

  it('Given an inferred golden count, when built, then the source note carries the inferred marker', () => {
    /**
     * Scenario: max_per_run means the golden count was guessed from the results.
     * Slice: 67E - inferred marker
     */
    // -- Given / When --
    const inferred = experimentResultsFormula(stats({ golden_queries_source: 'max_per_run' }))
    const configured = experimentResultsFormula(stats({ golden_queries_source: 'config' }))

    // -- Then --
    expect(inferred?.sourceNote).toContain(INFERRED_MARKER)
    expect(configured?.sourceNote).toBeNull()
  })
})

describe('partialRunsNote', () => {
  it('Given partial runs on a running experiment, when worded, then it says "below the golden count so far"', () => {
    /**
     * Scenario: A running run is partial only for now.
     * Slice: 67E - partial-runs wording
     */
    // -- Given / When --
    const note = partialRunsNote({ partial_runs: 3 }, false)

    // -- Then --
    expect(note).toBe('3 runs below the golden count so far (still running or incomplete).')
  })

  it('Given partial runs on a finished experiment, when worded, then it states a fact without "so far"', () => {
    /**
     * Scenario: Terminal experiments will not add more results.
     * Slice: 67E - partial-runs wording
     */
    // -- Given / When --
    const note = partialRunsNote({ partial_runs: 1 }, true)

    // -- Then --
    expect(note).toBe('1 run returned fewer results than the golden count.')
  })

  it.each([[0], [null], [undefined]])('Given partial_runs %s, when worded, then there is no note', (partial) => {
    /**
     * Scenario: Nothing partial or unknown stays silent.
     * Slice: 67E - hide when absent
     */
    // -- Given / When / Then --
    expect(partialRunsNote({ partial_runs: partial }, true)).toBeNull()
  })
})

describe('groupResultsBreakdown', () => {
  const totals = (overrides = {}) => ({
    total_results: 6480,
    total_result_runs: 162,
    golden_queries_min: 40,
    golden_queries_max: 40,
    ...overrides,
  })

  it('Given min equals max, when built, then the group is uniform with runs and golden terms', () => {
    /**
     * Scenario: Every experiment has the same golden size.
     * Slice: 67E - uniform group
     */
    // -- Given / When --
    const breakdown = groupResultsBreakdown(totals())

    // -- Then --
    expect(breakdown).toEqual({
      kind: 'uniform',
      terms: [
        { count: 162, label: 'run' },
        { count: 40, label: 'golden query' },
      ],
      unit: 'result',
      observedTotal: 6480,
    })
  })

  it('Given min differs from max, when built, then the group is mixed with the observed total and range, no "="', () => {
    /**
     * Scenario: Experiments differ in golden size, so no single product exists.
     * Slice: 67E - mixed group
     */
    // -- Given / When --
    const breakdown = groupResultsBreakdown(totals({ golden_queries_min: 20 }))

    // -- Then --
    expect(breakdown.kind).toBe('mixed')
    if (breakdown.kind === 'mixed') {
      expect(breakdown.summary).toBe('6,480 results (observed); experiments have 20 to 40 golden queries.')
      expect(breakdown.summary).not.toContain('=')
    }
  })

  it('Given a uniform group whose product differs from the total, when built, then it is reported as observed', () => {
    /**
     * Scenario: 162 x 40 = 6,480 but 6,000 stored.
     * Slice: 67E - no false "=" at group level
     */
    // -- Given / When --
    const breakdown = groupResultsBreakdown(totals({ total_results: 6000 }))

    // -- Then --
    expect(breakdown).toEqual({
      kind: 'mixed',
      observedTotal: 6000,
      summary: '6,000 results (observed) · 162 runs × 40 golden queries',
    })
  })

  it.each([
    ['golden fields absent', { golden_queries_min: undefined, golden_queries_max: undefined }],
    ['golden fields null', { golden_queries_min: null, golden_queries_max: null }],
    ['one bound null', { golden_queries_max: null }],
    ['uniform but runs unknown', { total_result_runs: undefined }],
  ])('Given %s, when built, then the breakdown is unavailable', (_name, overrides) => {
    /**
     * Scenario: Split-store groups report no golden facts; nothing is invented.
     * Slice: 67E - unavailable group
     */
    // -- Given / When --
    const breakdown = groupResultsBreakdown(totals(overrides))

    // -- Then --
    expect(breakdown).toEqual({ kind: 'unavailable' })
  })
})

describe('pluralize with a consonant + y label', () => {
  it('Given "golden query", when pluralized, then it becomes queries; a vowel + y label keeps a plain s', () => {
    /**
     * Scenario: "golden query" must not read "golden querys".
     * Slice: 67E - shared pluralize
     */
    // -- Given / When --
    const many = pluralize(2, 'golden query')
    const one = pluralize(1, 'golden query')
    const vowelY = pluralize(2, 'key')

    // -- Then --
    expect([many, one, vowelY]).toEqual(['2 golden queries', '1 golden query', '2 keys'])
  })
})

describe('determinism', () => {
  it('Given the same input twice, when built, then the output is identical and numbers use en-US grouping', () => {
    /**
     * Scenario: Fixed locale, not the environment's.
     * Slice: 67E - determinism
     */
    // -- Given --
    const input = { total_results: 1234567, total_result_runs: 7, golden_queries_min: 1, golden_queries_max: 9 }

    // -- When --
    const a = groupResultsBreakdown(input)
    const b = groupResultsBreakdown(input)

    // -- Then --
    expect(b).toEqual(a)
    expect(formatCount(1234567)).toBe('1,234,567')
    // control: a different locale really would differ, so the assertion above has teeth
    expect((1234567).toLocaleString('de-DE')).not.toBe(formatCount(1234567))
    expect(RESULTS_ROW_NOTE).toBe(
      'One result row per query per run; top-k only sets how many chunks each row holds.',
    )
  })
})
