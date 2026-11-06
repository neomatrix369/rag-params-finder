/**
 * Tests for the pure estimate-label helpers.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67D - est. label and formula text are deterministic templates.
 */
import { describe, expect, it } from 'vitest'
import {
  BYTES_PER_DIMENSION,
  METADATA_BYTES_PER_CHUNK,
  chunksEstimateExplain,
  dbUsedExplain,
  estimateFormula,
  estimatedMbLabel,
  experimentsExplain,
  queryResultsExplain,
} from './estimateLabels'

describe('stats tile explanations', () => {
  it('Given the whole-store tiles, when explained, then each names its scope and only the chunk tile says est.', () => {
    /**
     * Scenario: Stats tiles state scope (whole store) and which numbers are estimates.
     * Slice: 67G-A - stats explanations
     * Given the four explanation helpers,
     * When called,
     * Then every sentence ends with the whole-store scope, and the chunk tile carries est. and the formula.
     */
    // -- Given / When --
    const sentences = [experimentsExplain(), queryResultsExplain(), dbUsedExplain(), chunksEstimateExplain()]

    // -- Then --
    sentences.forEach((sentence) => expect(sentence).toMatch(/Scope: whole store\.$/))
    expect(chunksEstimateExplain()).toBe(`est. MB = ${estimateFormula()} Scope: whole store.`)
    expect(dbUsedExplain()).toContain('not estimated')
    expect(experimentsExplain()).toBe('Experiments stored in this database, not runs. Scope: whole store.')
    expect(queryResultsExplain()).toContain('one row per golden-dataset query per run')
  })
})

describe('estimateLabels', () => {
  it('Given the same input, when called twice, then the output is identical and carries the constants', () => {
    /**
     * Scenario: Determinism - fixed template with the server's byte constants.
     * Slice: 67D - pure helpers
     */
    // -- Given / When --
    const a = [estimatedMbLabel(12.5), estimateFormula()]
    const b = [estimatedMbLabel(12.5), estimateFormula()]

    // -- Then --
    expect(b).toEqual(a)
    expect(a[0]).toBe('est. 12.5 MB')
    expect(a[1]).toContain(`${BYTES_PER_DIMENSION} bytes`)
    expect(a[1]).toContain(`${METADATA_BYTES_PER_CHUNK} bytes`)
    expect(a[1]).toContain('average dimensions')
  })
})
