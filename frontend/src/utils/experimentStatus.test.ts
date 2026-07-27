/**
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 — terminal/active status helpers and retriever display labels.
 */
import { describe, expect, it } from 'vitest';
import { Phase, RetrievalMethod, RetrieverType, type RunStatus } from '../types';
import {
  displayRetrievers,
  isActiveExperimentStatus,
  isPausedExperimentStatus,
  isRunningExperimentStatus,
  isTerminalExperimentStatus,
  summarizeExperimentRuns,
} from './experimentStatus';

function run(phase: Phase, overrides: Partial<RunStatus> = {}): RunStatus {
  return {
    run_id: `run-${phase}`,
    experiment_id: 'exp-1',
    phase,
    database_provider: 'mongodb',
    embedding_provider: 'local',
    embedding_model: 'all-MiniLM-L6-v2',
    chunking_method: 'fixed' as RunStatus['chunking_method'],
    chunk_size: 512,
    overlap: 64,
    created_at: '2026-07-27T00:00:00Z',
    updated_at: '2026-07-27T00:00:00Z',
    elapsed_ms: 0,
    retrieval_method: 'dense' as RunStatus['retrieval_method'],
    ...overrides,
  };
}

describe('experimentStatus', () => {
  it('Given run phases and expected count, when summarized, then counts match phase buckets', () => {
    /**
     * Scenario: Run tally splits complete, failed, interrupted, and in-progress.
     * Slice: 44 — frontend coverage gate (experimentStatus).
     * Given four runs across terminal and active phases with expected=5,
     * When summarizeExperimentRuns runs,
     * Then neverStarted and inProgress reflect the shortfall and unfinished work.
     */
    // -- Given --
    const runs = [
      run(Phase.COMPLETE),
      run(Phase.FAILED),
      run(Phase.INTERRUPTED),
      run(Phase.QUERYING),
    ];

    // -- When --
    const actual = summarizeExperimentRuns(runs, 5);

    // -- Then --
    expect(actual).toEqual({
      expected: 5,
      started: 4,
      complete: 1,
      failed: 1,
      interrupted: 1,
      neverStarted: 1,
      inProgress: 1,
    });
  });

  it.each([
    { status: 'complete' as const, completedAt: null, terminal: true },
    { status: 'failed' as const, completedAt: null, terminal: true },
    { status: 'partial' as const, completedAt: null, terminal: true },
    { status: 'cancelled' as const, completedAt: null, terminal: true },
    { status: 'running' as const, completedAt: null, terminal: false },
    { status: 'paused' as const, completedAt: null, terminal: false },
    { status: 'running' as const, completedAt: '2026-07-27T01:00:00Z', terminal: true },
  ])(
    'Given status=$status completedAt=$completedAt, when isTerminal, then $terminal',
    ({ status, completedAt, terminal }) => {
      // -- Given / When / Then --
      expect(isTerminalExperimentStatus(status, completedAt)).toBe(terminal);
    },
  );

  it('Given running vs paused, when activity helpers run, then only matching statuses match', () => {
    /**
     * Scenario: Control buttons rely on running/paused/active helpers.
     * Slice: 44 — frontend coverage gate (experimentStatus).
     * Given running and paused statuses without completed_at,
     * When the activity helpers evaluate,
     * Then each helper returns true only for its intended status.
     */
    // -- Given / When / Then --
    expect(isRunningExperimentStatus('running')).toBe(true);
    expect(isRunningExperimentStatus('paused')).toBe(false);
    expect(isPausedExperimentStatus('paused')).toBe(true);
    expect(isPausedExperimentStatus('running')).toBe(false);
    expect(isActiveExperimentStatus('running')).toBe(true);
    expect(isActiveExperimentStatus('paused')).toBe(true);
    expect(isActiveExperimentStatus('complete')).toBe(false);
  });

  it('Given completedAt set, when running/paused helpers run, then both return false', () => {
    /**
     * Scenario: Timestamp completion short-circuits activity helpers.
     * Slice: 44 Phase B — experimentStatus
     */
    // -- Given / When / Then --
    expect(isRunningExperimentStatus('running', '2026-07-27T01:00:00Z')).toBe(false);
    expect(isPausedExperimentStatus('paused', '2026-07-27T01:00:00Z')).toBe(false);
    expect(isTerminalExperimentStatus(undefined)).toBe(false);
  });

  it('Given undefined runs, when summarized, then expected falls back to zero', () => {
    /**
     * Scenario: Missing runs and expected count yield empty summary.
     * Slice: 44 Phase B — experimentStatus
     */
    // -- Given / When --
    const actual = summarizeExperimentRuns(undefined, undefined);

    // -- Then --
    expect(actual).toEqual({
      expected: 0,
      started: 0,
      complete: 0,
      failed: 0,
      interrupted: 0,
      neverStarted: 0,
      inProgress: 0,
    });
  });

  it('Given retrieval_method only, when displayed, then method string is returned', () => {
    /**
     * Scenario: Legacy method without model uses retrieval_method alone.
     * Slice: 44 Phase B — experimentStatus
     */
    // -- Given --
    const methodOnly = run(Phase.COMPLETE, {
      retrievers: undefined,
      retrieval_method: RetrievalMethod.HYBRID,
      retrieval_model: undefined,
      retrieval_provider: undefined,
    });

    // -- When --
    const actual = displayRetrievers(methodOnly);

    // -- Then --
    expect(actual).toEqual(['hybrid']);
  });

  it('Given reranker without provider model, when displayed, then type alone is returned', () => {
    /**
     * Scenario: Incomplete reranker config skips provider:model suffix.
     * Slice: 44 Phase B — experimentStatus
     */
    // -- Given --
    const incomplete = run(Phase.COMPLETE, {
      retrievers: [{ type: RetrieverType.RERANKER }],
    });

    // -- When --
    const actual = displayRetrievers(incomplete);

    // -- Then --
    expect(actual).toEqual(['reranker']);
  });

  it('Given new retriever format, when displayed, then type and optional model label appear', () => {
    /**
     * Scenario: Unified retrievers render a human-readable label.
     * Slice: 44 — frontend coverage gate (experimentStatus).
     * Given a cross_encoder retriever with provider and model,
     * When displayRetrievers formats the run,
     * Then the label includes type, provider, and model.
     */
    // -- Given --
    const runWithRetriever = run(Phase.COMPLETE, {
      retrievers: [
        {
          type: RetrieverType.CROSS_ENCODER,
          provider: 'local',
          model: 'cross-encoder/ms-marco-MiniLM-L-6-v2',
        },
      ],
    });

    // -- When --
    const actual = displayRetrievers(runWithRetriever);

    // -- Then --
    expect(actual).toEqual([
      'cross_encoder (local:cross-encoder/ms-marco-MiniLM-L-6-v2)',
    ]);
  });

  it('Given legacy retrieval_model fields, when displayed, then reranker label is synthesized', () => {
    /**
     * Scenario: Old format still produces a readable retriever line.
     * Slice: 44 — frontend coverage gate (experimentStatus).
     * Given retrieval_provider voyage and a retrieval_model without retrievers[],
     * When displayRetrievers formats the run,
     * Then a voyage reranker label is returned.
     */
    // -- Given --
    const legacyRun = run(Phase.COMPLETE, {
      retrievers: undefined,
      retrieval_provider: 'voyage',
      retrieval_model: 'rerank-2.5-lite',
    });

    // -- When --
    const actual = displayRetrievers(legacyRun);

    // -- Then --
    expect(actual).toEqual(['reranker (voyage:rerank-2.5-lite)']);
  });

  it('Given unified reranker retrievers, when displayed, then provider model label is used', () => {
    /**
     * Scenario: New retrievers[] format with reranker type.
     * Slice: 44 Phase B — experimentStatus
     */
    // -- Given --
    const modern = run(Phase.COMPLETE, {
      retrievers: [
        {
          type: RetrieverType.CROSS_ENCODER,
          provider: 'local',
          model: 'cross-encoder/ms-marco-MiniLM-L-6-v2',
        },
      ],
    });

    // -- When --
    const actual = displayRetrievers(modern);

    // -- Then --
    expect(actual[0]).toContain('cross_encoder');
    expect(actual[0]).toContain('local:');
  });

  it('Given dense-only retrievers entry, when displayed, then type alone is returned', () => {
    /**
     * Scenario: Traditional dense retriever needs no provider suffix.
     * Slice: 44 Phase B — experimentStatus
     */
    // -- Given --
    const dense = run(Phase.COMPLETE, {
      retrievers: [{ type: RetrieverType.DENSE }],
      retrieval_method: undefined,
      retrieval_model: undefined,
      retrieval_provider: undefined,
    });

    // -- When --
    const actual = displayRetrievers(dense);

    // -- Then --
    expect(actual).toEqual(['dense']);
  });

  it('Given no retriever fields, when displayed, then dense is the default', () => {
    /**
     * Scenario: Empty legacy run defaults to dense.
     * Slice: 44 Phase B — experimentStatus
     */
    // -- Given --
    const empty = run(Phase.COMPLETE, {
      retrievers: undefined,
      retrieval_method: undefined,
      retrieval_model: undefined,
      retrieval_provider: undefined,
    });

    // -- When --
    const actual = displayRetrievers(empty);

    // -- Then --
    expect(actual).toEqual(['dense']);
  });

  it('Given local legacy retrieval_model, when displayed, then cross_encoder label is used', () => {
    /**
     * Scenario: Non-voyage legacy provider maps to cross_encoder.
     * Slice: 44 Phase B — experimentStatus
     */
    // -- Given --
    const legacyLocal = run(Phase.COMPLETE, {
      retrievers: undefined,
      retrieval_provider: 'local',
      retrieval_model: 'cross-encoder/ms-marco-MiniLM-L-6-v2',
    });

    // -- When --
    const actual = displayRetrievers(legacyLocal);

    // -- Then --
    expect(actual[0]).toContain('cross_encoder');
  });
});
