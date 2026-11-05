/**
 * Tests for the pure InfoTip helpers.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67C — clampShift and accessible-name sentences
 */
import { describe, expect, it } from 'vitest';
import { aboutLabel, clampShift, explainLabel } from './infoTipUtils';

describe('clampShift', () => {
  it.each([
    ['left overflow', { left: -60, right: 196 }, 390, 68],
    ['right overflow', { left: 200, right: 456 }, 390, -74],
    ['fits', { left: 50, right: 306 }, 390, 0],
    ['exactly on the margins', { left: 8, right: 382 }, 390, 0],
    ['wider than the room favours the left edge', { left: -10, right: 420 }, 390, 18],
  ])('Given %s, when clamped, then the nudge matches the literal oracle', (_name, rect, vw, expected) => {
    /**
     * Scenario: Literal-number oracle for the viewport clamp (margin 8).
     * Slice: 67C — InfoTip
     */
    // -- Given / When --
    const shift = clampShift(rect, vw);
    // -- Then --
    expect(shift).toBe(expected);
  });

  it('Given a custom margin, when clamped, then it is honoured', () => {
    /**
     * Scenario: Margin is a parameter.
     * Slice: 67C — InfoTip
     */
    // -- Given / When / Then --
    expect(clampShift({ left: 0, right: 100 }, 390, 20)).toBe(20);
  });
});

describe('labels', () => {
  it('Given a label, when formatted, then the sentences are fixed', () => {
    /**
     * Scenario: Accessible-name sentences are pure functions of the label.
     * Slice: 67C — InfoTip
     */
    // -- Given / When / Then --
    expect(aboutLabel('Total')).toBe('About Total');
    expect(explainLabel('Total')).toBe('How Total is calculated');
  });
});
