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
  getExperimentDbStats,
  getExperimentExplore,
  getExperimentExploreWithProgress,
  getExperiments,
  getExperimentsWithProgress,
  getExperimentWithProgress,
  getVectorDbStatsGrouped,
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

  it('Given explore payload, when getExperimentExplore succeeds, then JSON is returned', async () => {
    /**
     * Scenario: Explore endpoint returns ranked configs payload.
     * Slice: 44 Phase B — apiClient
     */
    // -- Given --
    const body = { ranked_configs: [], total_matches: 0, query_count: 0 };
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(body));

    // -- When --
    const actual = await getExperimentExplore('exp-1', 'deadline');

    // -- Then --
    expect(actual).toEqual(body);
    expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain('query=deadline');
  });

  it('Given db-stats payload, when getExperimentDbStats succeeds, then JSON is returned', async () => {
    /**
     * Scenario: Per-experiment db-stats endpoint unwraps.
     * Slice: 44 Phase B — apiClient
     */
    // -- Given --
    const body = { experiment_id: 'exp-1', db_stats: { total_chunks: 1 } };
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(body));

    // -- When --
    const actual = await getExperimentDbStats('exp-1');

    // -- Then --
    expect(actual).toEqual(body);
  });

  it('Given grouped vector stats, when getVectorDbStatsGrouped succeeds, then groups are returned', async () => {
    /**
     * Scenario: Cluster-grouped vector DB stats endpoint.
     * Slice: 44 Phase B — apiClient
     */
    // -- Given --
    const body = { groups: [] };
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(body));

    // -- When --
    const actual = await getVectorDbStatsGrouped();

    // -- Then --
    expect(actual).toEqual(body);
  });

  it('Given progress helpers, when fetch resolves JSON, then callbacks receive messages', async () => {
    /**
     * Scenario: WithProgress helpers emit progress messages.
     * Slice: 44 Phase B — apiClient
     */
    // -- Given --
    const onProgress = vi.fn();
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ experiments: [] }));

    // -- When --
    await getExperimentsWithProgress(onProgress);
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ experiment_id: 'exp-1', run_count: 2, runs: [{}, {}] }),
    );
    await getExperimentWithProgress('exp-1', onProgress);
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ ranked_configs: [], total_matches: 0, query_count: 1 }),
    );
    await getExperimentExploreWithProgress('exp-1', 'q'.repeat(80), onProgress);

    // -- Then --
    expect(onProgress.mock.calls.length).toBeGreaterThan(2);
  });

  it('Given HTTP error with error field, when assertOk runs, then error string is thrown', async () => {
    /**
     * Scenario: Alternate JSON error key surfaces as Error message.
     * Slice: 44 Phase B — apiClient
     */
    // -- Given --
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ error: 'quota exceeded' }, 422));

    // -- When / Then --
    await expect(getExperiment('exp-1')).rejects.toThrow('quota exceeded');
  });

  it('Given a successful response, when getExperiment runs, then the experiment JSON is returned', async () => {
    /**
     * Scenario: Single-experiment fetch happy path.
     * Slice: 44 Phase C — apiClient coverage gate.
     * Given a 200 response with an experiment body,
     * When getExperiment is called,
     * Then the parsed JSON is returned unchanged.
     */
    // -- Given --
    const body = { experiment_id: 'exp-1', experiment_name: 'demo', status: 'running' };
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(body));

    // -- When --
    const actual = await getExperiment('exp-1');

    // -- Then --
    expect(actual).toEqual(body);
  });

  it('Given a DOMException AbortError, when getExperiment aborts, then the same error is rethrown unchanged', async () => {
    /**
     * Scenario: Caller-initiated aborts on plain-fetch endpoints propagate without the reachability wrapper.
     * Slice: 44 Phase C — apiClient coverage gate.
     * Given fetch rejects with a DOMException named AbortError,
     * When getExperiment is called (no fetchWithTimeout involved),
     * Then the exact same AbortError instance rejects the call.
     */
    // -- Given --
    const abortError = new DOMException('Aborted', 'AbortError');
    vi.mocked(fetch).mockRejectedValueOnce(abortError);

    // -- When / Then --
    await expect(getExperiment('exp-1')).rejects.toBe(abortError);
  });

  it('Given a generic Error with a network-failure message, when getExperiments fails, then a reachability hint is thrown', async () => {
    /**
     * Scenario: Non-TypeError network signatures (Safari "Load failed", browser NetworkError) still map to the hint.
     * Slice: 44 Phase C — apiClient coverage gate.
     * Given fetch rejects with a plain Error whose message matches known network-failure text,
     * When getExperiments is called,
     * Then the Error mentions API reachability.
     */
    // -- Given --
    vi.mocked(fetch).mockRejectedValueOnce(
      new Error('NetworkError when attempting to fetch resource.'),
    );

    // -- When / Then --
    await expect(getExperiments()).rejects.toThrow(/Is the API reachable/);
  });

  it('Given a non-Error rejection unrelated to networking, when getExperiments fails, then the original value is rethrown unchanged', async () => {
    /**
     * Scenario: Unclassified rejections (not Error, not Abort, not a network signature) pass through untouched.
     * Slice: 44 Phase C — apiClient coverage gate.
     * Given fetch rejects with a plain string,
     * When getExperiments is called,
     * Then the same string value rejects the promise.
     */
    // -- Given --
    vi.mocked(fetch).mockRejectedValueOnce('boom');

    // -- When / Then --
    await expect(getExperiments()).rejects.toBe('boom');
  });

  const NETWORK_FAILURE_CASES: Array<{ name: string; call: () => Promise<unknown> }> = [
    { name: 'getExperimentsWithProgress', call: () => getExperimentsWithProgress(undefined) },
    { name: 'getExperiment', call: () => getExperiment('exp-1') },
    { name: 'getExperimentWithProgress', call: () => getExperimentWithProgress('exp-1', undefined) },
    { name: 'getExperimentExplore', call: () => getExperimentExplore('exp-1') },
    {
      name: 'getExperimentExploreWithProgress',
      call: () => getExperimentExploreWithProgress('exp-1', undefined, undefined),
    },
    { name: 'getExperimentDbStats', call: () => getExperimentDbStats('exp-1') },
    { name: 'getVectorDbStatsGrouped', call: () => getVectorDbStatsGrouped() },
    { name: 'cancelExperiment', call: () => cancelExperiment('exp-1') },
    { name: 'pauseExperiment', call: () => pauseExperiment('exp-1') },
    { name: 'resumeExperiment', call: () => resumeExperiment('exp-1') },
    { name: 'deleteExperiment', call: () => deleteExperiment('exp-1') },
  ];

  it.each(NETWORK_FAILURE_CASES)(
    'Given a network TypeError, when $name fails, then a reachability hint is thrown',
    async ({ call }) => {
      /**
       * Scenario: Every API helper's catch path surfaces the reachability hint on network failure.
       * Slice: 44 Phase C — apiClient coverage gate (covers cancel/pause/resume/delete catch paths).
       */
      // -- Given --
      vi.mocked(fetch).mockRejectedValueOnce(new TypeError('Failed to fetch'));

      // -- When / Then --
      await expect(call()).rejects.toThrow(/Is the API reachable/);
    },
  );

  it('Given a response without an experiments key, when getExperiments runs, then an empty array is returned', async () => {
    /**
     * Scenario: Missing experiments key degrades gracefully to an empty list.
     * Slice: 44 Phase C — apiClient coverage gate.
     */
    // -- Given --
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({}));

    // -- When --
    const actual = await getExperiments();

    // -- Then --
    expect(actual).toEqual([]);
  });

  it('Given a response without an experiments key, when getExperimentsWithProgress runs, then an empty array is returned', async () => {
    /**
     * Scenario: WithProgress variant mirrors the missing-key fallback.
     * Slice: 44 Phase C — apiClient coverage gate.
     */
    // -- Given --
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({}));

    // -- When --
    const actual = await getExperimentsWithProgress(undefined);

    // -- Then --
    expect(actual).toEqual([]);
  });

  it('Given experiment data without a runs array, when getExperimentWithProgress runs, then a generic parsed message is emitted', async () => {
    /**
     * Scenario: Experiments still queued (no run rows yet) skip the run-count summary text.
     * Slice: 44 Phase C — apiClient coverage gate.
     * Given an experiment body with neither `run_count` nor `runs`,
     * When getExperimentWithProgress is called,
     * Then the progress message falls back to the generic "Parsed experiment." text.
     */
    // -- Given --
    const onProgress = vi.fn();
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ experiment_id: 'exp-1' }));

    // -- When --
    await getExperimentWithProgress('exp-1', onProgress);

    // -- Then --
    expect(onProgress).toHaveBeenCalledWith({ type: 'message', text: 'Parsed experiment.' });
  });

  it('Given no query parameter, when getExperimentExplore runs, then the request URL omits the query string', async () => {
    /**
     * Scenario: Optional query param is omitted from the explore request when absent.
     * Slice: 44 Phase C — apiClient coverage gate.
     */
    // -- Given --
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ ranked_configs: [], total_matches: 0, query_count: 0 }),
    );

    // -- When --
    await getExperimentExplore('exp-1');

    // -- Then --
    expect(String(vi.mocked(fetch).mock.calls[0][0])).not.toContain('?query=');
  });

  it('Given no query parameter, when getExperimentExploreWithProgress runs, then the message omits a query snippet and pluralizes a non-singular query count', async () => {
    /**
     * Scenario: Progress messages degrade gracefully with no query text and non-singular match counts.
     * Slice: 44 Phase C — apiClient coverage gate.
     */
    // -- Given --
    const onProgress = vi.fn();
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ ranked_configs: [], total_matches: 0, query_count: 0 }),
    );

    // -- When --
    await getExperimentExploreWithProgress('exp-1', undefined, onProgress);

    // -- Then --
    const startMessage = onProgress.mock.calls[0][0] as { text: string };
    expect(startMessage.text).not.toContain('(');
    const calls = onProgress.mock.calls;
    const summaryMessage = calls[calls.length - 1][0] as { text: string };
    expect(summaryMessage.text).toContain('0 queries.');
  });

  it('Given a short query, when getExperimentExploreWithProgress runs, then the snippet is not truncated', async () => {
    /**
     * Scenario: Queries at or under the 60-character preview limit render in full.
     * Slice: 44 Phase C — apiClient coverage gate.
     */
    // -- Given --
    const onProgress = vi.fn();
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ ranked_configs: [], total_matches: 1, query_count: 1 }),
    );

    // -- When --
    await getExperimentExploreWithProgress('exp-1', 'ai', onProgress);

    // -- Then --
    const startMessage = onProgress.mock.calls[0][0] as { text: string };
    expect(startMessage.text).toContain('(ai)');
  });

  it('Given an HTTP error with a malformed JSON body, when getExperiments fails, then the fallback message is thrown', async () => {
    /**
     * Scenario: Neither `detail` nor `error` is recoverable from the response — the fallback message is used.
     * Slice: 44 Phase C — apiClient coverage gate.
     * Given a 500 response whose body is not valid JSON,
     * When getExperiments is called,
     * Then the generic fallback message is thrown instead of a parsed detail.
     */
    // -- Given --
    vi.mocked(fetch).mockResolvedValueOnce(new Response('not-json', { status: 500 }));

    // -- When / Then --
    await expect(getExperiments()).rejects.toThrow('Failed to fetch experiments');
  });
});
