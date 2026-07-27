/**
 * Tests for dev-only console helpers.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 Phase B — devDebug/Info/Warn + throttled variants
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  devDebug,
  devDebugThrottled,
  devInfo,
  devInfoThrottled,
  devWarn,
} from './devLog';

describe('devLog', () => {
  beforeEach(() => {
    vi.spyOn(console, 'debug').mockImplementation(() => undefined);
    vi.spyOn(console, 'info').mockImplementation(() => undefined);
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('Given DEV mode, when helpers are called, then scoped console methods fire', () => {
    /**
     * Scenario: Dev helpers prefix scope and forward to console.
     * Slice: 44 Phase B — devLog
     */
    // -- Given / When --
    devDebug('Scope', 'debug msg', 1);
    devInfo('Scope', 'info msg');
    devWarn('Scope', 'warn msg');

    // -- Then --
    expect(console.debug).toHaveBeenCalled();
    expect(console.info).toHaveBeenCalled();
    expect(console.warn).toHaveBeenCalled();
  });

  it('Given throttled key, when called twice within interval, then logs once', () => {
    /**
     * Scenario: Throttle suppresses rapid duplicate breadcrumbs.
     * Slice: 44 Phase B — devLog
     */
    // -- Given --
    const lastAt = new Map<string, number>();
    vi.spyOn(Date, 'now').mockReturnValue(10_000);

    // -- When --
    devInfoThrottled('Poll', 'list', 5_000, 'first', lastAt);
    devInfoThrottled('Poll', 'list', 5_000, 'second', lastAt);
    devDebugThrottled('Poll', 'list', 5_000, 'third', lastAt);

    // -- Then --
    expect(console.info).toHaveBeenCalledTimes(1);
  });

  it('Given throttled key after interval, when called again, then logs again', () => {
    /**
     * Scenario: Throttle resets after intervalMs.
     * Slice: 44 Phase B — devLog
     */
    // -- Given --
    const lastAt = new Map<string, number>();
    const now = vi.spyOn(Date, 'now');
    now.mockReturnValue(1_000);
    devInfoThrottled('Poll', 'k', 100, 'a', lastAt);

    // -- When --
    now.mockReturnValue(1_200);
    devInfoThrottled('Poll', 'k', 100, 'b', lastAt);

    // -- Then --
    expect(console.info).toHaveBeenCalledTimes(2);
  });

  it('Given production mode, when helpers are called, then console methods stay quiet', () => {
    /**
     * Scenario: Non-DEV builds drop all console breadcrumbs.
     * Slice: 44 Phase B — devLog DEV=false branches
     */
    // -- Given --
    vi.stubEnv('DEV', false);

    // -- When --
    devDebug('Scope', 'debug msg');
    devInfo('Scope', 'info msg');
    devWarn('Scope', 'warn msg');
    const lastAt = new Map<string, number>();
    devInfoThrottled('Poll', 'list', 5_000, 'throttled', lastAt);

    // -- Then --
    expect(console.debug).not.toHaveBeenCalled();
    expect(console.info).not.toHaveBeenCalled();
    expect(console.warn).not.toHaveBeenCalled();
  });
});
