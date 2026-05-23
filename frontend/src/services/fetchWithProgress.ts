/**
 * Streaming fetch progress for GET JSON bodies — byte counts when Content-Length exists.
 */

import { API_FETCH_TIMEOUT_MS } from '../constants';
import { devWarn } from '../utils/devLog';

const BYTE_PROGRESS_INTERVAL_MS = 200;

export function abortSignalWithTimeout(
  userSignal: AbortSignal | undefined,
  timeoutMs: number = API_FETCH_TIMEOUT_MS,
): { signal: AbortSignal; dispose: () => void } {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  const forwardAbort = () => controller.abort();
  if (userSignal?.aborted) {
    controller.abort();
  } else if (userSignal) {
    userSignal.addEventListener('abort', forwardAbort, { once: true });
  }
  return {
    signal: controller.signal,
    dispose: () => {
      clearTimeout(timeoutId);
      userSignal?.removeEventListener('abort', forwardAbort);
    },
  };
}

export async function fetchWithTimeout(
  url: string,
  init?: RequestInit,
  timeoutMs: number = API_FETCH_TIMEOUT_MS,
): Promise<Response> {
  const { signal, dispose } = abortSignalWithTimeout(init?.signal ?? undefined, timeoutMs);
  try {
    return await fetch(url, { ...init, signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error(
        `Request timed out after ${Math.round(timeoutMs / 1000)}s — the server may be busy running a sweep.`,
      );
    }
    throw err;
  } finally {
    dispose();
  }
}

export type FetchProgressUpdate =
  | { type: 'message'; text: string; variant?: 'default' | 'warning' }
  | {
      type: 'downloading';
      receivedBytes: number;
      totalBytes: number | null;
    };

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

function parseContentLength(response: Response): number | null {
  const hdr = response.headers.get('Content-Length');
  const n = hdr !== null ? Number.parseInt(hdr, 10) : NaN;
  if (Number.isNaN(n) || n < 0) return null;
  return n;
}

async function readBodyAsTextTracked(
  response: Response,
  onChunkProgress: (receivedBytes: number, totalBytes: number | null) => void,
  signal?: AbortSignal,
): Promise<string> {
  const validTotal = parseContentLength(response);

  if (!response.body) {
    const text = await response.text();
    onChunkProgress(text.length, validTotal);
    return text;
  }

  const reader = response.body.getReader();
  const parts: Uint8Array[] = [];
  let received = 0;
  let lastEmit = 0;

  const emitProgress = () => {
    const now = typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now();
    if (now - lastEmit >= BYTE_PROGRESS_INTERVAL_MS) {
      lastEmit = now;
      onChunkProgress(received, validTotal);
    }
  };

  while (true) {
    if (signal?.aborted) {
      reader.cancel().catch(() => undefined);
      throw new DOMException('Aborted', 'AbortError');
    }
    const { done, value } = await reader.read();
    if (done) break;
    if (!value) continue;
    parts.push(value);
    received += value.length;
    emitProgress();
  }

  onChunkProgress(received, validTotal);

  let length = 0;
  for (const p of parts) length += p.length;
  const merged = new Uint8Array(length);
  let off = 0;
  for (const p of parts) {
    merged.set(p, off);
    off += p.length;
  }

  return new TextDecoder().decode(merged);
}

export async function fetchJsonWithProgress<T>(
  url: string,
  init: RequestInit | undefined,
  onProgress: (u: FetchProgressUpdate) => void,
): Promise<T> {
  const rawSignal = init?.signal;
  const abortSignal =
    rawSignal === null || rawSignal === undefined ? undefined : rawSignal;

  const { signal, dispose } = abortSignalWithTimeout(abortSignal);
  let response: Response;
  try {
    response = await fetch(url, { ...init, signal });
  } finally {
    dispose();
  }

  if (!response.ok) {
    const errText = await response.text().catch(() => '');
    devWarn(
      'fetchWithProgress',
      `HTTP error — ${response.status} GET ${url.split('?')[0]}`,
      errText ? errText.slice(0, 200) : '(no body)',
    );
    throw new Error(
      errText ? `HTTP ${response.status}: ${errText.slice(0, 200)}` : `HTTP ${response.status}`,
    );
  }

  const hdrTotal = parseContentLength(response);
  onProgress({ type: 'downloading', receivedBytes: 0, totalBytes: hdrTotal });

  /** Skip duplicate emits when streaming reports the same cumulative count */
  let lastEmitted = 0;

  const text = await readBodyAsTextTracked(
    response,
    (received, total) => {
      if (received === lastEmitted) return;
      lastEmitted = received;
      onProgress({ type: 'downloading', receivedBytes: received, totalBytes: total });
    },
    abortSignal,
  );

  const downloadNote =
    hdrTotal !== null
      ? `Download complete (${formatBytes(text.length)} of ${formatBytes(hdrTotal)})`
      : `Response body read (${formatBytes(text.length)})`;
  onProgress({ type: 'message', text: `${downloadNote}. Parsing JSON…` });

  return JSON.parse(text) as T;
}

export type StallWatcher = {
  start: () => void;
  stop: () => void;
};

/** Repeats human-readable stalled warnings until `stop()`, if `alive()` is true. */
export function createStallWatcher(options: {
  scope: string;
  operation: string;
  alive: () => boolean;
  onWarning: (text: string) => void;
  afterMs: number;
  repeatMs: number;
}): StallWatcher {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  let intervalId: ReturnType<typeof setInterval> | null = null;
  const deadline = (): number =>
    typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now();

  const tickWarning = () => {
    if (!options.alive()) return;
    const elapsed = deadline() - baseline;
    const s = (elapsed / 1000).toFixed(1);
    const uiText = `Still waiting (${s}s) — server busy, Atlas latency, or large payload.`;
    devWarn(options.scope, `stall — ${options.operation} still waiting (${s}s) — server busy, Atlas latency, or large payload`);
    options.onWarning(uiText);
  };

  let baseline = 0;

  return {
    start() {
      baseline = deadline();
      if (timeoutId !== null) clearTimeout(timeoutId);
      if (intervalId !== null) clearInterval(intervalId);
      timeoutId = setTimeout(() => {
        timeoutId = null;
        tickWarning();
        intervalId = setInterval(tickWarning, options.repeatMs);
      }, options.afterMs);
    },
    stop() {
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
        timeoutId = null;
      }
      if (intervalId !== null) {
        clearInterval(intervalId);
        intervalId = null;
      }
    },
  };
}
