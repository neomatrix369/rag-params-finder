/**
 * Types for `docs/about/demo-results.json` (schema_version 1), written by
 * `scripts/demo/export_demo_results.py`. Hand-mirrored, like `types/index.ts`.
 *
 * Scores are similarity scores min-max normalised across the exported runs
 * (0-100). They say nothing about correctness. Timings are indicative only.
 */

export interface DemoTopResult {
  query_text: string
  score: number
  raw_score: number
  chunk_text: string
  retrieval_method: string
}

export interface DemoRun {
  run_id: string
  experiment_id: string
  experiment_name: string
  store: string
  /** Same-config runs across stores share a group_id (config key minus provider). */
  group_id: string
  /** Rank across the whole export. */
  rank: number
  /** Rank within this run's store. */
  store_rank: number
  /** e.g. "best" | "median" | "worst" for non-primary stores. */
  roles: string[]
  embedding_model: string
  embedding_provider: string
  embedding_dimensions: number
  chunking_method: string
  chunk_size: number
  overlap: number
  padding: number
  retrieval_method: string
  retrieval_model: string | null
  rerank_provider: string
  max_score: number
  avg_score: number
  query_avg_score: number
  result_count: number
  /** Final phase, e.g. "complete". */
  phase: string
  /** Total elapsed time only; per-stage durations were never recorded. */
  elapsed_ms: number
  created_at: string
  updated_at: string
  top_results: DemoTopResult[]
}

export interface DemoStoreSummary {
  is_primary: boolean
  run_count: number
  best_run_id: string
  median_run_id: string
  worst_run_id: string
}

export interface DemoStoryRunRef {
  run_id: string
  rank: number
  max_score: number
  query_avg_score: number
  avg_score: number
}

export interface DemoStoryChunk {
  run_id: string
  position: number
  score: number
  raw_score: number
  chunk_text: string
}

export interface DemoStory {
  basis: string
  run_count: number
  best: DemoStoryRunRef
  median: DemoStoryRunRef
  worst: DemoStoryRunRef
  /** best - worst, per metric (the exporter reports both normalised metrics). */
  spread: { max_score: number; query_avg_score: number }
  question: { text: string; focus: string; best_top1: number; worst_top1: number; gap: number }
  best_top_chunks: DemoStoryChunk[]
  worst_top_chunks: DemoStoryChunk[]
}

export interface DemoExclusion {
  scope: string
  reason: string
  count: number
  ids: string[]
}

export interface DemoManifest {
  schema_version: number
  inputs: {
    databases: { path: string; sha256: string }[]
    questions: { path: string; sha256: string }
  }
  ranking: { fields: string[]; source: string; score: string; tiebreak_note: string }
  selection_rule: string
  counts: Record<string, number>
  exclusions: DemoExclusion[]
  generated_by: string
}

export interface DemoResults {
  schema_version: number
  manifest: DemoManifest
  /** Keyed by store name; the primary store is the Redis 8 one. */
  stores: Record<string, DemoStoreSummary>
  runs: DemoRun[]
  story: DemoStory
}

/** The fixed pipeline stages the replay steps through, in order. */
export const REPLAY_PHASES = [
  'QUEUED',
  'PARSING',
  'CHUNKING',
  'EMBEDDING',
  'STORING',
  'QUERYING',
  'RERANKING',
  'COMPLETE',
] as const
