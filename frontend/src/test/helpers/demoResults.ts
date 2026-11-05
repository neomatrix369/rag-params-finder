/**
 * Shared demo-results fixtures for Vitest suites (SLICE-56 meetup demo kit).
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 — builders for `DemoResults` / `DemoRun`
 */
import type { DemoResults, DemoRun, DemoStoreSummary } from '../../demo/demoResults'

/** One valid exported run; override any field via Partial. */
export function makeDemoRun(overrides: Partial<DemoRun> = {}): DemoRun {
  return {
    run_id: 'run-redis-best',
    experiment_id: 'exp-redis',
    experiment_name: 'Redis Pell sweep',
    store: 'redis',
    group_id: 'group-a',
    rank: 1,
    store_rank: 1,
    roles: [],
    embedding_model: 'all-MiniLM-L6-v2',
    embedding_provider: 'local',
    embedding_dimensions: 384,
    chunking_method: 'recursive',
    chunk_size: 512,
    overlap: 64,
    padding: 0,
    retrieval_method: 'dense',
    retrieval_model: null,
    rerank_provider: 'local',
    max_score: 100,
    avg_score: 72.5,
    query_avg_score: 80,
    result_count: 2,
    phase: 'complete',
    elapsed_ms: 12500,
    created_at: '2026-11-01T10:00:00Z',
    updated_at: '2026-11-01T10:00:12Z',
    top_results: [
      {
        query_text: 'What is the Pell Grant deadline?',
        score: 100,
        raw_score: 0.91,
        chunk_text: 'Applications for the Pell Grant close on June 30.',
        retrieval_method: 'dense',
      },
      {
        query_text: 'What is the Pell Grant deadline?',
        score: 55,
        raw_score: 0.62,
        chunk_text: 'Federal aid overview and eligibility notes.',
        retrieval_method: 'dense',
      },
    ],
    ...overrides,
  }
}

function summary(best: string, median: string, worst: string, isPrimary: boolean, count: number): DemoStoreSummary {
  return { is_primary: isPrimary, run_count: count, best_run_id: best, median_run_id: median, worst_run_id: worst }
}

/** Multi-store export: primary `redis` plus `postgres` and `mongodb` runs sharing group ids. */
export function makeDemoResults(overrides: Partial<DemoResults> = {}): DemoResults {
  const redisBest = makeDemoRun()
  const redisWorst = makeDemoRun({
    run_id: 'run-redis-worst',
    group_id: 'group-b',
    rank: 5,
    store_rank: 2,
    chunk_size: 128,
    max_score: 20,
    avg_score: 10,
    query_avg_score: 12,
    elapsed_ms: 9000,
    top_results: [
      {
        query_text: 'What is the Pell Grant deadline?',
        score: 20,
        raw_score: 0.41,
        chunk_text: 'Unrelated campus parking guidance.',
        retrieval_method: 'dense',
      },
    ],
    result_count: 1,
  })
  const pgBest = makeDemoRun({
    run_id: 'run-pg-best',
    experiment_id: 'exp-pg',
    experiment_name: 'Postgres Pell sweep',
    store: 'postgres',
    rank: 2,
    store_rank: 1,
    roles: ['best'],
    max_score: 95,
    elapsed_ms: 15000,
  })
  const pgWorst = makeDemoRun({
    run_id: 'run-pg-worst',
    experiment_id: 'exp-pg',
    experiment_name: 'Postgres Pell sweep',
    store: 'postgres',
    group_id: 'group-b',
    rank: 6,
    store_rank: 2,
    roles: ['worst'],
    chunk_size: 128,
    max_score: 18,
  })
  const mongoBest = makeDemoRun({
    run_id: 'run-mongo-best',
    experiment_id: 'exp-mongo',
    experiment_name: 'MongoDB Pell sweep',
    store: 'mongodb',
    rank: 3,
    store_rank: 1,
    roles: ['best'],
    max_score: 90,
    elapsed_ms: 18000,
  })
  const mongoWorst = makeDemoRun({
    run_id: 'run-mongo-worst',
    experiment_id: 'exp-mongo',
    experiment_name: 'MongoDB Pell sweep',
    store: 'mongodb',
    group_id: 'group-b',
    rank: 7,
    store_rank: 2,
    roles: ['worst'],
    chunk_size: 128,
    max_score: 15,
  })
  const chunk = (run_id: string, position: number, score: number) => ({
    run_id,
    position,
    score,
    raw_score: score / 100,
    chunk_text: `chunk ${position} for ${run_id}`,
  })
  return {
    schema_version: 1,
    manifest: {
      schema_version: 1,
      inputs: {
        databases: [{ path: 'demo.sqlite', sha256: 'abc' }],
        questions: { path: 'questions.json', sha256: 'def' },
      },
      ranking: { fields: ['max_score'], source: 'run results', score: 'similarity score', tiebreak_note: 'none' },
      selection_rule: 'best, median and worst per store',
      counts: { runs: 6 },
      exclusions: [],
      generated_by: 'test',
    },
    stores: {
      redis: summary('run-redis-best', 'run-redis-best', 'run-redis-worst', true, 2),
      postgres: summary('run-pg-best', 'run-pg-best', 'run-pg-worst', false, 2),
      mongodb: summary('run-mongo-best', 'run-mongo-best', 'run-mongo-worst', false, 2),
    },
    runs: [redisBest, pgBest, mongoBest, redisWorst, pgWorst, mongoWorst],
    story: {
      basis: 'similarity score',
      run_count: 6,
      best: { run_id: 'run-redis-best', rank: 1, max_score: 100, query_avg_score: 80, avg_score: 72.5 },
      median: { run_id: 'run-pg-best', rank: 2, max_score: 95, query_avg_score: 80, avg_score: 72.5 },
      worst: { run_id: 'run-mongo-worst', rank: 7, max_score: 15, query_avg_score: 80, avg_score: 72.5 },
      spread: { max_score: 85, query_avg_score: 68 },
      question: {
        text: 'What is the Pell Grant deadline?',
        focus: 'deadlines',
        best_top1: 100,
        worst_top1: 15,
        gap: 85,
      },
      best_top_chunks: [chunk('run-redis-best', 1, 100)],
      worst_top_chunks: [chunk('run-mongo-worst', 1, 15)],
    },
    ...overrides,
  }
}
