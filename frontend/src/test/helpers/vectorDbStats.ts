/**
 * Shared vector-DB stats group fixtures for Vitest suites.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-07-28
 * Scope: Slice 45 — FE shared test helpers
 */
import type { VectorDbStatsGroup } from '../../types';

/** Cluster/group card fixture; totals and host are overridable. */
export function vectorDbGroup(overrides: Partial<VectorDbStatsGroup> = {}): VectorDbStatsGroup {
  return {
    vector_db_id: 'mongodb::chunks',
    database_provider: 'mongodb',
    collection_name: 'chunks',
    cluster_host: null,
    index_names: ['vector_index_1024'],
    embedding_dimensions: [1024],
    totals: {
      experiment_count: 1,
      total_chunks: 120,
      total_results: 42,
      estimated_storage_mb: 5,
      estimated_embedding_mb: 4,
      estimated_metadata_mb: 1,
    },
    experiments: [],
    ...overrides,
  };
}
