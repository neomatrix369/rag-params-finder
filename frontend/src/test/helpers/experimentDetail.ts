/**
 * Shared experiment-detail fixtures (runs and detail payload).
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
