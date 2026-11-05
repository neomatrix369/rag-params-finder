/**
 * Tests for the pure score-label helpers.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67D - lone-run marker, dedup note and baseline text are deterministic templates.
 */
import { describe, expect, it } from 'vitest'
import { LONE_RUN_LABEL, STORY_BASELINE_NOTE, dedupNote, scoreCellLabel } from './scoreLabels'

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
