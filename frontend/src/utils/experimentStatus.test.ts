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
  bayesianNotStartedCount,
  bayesianTotalsLine,
  detailDenominator,
  selectableExperimentIds,
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

describe('bayesianNotStartedCount', () => {
  it('Given planned, attempted (incl. interrupted) and discarded trials, when counted, then not started is the single remainder', () => {
    /**
     * Scenario: Not started is planned minus attempted minus discarded, computed once.
     * Slice: 67D1 — shared helper for list and detail (finding D).
     */
    // -- Given --
    const trials = { planned: 20, attempted: 12, discarded: 3 };

    // -- When --
    const notStarted = bayesianNotStartedCount(trials.planned, trials.attempted, trials.discarded);

    // -- Then --
    expect(notStarted).toBe(5);
  });

  it('Given attempted plus discarded above planned, when counted, then it floors at zero', () => {
    /**
     * Scenario: Over-reported trials never produce a negative count.
     * Slice: 67D1 — shared helper floor.
     */
    // -- Given / When --
    const notStarted = bayesianNotStartedCount(10, 9, 4);

    // -- Then --
    expect(notStarted).toBe(0);
  });

  it('Given the same inputs, when counted repeatedly, then the output is identical and inputs are untouched', () => {
    /**
     * Scenario: The helper is a pure function of its arguments (no clock, randomness or I/O).
     * Slice: 67D1 — determinism requirement for slice 67 numbers.
     */
    // -- Given --
    const args = [20, 12, 3] as const;

    // -- When --
    const results = Array.from({ length: 5 }, () => bayesianNotStartedCount(...args));

    // -- Then --
    expect(new Set(results)).toEqual(new Set([5]));
    expect(args).toEqual([20, 12, 3]);
  });
});

describe('bayesianTotalsLine', () => {
  it('Given planned, attempted, discarded and not-started trials that add up, when explained, then the line states the sum with no caveat', () => {
    /**
     * Scenario: Total = attempted + discarded + not started, with Discarded shown separately from runs.
     * Slice: 67D — finding F, Bayesian cards reconcile.
     */
    // -- Given / When --
    const line = bayesianTotalsLine({ planned: 20, attempted: 13, discarded: 4, notStarted: 3 });

    // -- Then --
    expect(line).toBe('Total 20 = 13 attempted + 4 discarded + 3 not started. Discarded trials are not runs.');
  });

  it('Given parts that do not add up to planned, when explained, then the line says so instead of a false equals', () => {
    /**
     * Scenario: A stale summary never prints a sum that is false.
     * Slice: 67D — finding F.
     */
    // -- Given / When --
    const line = bayesianTotalsLine({ planned: 20, attempted: 18, discarded: 4, notStarted: 0 });

    // -- Then --
    expect(line).toBe('Total 20; attempted 18, discarded 4, not started 0 (parts do not add up yet). Discarded trials are not runs.');
  });
});

describe('bayesianTotalsLine with runs in flight', () => {
  it('Given runs still executing, when explained, then they are annotated inside attempted and the sum still holds', () => {
    /**
     * Scenario: a running Bayesian sweep has in-progress runs that count as attempted.
     * Slice: 67D — line and cards agree mid-run.
     */
    // -- Given / When --
    const line = bayesianTotalsLine({ planned: 20, attempted: 6, discarded: 0, notStarted: 14, inProgress: 2 });

    // -- Then --
    expect(line).toBe('Total 20 = 6 attempted (2 in progress) + 0 discarded + 14 not started. Discarded trials are not runs.');
  });
});

describe('detailDenominator', () => {
  it('Given a Bayesian or a grid sweep, when the denominator is chosen, then Bayesian uses planned trials and grid uses expected runs', () => {
    /**
     * Scenario: one denominator for every Detail-screen count.
     * Slice: 67D - Total tile, ring, subtitle and totals line share it.
     */
    // -- Given / When / Then --
    expect(detailDenominator({ isBayesian: true, plannedTrials: 10, expectedRuns: 12 })).toBe(10);
    expect(detailDenominator({ isBayesian: false, plannedTrials: 10, expectedRuns: 12 })).toBe(12);
  });
});

describe('selectableExperimentIds', () => {
  it('Given running and finished experiments, when selecting for bulk actions, then running ones are excluded in order', () => {
    /**
     * Scenario: Bulk select skips running experiments.
     * Slice: 67D — replaces inline filter-and-count in ExperimentsScreen.
     */
    // -- Given --
    const experiments = [
      { experiment_id: 'a', status: 'complete' as const },
      { experiment_id: 'b', status: 'running' as const },
      { experiment_id: 'c', status: 'failed' as const },
    ];

    // -- When / Then --
    expect(selectableExperimentIds(experiments)).toEqual(['a', 'c']);
  });
});
