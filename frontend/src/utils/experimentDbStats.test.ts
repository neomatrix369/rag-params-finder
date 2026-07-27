/**
 * Tests for experimentDbStats helpers.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 Phase B — toExperimentDbStatsSummary + findDbStatsInGroups
 */
import { describe, expect, it } from 'vitest';
import type { ExperimentDbStats, ExperimentDbStatsSummary } from '../types';
import { findDbStatsInGroups, toExperimentDbStatsSummary } from './experimentDbStats';

const ANY_DB_STATS: ExperimentDbStats = {
  database_provider: 'mongodb',
  collection_name: 'chunks',
  cluster_host: 'localhost',
  total_chunks: 10,
  unique_documents: 1,
  embedding_models: ['all-MiniLM-L6-v2'],
  embedding_dimensions: [384],
  index_names: ['vector_index_384'],
  retrieval_methods: ['dense'],
  chunking_methods: ['fixed'],
  chunking_breakdown: { fixed: 10 },
  estimated_storage_mb: 1.2,
  estimated_embedding_mb: 0.8,
  estimated_metadata_mb: 0.4,
  runs_with_data: 1,
  avg_chunks_per_run: 10,
  total_results: 5,
  unique_queries: 2,
  run_breakdown: [],
};

describe('experimentDbStats', () => {
  it('Given experiment and db stats, when summarized, then fields are merged', () => {
    /**
     * Scenario: Summary combines experiment metadata with vector DB stats.
     * Slice: 44 Phase B — experimentDbStats
     *
     * Given a minimal experiment and db-stats payload,
     * When toExperimentDbStatsSummary merges them,
     * Then experiment_id and total_chunks appear on the summary.
     */
    // -- Given --
    const experiment = {
      experiment_id: 'exp-1',
      experiment_name: 'demo',
      status: 'complete' as const,
      created_at: '2026-07-27T00:00:00Z',
    };

    // -- When --
    const actual = toExperimentDbStatsSummary(experiment, ANY_DB_STATS);

    // -- Then --
    expect(actual.experiment_id).toBe('exp-1');
    expect(actual.total_chunks).toBe(10);
    expect(actual.database_provider).toBe('mongodb');
  });

  it('Given grouped stats, when finding by id, then matching row is returned', () => {
    /**
     * Scenario: Lookup finds an experiment row inside vector-db groups.
     * Slice: 44 Phase B — experimentDbStats
     *
     * Given one group containing exp-hit,
     * When findDbStatsInGroups searches for exp-hit,
     * Then the matching summary is returned.
     */
    // -- Given --
    const hit: ExperimentDbStatsSummary = {
      experiment_id: 'exp-hit',
      experiment_name: 'hit',
      status: 'complete',
      created_at: '2026-07-27T00:00:00Z',
      ...ANY_DB_STATS,
    };
    const groups = [{ experiments: [hit] }];

    // -- When --
    const actual = findDbStatsInGroups(groups, 'exp-hit');

    // -- Then --
    expect(actual?.experiment_name).toBe('hit');
  });

  it('Given grouped stats, when id is missing, then undefined is returned', () => {
    /**
     * Scenario: Missing experiment id yields undefined.
     * Slice: 44 Phase B — experimentDbStats
     *
     * Given groups without exp-missing,
     * When findDbStatsInGroups searches for it,
     * Then undefined is returned.
     */
    // -- Given --
    const groups = [{ experiments: [] as ExperimentDbStatsSummary[] }];

    // -- When --
    const actual = findDbStatsInGroups(groups, 'exp-missing');

    // -- Then --
    expect(actual).toBeUndefined();
  });
});
