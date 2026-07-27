/**
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 — byte formatting, timeout abort, JSON progress fetch.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  abortSignalWithTimeout,
  createStallWatcher,
  fetchJsonWithProgress,
  fetchWithTimeout,
  formatBytes,
} from './fetchWithProgress';

const EXPERIMENTS_URL = 'http://127.0.0.1:8001/experiments';

/** Minimal fake `Response` for stream-path tests that a real `Response` cannot express. */
function fakeStreamResponse(
  reader: { read: () => Promise<{ done: boolean; value?: Uint8Array }>; cancel: () => Promise<void> },
  init: { ok?: boolean; status?: number; headers?: Record<string, string> } = {},
): Response {
  return {
    ok: init.ok ?? true,
    status: init.status ?? 200,
    headers: new Headers(init.headers ?? {}),
    body: { getReader: () => reader },
    text: async () => '',
  } as unknown as Response;
}

describe('fetchWithProgress', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it.each([
    { n: 0, expected: '0 B' },
    { n: 512, expected: '512 B' },
    { n: 1024, expected: '1.0 KB' },
    { n: 2048, expected: '2.0 KB' },
    { n: 1024 * 1024, expected: '1.00 MB' },
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

  it('Given a non-OK response whose body cannot be read, when fetchJsonWithProgress runs, then the plain HTTP status message is thrown', async () => {
    /**
     * Scenario: `response.text()` rejecting falls back to an empty error body.
     * Slice: 44 Phase C — fetchWithProgress coverage gate.
     * Given a 503 response whose text() call rejects,
     * When fetchJsonWithProgress is called,
     * Then the thrown message is the plain "HTTP 503" (no detail suffix).
     */
    // -- Given --
    const fakeResponse = {
      ok: false,
      status: 503,
      headers: new Headers(),
      text: async () => {
        throw new Error('body stream errored');
      },
    } as unknown as Response;
    vi.stubGlobal('fetch', vi.fn(async () => fakeResponse));

    // -- When / Then --
    await expect(fetchJsonWithProgress(EXPERIMENTS_URL, undefined, () => undefined)).rejects.toThrow(
      /^HTTP 503$/,
    );
  });

  it('Given a response without a readable body, when fetchJsonWithProgress runs, then response.text() is used as a fallback', async () => {
    /**
     * Scenario: Responses without a ReadableStream body (e.g. some polyfills) still parse.
     * Slice: 44 Phase C — fetchWithProgress coverage gate.
     */
    // -- Given --
    const payload = { ok: true };
    const fakeResponse = {
      ok: true,
      status: 200,
      headers: new Headers(),
      body: null,
      text: async () => JSON.stringify(payload),
    } as unknown as Response;
    vi.stubGlobal('fetch', vi.fn(async () => fakeResponse));

    // -- When --
    const actual = await fetchJsonWithProgress(EXPERIMENTS_URL, undefined, () => undefined);

    // -- Then --
    expect(actual).toEqual(payload);
  });

  it('Given a defined non-aborted user signal, when fetchJsonWithProgress runs, then the request still resolves normally', async () => {
    /**
     * Scenario: A caller-supplied AbortSignal that never fires is forwarded without side effects.
     * Slice: 44 Phase C — fetchWithProgress coverage gate.
     */
    // -- Given --
    const controller = new AbortController();
    const payload = { ok: true };
    const body = JSON.stringify(payload);
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(body, {
            status: 200,
            headers: { 'Content-Length': String(body.length) },
          }),
      ),
    );

    // -- When --
    const actual = await fetchJsonWithProgress(
      EXPERIMENTS_URL,
      { signal: controller.signal },
      () => undefined,
    );

    // -- Then --
    expect(actual).toEqual(payload);
  });

  it('Given the caller aborts mid-stream, when fetchJsonWithProgress reads chunks, then the reader is cancelled and AbortError propagates', async () => {
    /**
     * Scenario: An abort fired between chunk reads stops the stream and surfaces an AbortError.
     * Slice: 44 Phase C — fetchWithProgress coverage gate.
     * Given a stream reader whose second poll observes an aborted signal,
     * When fetchJsonWithProgress reads the body,
     * Then the reader is cancelled and the promise rejects with an AbortError.
     */
    // -- Given --
    const controller = new AbortController();
    const reader = {
      read: vi.fn(async () => {
        controller.abort();
        return { done: false, value: new Uint8Array([1, 2, 3]) };
      }),
      cancel: vi.fn(async () => {
        throw new Error('cancel failed');
      }),
    };
    vi.stubGlobal('fetch', vi.fn(async () => fakeStreamResponse(reader)));

    // -- When / Then --
    await expect(
      fetchJsonWithProgress(EXPERIMENTS_URL, { signal: controller.signal }, () => undefined),
    ).rejects.toMatchObject({ name: 'AbortError' });
    expect(reader.cancel).toHaveBeenCalled();
  });

  it('Given a chunk read with no value and no Content-Length header, when fetchJsonWithProgress runs, then empty chunks are skipped and the plain body-read message is used', async () => {
    /**
     * Scenario: Defensive `continue` on an empty chunk, and the non-Content-Length download note.
     * Slice: 44 Phase C — fetchWithProgress coverage gate.
     */
    // -- Given --
    let calls = 0;
    const reader = {
      read: vi.fn(async () => {
        calls += 1;
        if (calls === 1) return { done: false, value: undefined };
        if (calls === 2) return { done: false, value: new TextEncoder().encode('{}') };
        return { done: true, value: undefined };
      }),
      cancel: vi.fn(async () => undefined),
    };
    vi.stubGlobal('fetch', vi.fn(async () => fakeStreamResponse(reader)));
    const updates: Array<{ type: string; text?: string }> = [];

    // -- When --
    const actual = await fetchJsonWithProgress(EXPERIMENTS_URL, undefined, (u) => updates.push(u));

    // -- Then --
    expect(actual).toEqual({});
    expect(
      updates.some((u) => u.type === 'message' && u.text?.includes('Response body read')),
    ).toBe(true);
  });

  it('Given a live user signal, when it aborts after construction, then the composed signal aborts too', () => {
    /**
     * Scenario: A user abort fired after setup forwards into the composed timeout controller.
     * Slice: 44 Phase C — fetchWithProgress coverage gate.
     */
    // -- Given --
    const user = new AbortController();
    const { signal, dispose } = abortSignalWithTimeout(user.signal, 5000);
    expect(signal.aborted).toBe(false);

    // -- When --
    user.abort();

    // -- Then --
    expect(signal.aborted).toBe(true);
    dispose();
  });

  it('Given timers advance past the stall thresholds, when start/stop are called repeatedly, then warnings repeat while alive and both timers clear', () => {
    /**
     * Scenario: createStallWatcher repeats warnings on a schedule and respects the alive() guard.
     * Slice: 44 Phase C — fetchWithProgress coverage gate.
     * Given a stall watcher configured with a short after/repeat interval,
     * When start() is called twice in a row, timers fire, and alive() later flips to false,
     * Then onWarning fires only while alive() is true, and stop() clears any pending timers.
     */
    // -- Given --
    const onWarning = vi.fn();
    let alive = true;
    const watcher = createStallWatcher({
      scope: 'test',
      operation: 'download',
      alive: () => alive,
      onWarning,
      afterMs: 1000,
      repeatMs: 500,
    });

    // -- When --
    watcher.start();
    watcher.start(); // re-entrant start while a timeout is still pending
    vi.advanceTimersByTime(1000); // first warning fires; repeat interval scheduled
    vi.advanceTimersByTime(500); // repeat interval fires a second warning
    watcher.start(); // re-entrant start while an interval is still active
    alive = false;
    vi.advanceTimersByTime(1000); // fires again, but alive() is false — no additional warning
    watcher.stop();

    // -- Then --
    expect(onWarning).toHaveBeenCalledTimes(2);
    expect(onWarning.mock.calls[0][0]).toMatch(/Still waiting/);
  });
});
