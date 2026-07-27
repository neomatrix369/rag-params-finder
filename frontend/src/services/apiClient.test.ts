/**
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 — experiment list/detail/control API helpers and error paths.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  cancelExperiment,
  deleteExperiment,
  getApiBaseUrl,
  getExperiment,
  getExperiments,
  pauseExperiment,
  resumeExperiment,
} from './apiClient';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('apiClient', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('Given default env, when getApiBaseUrl is read, then a non-empty origin is returned', () => {
    /**
     * Scenario: Resolved API base is always available for diagnostics.
     * Slice: 44 — frontend coverage gate (apiClient).
     * Given the module-resolved API base,
     * When getApiBaseUrl is called,
     * Then a non-empty string is returned.
     */
    // -- Given / When --
    const actual = getApiBaseUrl();

    // -- Then --
    expect(actual.length).toBeGreaterThan(0);
  });

  it('Given experiments payload, when getExperiments succeeds, then the list is returned', async () => {
    /**
     * Scenario: List endpoint unwraps the experiments array.
     * Slice: 44 — frontend coverage gate (apiClient).
     * Given a 200 response with experiments[],
     * When getExperiments runs,
     * Then the array is returned.
     */
    // -- Given --
    const experiments = [{ experiment_id: 'exp-1', experiment_name: 'demo', status: 'complete' }];
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ experiments }));

    // -- When --
    const actual = await getExperiments();

    // -- Then --
    expect(actual).toEqual(experiments);
    expect(fetch).toHaveBeenCalled();
  });

  it('Given HTTP 500 with detail, when getExperiment fails, then detail is thrown', async () => {
    /**
     * Scenario: Server error detail surfaces to the UI layer.
     * Slice: 44 — frontend coverage gate (apiClient).
     * Given a 500 JSON body with detail,
     * When getExperiment is called,
     * Then the Error message equals the detail string.
     */
    // -- Given --
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ detail: 'experiment not found' }, 500),
    );

    // -- When / Then --
    await expect(getExperiment('missing')).rejects.toThrow('experiment not found');
  });

  it('Given network TypeError, when getExperiments fails, then a reachability hint is thrown', async () => {
    /**
     * Scenario: Network failures include API reachability guidance.
     * Slice: 44 — frontend coverage gate (apiClient).
     * Given fetch rejects with TypeError Failed to fetch,
     * When getExperiments is called,
     * Then the Error mentions API reachability.
     */
    // -- Given --
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError('Failed to fetch'));

    // -- When / Then --
    await expect(getExperiments()).rejects.toThrow(/Is the API reachable/);
  });

  it.each([
    {
      name: 'pause',
      call: () => pauseExperiment('exp-1'),
      pathSuffix: '/pause',
      body: { status: 'paused', message: 'ok' },
    },
    {
      name: 'resume',
      call: () => resumeExperiment('exp-1'),
      pathSuffix: '/resume',
      body: { status: 'running', message: 'ok' },
    },
    {
      name: 'cancel',
      call: () => cancelExperiment('exp-1'),
      pathSuffix: '/cancel',
      body: { status: 'cancelled', message: 'ok' },
    },
  ])(
    'Given control action $name, when POSTed successfully, then response JSON is returned',
    async ({ call, pathSuffix, body }) => {
      // -- Given --
      vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(body));

      // -- When --
      const actual = await call();

      // -- Then --
      expect(actual).toEqual(body);
      const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
      expect(url).toContain(pathSuffix);
      expect(init.method).toBe('POST');
    },
  );

  it('Given delete succeeds, when deleteExperiment runs, then DELETE is used', async () => {
    /**
     * Scenario: Cascade delete uses HTTP DELETE.
     * Slice: 44 — frontend coverage gate (apiClient).
     * Given a 200 delete response,
     * When deleteExperiment runs,
     * Then fetch uses method DELETE and returns the payload.
     */
    // -- Given --
    const body = {
      experiment_id: 'exp-1',
      deleted: true,
      chunks_deleted: 1,
      results_deleted: 1,
      runs_deleted: 1,
    };
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(body));

    // -- When --
    const actual = await deleteExperiment('exp-1');

    // -- Then --
    expect(actual).toEqual(body);
    const [, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe('DELETE');
  });
});
