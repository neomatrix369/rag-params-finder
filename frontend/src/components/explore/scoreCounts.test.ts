/**
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67D - Explorer tie count.
 */
import { describe, expect, it } from 'vitest';
import { countConfigsAtScore } from './scoreCounts';

describe('countConfigsAtScore', () => {
  it('Given configs with a shared top score, when counted at that score, then only exact ties are counted', () => {
    /**
     * Scenario: the Explorer tie count is a named pure function, not inline filtering.
     * Slice: 67D — determinism guard widening.
     */
    // -- Given --
    const configs = [{ max_score: 91 }, { max_score: 91 }, { max_score: 80 }];

    // -- When / Then --
    expect(countConfigsAtScore(configs, 91)).toBe(2);
  });
});
