/**
 * Shared experiment-detail fixtures (runs, detail payload, per-experiment db stats).
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-07-28
 * Scope: Slice 45 — FE shared test helpers
 */
import {
  ChunkingMethod,
  Phase,
  RetrievalMethod,
  type Experiment,
  type ExperimentDbStatsSummary,
  type ExperimentStatus,
  type RunStatus,
} from '../../types';

export type DetailFixture = Experiment & { runs: RunStatus[] };

/** Single run row for detail screens / progress metrics. */
export function run(
  experimentId: string,
  index: number,
  phase: Phase,
  overrides: Partial<RunStatus> = {},
): RunStatus {
  return {
    run_id: `${experimentId}-run-${index}`,
    experiment_id: experimentId,
    phase,
    database_provider: 'mongodb',
    embedding_provider: 'local',
    embedding_model: 'test-embedding',
    chunking_method: ChunkingMethod.RECURSIVE,
    chunk_size: 512,
    overlap: 50,
    created_at: '2026-07-18T12:00:00Z',
    updated_at: '2026-07-18T12:01:00Z',
    elapsed_ms: 60_000,
    retrieval_method: RetrievalMethod.DENSE,
    ...overrides,
  };
}

/** Experiment + runs detail payload; `phases` seeds one run each. */
export function detailFixture(
  status: ExperimentStatus,
  phases: Phase[],
  overrides: Partial<DetailFixture> = {},
): DetailFixture {
  const experimentId = `detail-${status}`;
  const base: DetailFixture = {
    experiment_id: experimentId,
    experiment_name: `${status} detail sweep`,
    config: {},
    created_at: '2026-07-18T12:00:00Z',
    status,
    run_count: 3,
    runs: phases.map((phase, index) => run(experimentId, index, phase)),
  };
  return { ...base, ...overrides };
}

/** Empty-ish db-stats summary keyed off a detail fixture (detail-screen default). */
export function dbStats(fixture: DetailFixture): ExperimentDbStatsSummary {
  return dbStatsSummary({
    experiment_id: fixture.experiment_id,
    experiment_name: fixture.experiment_name,
    status: fixture.status,
    created_at: fixture.created_at,
  });
}

export function dbStatsResponse(fixture: DetailFixture): { db_stats: ExperimentDbStatsSummary } {
  return { db_stats: dbStats(fixture) };
}

/** Standalone ExperimentDbStatsSummary builder for stats-card suites. */
export function dbStatsSummary(
  overrides: Partial<ExperimentDbStatsSummary> = {},
): ExperimentDbStatsSummary {
  return {
    experiment_id: 'exp-vdb',
    experiment_name: 'vdb demo',
    status: 'complete',
    created_at: '2026-07-27T00:00:00Z',
    database_provider: 'mongodb',
    collection_name: 'chunks',
    cluster_host: null,
    total_chunks: 0,
    unique_documents: 0,
    embedding_models: [],
    embedding_dimensions: [],
    index_names: [],
    retrieval_methods: [],
    chunking_methods: [],
    chunking_breakdown: {},
    estimated_storage_mb: 0,
    estimated_embedding_mb: 0,
    estimated_metadata_mb: 0,
    runs_with_data: 0,
    avg_chunks_per_run: 0,
    total_results: 0,
    unique_queries: 0,
    run_breakdown: [],
    ...overrides,
  };
}
