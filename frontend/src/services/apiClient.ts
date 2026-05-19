import { DeleteExperimentResponse, Experiment, ExperimentDbStatsResponse, ExploreResponse, VectorDbStatsGroupedResponse } from '../types';
import { fetchJsonWithProgress, type FetchProgressUpdate } from './fetchWithProgress';
import { devWarn } from '../utils/devLog';

export { formatBytes } from './fetchWithProgress';

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
    devWarn('Network failure:', url, err);
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

export type ExperimentProgressCallback = (u: FetchProgressUpdate) => void;

function emit(cb: ExperimentProgressCallback | undefined, u: FetchProgressUpdate) {
  cb?.(u);
}

export async function getExperiments(signal?: AbortSignal): Promise<Experiment[]> {
  let response: Response;
  try {
    response = await fetch(EXPERIMENTS_URL, { signal });
  } catch (err) {
    rethrowWithFetchHint(EXPERIMENTS_URL, err);
  }
  if (!response.ok) throw new Error('Failed to fetch experiments');
  const data = (await response.json()) as { experiments?: Experiment[] };
  return data.experiments || [];
}

export async function getExperimentsWithProgress(
  onProgress: ExperimentProgressCallback | undefined,
  signal?: AbortSignal,
): Promise<Experiment[]> {
  emit(onProgress, { type: 'message', text: `GET ${EXPERIMENTS_URL}` });
  let data: { experiments?: Experiment[] };
  try {
    data = await fetchJsonWithProgress<{ experiments?: Experiment[] }>(
      EXPERIMENTS_URL,
      { signal },
      (u) => emit(onProgress, u),
    );
  } catch (err) {
    rethrowWithFetchHint(EXPERIMENTS_URL, err);
  }
  const experiments = data.experiments || [];
  emit(onProgress, {
    type: 'message',
    text: `Parsed ${experiments.length} experiment record(s).`,
  });
  return experiments;
}

export async function getExperiment(experimentId: string, signal?: AbortSignal): Promise<Experiment> {
  const url = `${API_BASE_URL}/experiments/${experimentId}`;
  let response: Response;
  try {
    response = await fetch(url, { signal });
  } catch (err) {
    rethrowWithFetchHint(url, err);
  }
  if (!response.ok) throw new Error('Failed to fetch experiment');
  return response.json();
}

export async function getExperimentWithProgress(
  experimentId: string,
  onProgress: ExperimentProgressCallback | undefined,
  signal?: AbortSignal,
): Promise<Experiment> {
  const url = `${API_BASE_URL}/experiments/${experimentId}`;
  emit(onProgress, { type: 'message', text: `GET ${url}` });
  let data: Experiment;
  try {
    data = await fetchJsonWithProgress<Experiment>(url, { signal }, (u) => emit(onProgress, u));
  } catch (err) {
    rethrowWithFetchHint(url, err);
  }

  const runCount =
    typeof (data as { run_count?: number }).run_count === 'number'
      ? (data as { run_count: number }).run_count
      : 0;
  const runs = (data as { runs?: unknown[] }).runs;

  emit(onProgress, {
    type: 'message',
    text:
      Array.isArray(runs) && runs.length > 0
        ? `Parsed experiment (${runCount} configured runs · ${runs.length} run rows).`
        : `Parsed experiment.`,
  });

  return data;
}

export async function getExperimentExplore(
  experimentId: string,
  query?: string,
  signal?: AbortSignal,
): Promise<ExploreResponse> {
  const params = query ? `?query=${encodeURIComponent(query)}` : '';
  const url = `${API_BASE_URL}/experiments/${experimentId}/explore${params}`;
  let response: Response;
  try {
    response = await fetch(url, { signal });
  } catch (err) {
    rethrowWithFetchHint(url, err);
  }
  if (!response.ok) throw new Error('Failed to fetch experiment explore data');
  return response.json();
}

