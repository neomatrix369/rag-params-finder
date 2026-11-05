/**
 * Types for `docs/about/walkthru-results.json` (schema_version 1), written by
 * `scripts/walkthru/export_walkthru_results.py`. Hand-mirrored, like `types/index.ts`.
 *
 * Scores are similarity scores min-max normalised across the exported runs
 * (0-100). They say nothing about correctness. Timings are indicative only.
 */

export interface WalkthruTopResult {
  query_text: string
  score: number
  raw_score: number
  chunk_text: string
  retrieval_method: string
}

export interface WalkthruRun {
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
  /** Null for runs whose embedding dimensions were not recorded. */
  embedding_dimensions: number | null
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
  top_results: WalkthruTopResult[]
}

export interface WalkthruStoreSummary {
  is_primary: boolean
  run_count: number
  best_run_id: string
  median_run_id: string
  worst_run_id: string
}

export interface WalkthruStoryRunRef {
  run_id: string
  rank: number
  max_score: number
  query_avg_score: number
  avg_score: number
}

export interface WalkthruStoryChunk {
  run_id: string
  position: number
  score: number
  raw_score: number
  chunk_text: string
}

export interface DemoQuestion {
  text: string
  focus: string
  best_top1: number
  worst_top1: number
  gap: number
}

export interface WalkthruStory {
  basis: string
  run_count: number
  best: WalkthruStoryRunRef
  median: WalkthruStoryRunRef
  worst: WalkthruStoryRunRef
  /** best - worst, per metric (the exporter reports both normalised metrics). */
  spread: { max_score: number; query_avg_score: number }
  /** Null when the best and worst runs share no common question (no per-question comparison). */
  question: DemoQuestion | null
  best_top_chunks: WalkthruStoryChunk[]
  worst_top_chunks: WalkthruStoryChunk[]
}

export interface WalkthruExclusion {
  scope: string
  reason: string
  count: number
  ids: string[]
}

/** A sweep that contributed some but not all of its runs (e.g. mid-run at export time). */
export interface DemoPartialExperiment {
  experiment_id: string
  experiment_name: string
  runs_exported: number
  runs_not_complete: number
  runs_total: number
}

export interface WalkthruManifest {
  schema_version: number
  inputs: {
    databases: { path: string; sha256: string }[]
    questions: { path: string; sha256: string }
    /** Export-time selection filters; optional because older exports / fixtures omit it. */
    filters?: { data_path_contains: string[] }
  }
  ranking: { fields: string[]; source: string; score: string; tiebreak_note: string }
  selection_rule: string
  counts: Record<string, number>
  exclusions: WalkthruExclusion[]
  /** Partially-exported sweeps; optional because older exports / fixtures omit it. */
  partial_experiments?: DemoPartialExperiment[]
  generated_by: string
}

export interface WalkthruResults {
  schema_version: number
  manifest: WalkthruManifest
  /** Keyed by store name; the primary store is the Redis 8 one. */
  stores: Record<string, WalkthruStoreSummary>
  runs: WalkthruRun[]
  story: WalkthruStory
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
