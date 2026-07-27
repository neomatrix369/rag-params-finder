/**
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 — byte formatting, timeout abort, JSON progress fetch.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  abortSignalWithTimeout,
  fetchJsonWithProgress,
  fetchWithTimeout,
  formatBytes,
} from './fetchWithProgress';

describe('fetchWithProgress', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it.each([
    { n: 512, expected: '512 B' },
    { n: 2048, expected: '2.0 KB' },
    { n: 2 * 1024 * 1024, expected: '2.00 MB' },
  ])('Given $n bytes, when formatBytes, then $expected', ({ n, expected }) => {
    // -- Given / When / Then --
    expect(formatBytes(n)).toBe(expected);
  });

  it('Given a slow fetch, when timeout elapses, then fetchWithTimeout rejects with timeout copy', async () => {
    /**
     * Scenario: Timed-out API calls surface a sweep-busy message.
     * Slice: 44 — frontend coverage gate (fetchWithProgress).
     * Given fetch never resolves before the timeout,
     * When fetchWithTimeout waits past the limit,
     * Then the rejection message names the timeout window.
     */
    // -- Given --
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) => {
        return new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => {
            reject(new DOMException('Aborted', 'AbortError'));
          });
        });
      }),
    );

    // -- When --
    const pending = fetchWithTimeout('http://127.0.0.1:8001/experiments', {}, 1000);
    const assertion = expect(pending).rejects.toThrow(/timed out after 1s/);
    await vi.advanceTimersByTimeAsync(1000);

    // -- Then --
    await assertion;
  });

  it('Given already-aborted user signal, when abortSignalWithTimeout builds, then signal is aborted', () => {
    /**
     * Scenario: Caller abort is forwarded into the composed timeout signal.
     * Slice: 44 — frontend coverage gate (fetchWithProgress).
     * Given a user AbortSignal that is already aborted,
     * When abortSignalWithTimeout composes,
     * Then the returned signal is aborted immediately.
     */
    // -- Given --
    const user = new AbortController();
    user.abort();

    // -- When --
    const { signal, dispose } = abortSignalWithTimeout(user.signal, 5000);

    // -- Then --
    expect(signal.aborted).toBe(true);
    dispose();
  });

  it('Given a 200 JSON body, when fetchJsonWithProgress runs, then progress emits and payload parses', async () => {
    /**
     * Scenario: Successful streaming JSON fetch reports download then parse.
     * Slice: 44 — frontend coverage gate (fetchWithProgress).
     * Given a 200 response with Content-Length and a JSON body,
     * When fetchJsonWithProgress reads it,
     * Then downloading updates and a parse message are emitted and data returns.
     */
    // -- Given --
    const payload = { experiments: [{ experiment_id: 'e1' }] };
    const body = JSON.stringify(payload);
    const updates: Array<{ type: string; text?: string }> = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        return new Response(body, {
          status: 200,
          headers: { 'Content-Length': String(body.length), 'Content-Type': 'application/json' },
        });
      }),
    );

    // -- When --
    const actual = await fetchJsonWithProgress<typeof payload>(
      'http://127.0.0.1:8001/experiments',
      undefined,
      (u) => updates.push(u),
    );

    // -- Then --
    expect(actual).toEqual(payload);
    expect(updates.some((u) => u.type === 'downloading')).toBe(true);
    expect(updates.some((u) => u.type === 'message' && u.text?.includes('Parsing JSON'))).toBe(
      true,
    );
  });

  it('Given a non-OK response, when fetchJsonWithProgress runs, then HTTP status is in the error', async () => {
    /**
     * Scenario: HTTP errors fail before JSON parse.
     * Slice: 44 — frontend coverage gate (fetchWithProgress).
     * Given a 503 response body,
     * When fetchJsonWithProgress is called,
     * Then the rejection message includes HTTP 503.
     */
    // -- Given --
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('busy', { status: 503 })),
    );

    // -- When / Then --
    await expect(
      fetchJsonWithProgress('http://127.0.0.1:8001/experiments', undefined, () => undefined),
    ).rejects.toThrow(/HTTP 503/);
  });
});
