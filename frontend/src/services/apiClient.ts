import { Experiment, ExploreResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

const EXPERIMENTS_URL = `${API_BASE_URL}/experiments`;

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
  const response = await fetch(EXPERIMENTS_URL);
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

  const response = await fetch(EXPERIMENTS_URL, { signal });

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
  const response = await fetch(`${API_BASE_URL}/experiments/${experimentId}`);
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
  const response = await fetch(`${API_BASE_URL}/experiments/${experimentId}/explore${params}`);
  if (!response.ok) {
    throw new Error('Failed to fetch experiment explore data');
  }
  return response.json();
}

export async function cancelExperiment(
  experimentId: string,
): Promise<{ status: string; message: string }> {
  const response = await fetch(`${API_BASE_URL}/experiments/${experimentId}/cancel`, {
    method: 'POST',
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to cancel experiment');
  }
  return response.json();
}
