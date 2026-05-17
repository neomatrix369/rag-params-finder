import { Experiment, ExploreResponse } from '../types';

/**
 * Resolve API origin: explicit VITE_API_URL wins.
 * Dev default `/api` uses Vite proxy → 127.0.0.1:8001 (same-origin fetch, no CORS).
 * Non-dev default uses IPv4 literal so `localhost` is not resolved to [::1].
 */
function resolvedApiBaseUrl(): string {
  const raw = typeof import.meta.env.VITE_API_URL === 'string' ? import.meta.env.VITE_API_URL.trim() : '';
  if (raw !== '') return raw;
  if (import.meta.env.DEV) return '/api';
  return 'http://127.0.0.1:8001';
}

const API_BASE_URL = resolvedApiBaseUrl();

const EXPERIMENTS_URL = `${API_BASE_URL}/experiments`;

/** Browser fetch uses this vague message for CORS, refused connection, DNS, etc. */
function isLikelyNetworkFailure(err: unknown): boolean {
  if (err instanceof TypeError) return true;
  if (!(err instanceof Error)) return false;
  return /failed to fetch|networkerror|load failed/i.test(err.message);
}

function rethrowWithFetchHint(url: string, err: unknown): never {
  if (err instanceof DOMException && err.name === 'AbortError') {
    throw err;
  }
  if (isLikelyNetworkFailure(err)) {
    const pageOrigin =
      typeof window !== 'undefined' && window.location?.origin != null
        ? window.location.origin
        : '(SSR / unknown)';
    throw new Error(
      `Failed to fetch ${url}. Is the API reachable at ${API_BASE_URL}? ` +
        `(Dev: leave VITE_API_URL unset to use the /api proxy unless you intentionally override.) ` +
        `If pointing at localhost, try http://127.0.0.1:8001 — some systems resolve localhost to IPv6 [::1] ` +
        `while uvicorn only listens on 127.0.0.1. ` +
        `CORS/page origin is ${pageOrigin}.`,
    );
  }
  throw err;
}

/** Throttle high-frequency byte progress callbacks (streaming body). */
const BYTE_PROGRESS_INTERVAL_MS = 200;

export type ExperimentsListProgressUpdate =
  | { type: 'message'; text: string; variant?: 'default' | 'warning' }
  | {
      type: 'downloading';
      receivedBytes: number;
      totalBytes: number | null;
    };

function parseContentLength(response: Response): number | null {
  const hdr = response.headers.get('Content-Length');
  const n = hdr !== null ? Number.parseInt(hdr, 10) : NaN;
  if (Number.isNaN(n) || n < 0) return null;
  return n;
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
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
    const now =
      typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now();
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

export async function getExperiments(): Promise<Experiment[]> {
  let response: Response;
  try {
    response = await fetch(EXPERIMENTS_URL);
  } catch (err) {
    rethrowWithFetchHint(EXPERIMENTS_URL, err);
  }
  if (!response.ok) throw new Error('Failed to fetch experiments');
  const data = (await response.json()) as { experiments?: Experiment[] };
  return data.experiments || [];
}

/**
 * Loads the experiments list while reporting download / parse milestones.
 * When the server sends Content-Length, reports received vs total bytes.
 */
export async function getExperimentsWithProgress(
  onProgress: (u: ExperimentsListProgressUpdate) => void,
  signal?: AbortSignal,
): Promise<Experiment[]> {
  onProgress({
    type: 'message',
    text: `GET ${EXPERIMENTS_URL}`,
  });

  let response: Response;
  try {
    response = await fetch(EXPERIMENTS_URL, { signal });
  } catch (err) {
    rethrowWithFetchHint(EXPERIMENTS_URL, err);
  }

  if (!response.ok) throw new Error(`Failed to fetch experiments (${response.status})`);

  let lastEmitted = -1;
  const text = await readBodyAsTextTracked(
    response,
    (received, total) => {
      if (received === lastEmitted) return;
      lastEmitted = received;
      onProgress({
        type: 'downloading',
        receivedBytes: received,
        totalBytes: total,
      });
    },
    signal,
  );

  const hdrTotal = parseContentLength(response);

  const downloadNote =
    hdrTotal !== null
      ? `Download complete (${formatBytes(text.length)} of ${formatBytes(hdrTotal)})`
      : `Response body read (${formatBytes(text.length)})`;

  onProgress({
    type: 'message',
    text: `${downloadNote}. Parsing JSON…`,
  });

  const data = JSON.parse(text) as { experiments?: Experiment[] };
  const experiments = data.experiments || [];

  onProgress({
    type: 'message',
    text: `Parsed ${experiments.length} experiment record(s).`,
  });

  return experiments;
}

export async function getExperiment(experimentId: string): Promise<Experiment> {
  const url = `${API_BASE_URL}/experiments/${experimentId}`;
  let response: Response;
  try {
    response = await fetch(url);
  } catch (err) {
    rethrowWithFetchHint(url, err);
  }
  if (!response.ok) {
    throw new Error('Failed to fetch experiment');
  }
  return response.json();
}

export async function getExperimentExplore(
  experimentId: string,
  query?: string,
): Promise<ExploreResponse> {
  const params = query ? `?query=${encodeURIComponent(query)}` : '';
  const url = `${API_BASE_URL}/experiments/${experimentId}/explore${params}`;
  let response: Response;
  try {
    response = await fetch(url);
  } catch (err) {
    rethrowWithFetchHint(url, err);
  }
  if (!response.ok) {
    throw new Error('Failed to fetch experiment explore data');
  }
  return response.json();
}

export async function cancelExperiment(
  experimentId: string,
): Promise<{ status: string; message: string }> {
  const url = `${API_BASE_URL}/experiments/${experimentId}/cancel`;
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
    });
  } catch (err) {
    rethrowWithFetchHint(url, err);
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to cancel experiment');
  }
  return response.json();
}
