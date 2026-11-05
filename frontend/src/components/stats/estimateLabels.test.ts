/**
 * Tests for the pure estimate-label helpers.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67D - est. label and formula text are deterministic templates.
 */
import { describe, expect, it } from 'vitest'
import { BYTES_PER_DIMENSION, METADATA_BYTES_PER_CHUNK, estimateFormula, estimatedMbLabel } from './estimateLabels'

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
