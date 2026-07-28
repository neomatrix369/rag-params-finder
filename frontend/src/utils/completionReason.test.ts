/**
 * Author: Slice 45
 * Created: 2026-07-28
 * Scope: shared completionReasonLabel mapping
 */
import { describe, expect, it } from 'vitest';
import { completionReasonLabel } from './completionReason';

describe('completionReasonLabel', () => {
  it('Given a null reason, when labelled, then returns the recorded-state fallback', () => {
    /**
     * Scenario: Null completion reason maps to the recorded-state fallback.
     * Slice: 45 — FE shared primitives (completionReasonLabel).
     * Given reason is null,
     * When labelled,
     * Then the fallback phrase is returned.
     */
    // -- Given --
    const reason = null;
    // -- When --
    const label = completionReasonLabel(reason);
    // -- Then --
    expect(label).toBe('completion state recorded');
  });

  it('Given a known reason code, when labelled, then returns the mapped phrase', () => {
    /**
     * Scenario: Known reason codes map to human phrases.
     * Slice: 45 — FE shared primitives (completionReasonLabel).
     * Given cancelled_by_user,
     * When labelled,
     * Then "cancelled by user" is returned.
     */
    // -- Given --
    const reason = 'cancelled_by_user';
    // -- When --
    const label = completionReasonLabel(reason);
    // -- Then --
    expect(label).toBe('cancelled by user');
  });

  it('Given an unknown reason code, when labelled, then replaces underscores with spaces', () => {
    /**
     * Scenario: Unknown reason codes are humanized via underscore replacement.
     * Slice: 45 — FE shared primitives (completionReasonLabel).
     * Given custom_reason_code,
     * When labelled,
     * Then underscores become spaces.
     */
    // -- Given --
    const reason = 'custom_reason_code';
    // -- When --
    const label = completionReasonLabel(reason);
    // -- Then --
    expect(label).toBe('custom reason code');
  });
});
