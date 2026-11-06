/**
 * Tests for the pure score-label helpers.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67D - lone-run marker, dedup note and baseline text are deterministic templates.
 */
import { describe, expect, it } from 'vitest'
import {
  LONE_RUN_LABEL,
  OVERLAP_EXPLAIN,
  SCORE_COLUMN_EXPLAIN,
  STORY_BASELINE_NOTE,
  dedupNote,
  rankExplain,
  scoreCellLabel,
  storyRunsExplain,
  storyTileExplain,
  type StoryTile,
} from './scoreLabels'

describe('scoreLabels explanations (Slice 67G)', () => {
  it.each([
    [undefined, 'When a store ran the same config more than once, only the latest run is shown; earlier duplicates are collapsed.'],
    [0, '0 duplicate rows were collapsed: when a store ran the same config more than once, only the latest run is shown.'],
    [1, '1 duplicate row was collapsed: when a store ran the same config more than once, only the latest run is shown.'],
    [7, '7 duplicate rows were collapsed: when a store ran the same config more than once, only the latest run is shown.'],
  ])('Given collapsed=%s, when the dedup note is built, then it reads exactly', (collapsed, expected) => {
    /**
     * Scenario: A silent dedup becomes a visible sentence; an older server (absent field) states the rule only.
     * Slice: 67G - dedup visibility
     */
    // -- Given / When / Then --
    expect(dedupNote(collapsed)).toBe(expected)
  })

  it('Given each rank scope, when explained, then the counting scope is stated', () => {
    /**
     * Scenario: Rank is per group in live Compare and per export in Walkthru.
     * Slice: 67G - rank
     */
    // -- Given / When / Then --
    expect(rankExplain('group')).toContain('counted inside its group')
    expect(rankExplain('export')).toContain('counted across the whole export')
    expect(rankExplain('group')).toContain('not answer quality')
  })

  it('Given the fixed score and overlap explanations, when read, then normalisation, lone run and overlap rule are stated', () => {
    /**
     * Scenario: Normalisation and lone-run behaviour are explained once, in fixed text.
     * Slice: 67G - score normalisation
     */
    // -- Given / When / Then --
    expect(SCORE_COLUMN_EXPLAIN).toContain('lowest run in the group is 0 and the highest is 100')
    expect(SCORE_COLUMN_EXPLAIN).toContain(LONE_RUN_LABEL)
    expect(OVERLAP_EXPLAIN).toContain('at least two stores')
  })

  it.each([
    [1, '1 run from the primary store only'],
    [12, '12 runs from the primary store only'],
  ])('Given %i story runs, when explained, then it says "%s" and names the baseline', (count, phrase) => {
    /**
     * Scenario: "across N runs" is scoped to the primary store with a stated baseline.
     * Slice: 67G - percentage baselines
     */
    // -- Given / When --
    const text = storyRunsExplain(count)

    // -- Then --
    expect(text).toContain(phrase)
    expect(text).toContain('baseline is the lowest-scoring run (0)')
  })

  it.each<[StoryTile, string]>([
    ['best', 'highest'],
    ['median', 'middle'],
    ['worst', 'lowest'],
    ['spread', 'not a percentage'],
  ])('Given the %s tile, when explained, then the sentence mentions "%s"', (tile, word) => {
    /**
     * Scenario: Every story tile has its own fixed sentence.
     * Slice: 67G - percentage baselines
     */
    // -- Given / When / Then --
    expect(storyTileExplain(tile)).toContain(word)
  })
})

describe('scoreLabels', () => {
  it('Given the same inputs, when called twice, then the output is identical', () => {
    /**
     * Scenario: Determinism - fixed templates, no clock or randomness.
     * Slice: 67D - pure helpers
     */
    // -- Given / When --
    const first = [scoreCellLabel(87.25, 3), scoreCellLabel(100, 1), dedupNote(), dedupNote(4)]
    const second = [scoreCellLabel(87.25, 3), scoreCellLabel(100, 1), dedupNote(), dedupNote(4)]

    // -- Then --
    expect(second).toEqual(first)
  })

  it('Given group sizes, when the score cell is labelled, then only a lone run gets the marker', () => {
    /**
     * Scenario: A group of one never shows a number.
     * Slice: 67D - lone run
     */
    // -- Given / When / Then --
    expect(scoreCellLabel(100, 1)).toBe(LONE_RUN_LABEL)
    expect(scoreCellLabel(87.25, 2)).toBe('87.3')
  })

  it('Given a collapsed count, when the dedup note is built, then the number and plural are exact', () => {
    /**
     * Scenario: The count is stated when known; the rule alone otherwise.
     * Slice: 67D - dedup visibility
     */
    // -- Given / When / Then --
    expect(dedupNote(1)).toMatch(/^1 duplicate row was collapsed/)
    expect(dedupNote(3)).toMatch(/^3 duplicate rows were collapsed/)
    expect(dedupNote(0)).toMatch(/^0 duplicate rows were collapsed/)
    expect(dedupNote()).not.toMatch(/\d/)
    expect(STORY_BASELINE_NOTE).toMatch(/primary store only/)
  })
})