export async function getExperimentExploreWithProgress(
  experimentId: string,
  query: string | undefined,
  onProgress: ExperimentProgressCallback | undefined,
  signal?: AbortSignal,
): Promise<ExploreResponse> {
  const params = query ? `?query=${encodeURIComponent(query)}` : '';
  const url = `${API_BASE_URL}/experiments/${experimentId}/explore${params}`;
  const qSnippet =
    query && query.length > 0 ? ` (${query.length > 60 ? `${query.slice(0, 60)}…` : query})` : '';
  emit(onProgress, {
    type: 'message',
    text: `GET explore for ${experimentId.slice(0, 8)}…${qSnippet}`,
  });

  let data: ExploreResponse;
  try {
    data = await fetchJsonWithProgress<ExploreResponse>(url, { signal }, (u) => emit(onProgress, u));
  } catch (err) {
    rethrowWithFetchHint(url, err);
  }

  emit(onProgress, {
    type: 'message',
    text: `Explorer payload: ${data.ranked_configs.length} configs · ${data.total_matches} matches · ${data.query_count} quer${data.query_count === 1 ? 'y' : 'ies'}.`,
  });

  return data;
}

export async function getExperimentDbStats(
  experimentId: string,
  signal?: AbortSignal,
): Promise<ExperimentDbStatsResponse> {
  const url = `${API_BASE_URL}/experiments/${experimentId}/db-stats`;
  let response: Response;
  try {
    response = await fetch(url, { signal });
  } catch (err) {
    rethrowWithFetchHint(url, err);
  }
  if (!response.ok) throw new Error('Failed to fetch experiment DB stats');
  return response.json();
}

export async function getVectorDbStatsGrouped(
  signal?: AbortSignal,
): Promise<VectorDbStatsGroupedResponse> {
  const url = `${API_BASE_URL}/experiments/vector-db-stats`;
  let response: Response;
  try {
    response = await fetch(url, { signal });
  } catch (err) {
    rethrowWithFetchHint(url, err);
  }
  if (!response.ok) throw new Error('Failed to fetch vector DB stats');
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
    const parsed = await response.json().catch(() => ({}));
    const detail = typeof parsed.detail === 'string' ? parsed.detail : undefined;
    throw new Error(detail || 'Failed to cancel experiment');
  }
  return response.json();
}

export async function pauseExperiment(
  experimentId: string,
): Promise<{ status: string; message: string }> {
  const url = `${API_BASE_URL}/experiments/${experimentId}/pause`;
  let response: Response;
  try {
    response = await fetch(url, { method: 'POST' });
  } catch (err) {
    rethrowWithFetchHint(url, err);
  }
  if (!response.ok) {
    const parsed = await response.json().catch(() => ({}));
    const detail = typeof parsed.detail === 'string' ? parsed.detail : undefined;
    throw new Error(detail || 'Failed to pause experiment');
  }
  return response.json();
}

export async function resumeExperiment(
  experimentId: string,
): Promise<{ status: string; message: string; run_count?: number }> {
  const url = `${API_BASE_URL}/experiments/${experimentId}/resume`;
  let response: Response;
  try {
    response = await fetch(url, { method: 'POST' });
  } catch (err) {
    rethrowWithFetchHint(url, err);
  }
  if (!response.ok) {
    const parsed = await response.json().catch(() => ({}));
    const detail = typeof parsed.detail === 'string' ? parsed.detail : undefined;
    throw new Error(detail || 'Failed to resume experiment');
  }
  return response.json();
}

export async function deleteExperiment(experimentId: string): Promise<DeleteExperimentResponse> {
  const url = `${API_BASE_URL}/experiments/${experimentId}`;
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'DELETE',
    });
  } catch (err) {
    rethrowWithFetchHint(url, err);
  }
  if (!response.ok) {
    const parsed = await response.json().catch(() => ({}));
    const detail = typeof parsed.detail === 'string' ? parsed.detail : undefined;
    throw new Error(detail || 'Failed to delete experiment');
  }
  return response.json();
}
