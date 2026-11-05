/**
 * Pure adapter: maps an exported `DemoRun` onto the props the existing explorer components expect
 * (`PhaseIndicator`, `BestParamsCard`, `DetailedResultsTab`). No I/O, no network.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part B - run replay
 */
import { Phase } from '../types'
import type { DetailedResult, RankedConfig } from '../types'
import { REPLAY_PHASES } from './demoResults'
import type { DemoResults, DemoRun } from './demoResults'

export type ReplayPhase = (typeof REPLAY_PHASES)[number]

/** Replay stage name (upper case, as exported) to the dashboard `Phase` enum. */
export function toPhase(stage: ReplayPhase): Phase {
  // eslint-disable-next-line security/detect-object-injection -- keyed by the typed ReplayPhase union
  return Phase[stage]
}

/** Run to resolve when none is requested: the primary store's best run, else the first run. */
export function defaultRun(results: DemoResults): DemoRun | undefined {
  const primary = Object.values(results.stores).find((store) => store.is_primary)
  return results.runs.find((run) => run.run_id === primary?.best_run_id) ?? results.runs[0]
}

/** The run with `runId`, or the default run when `runId` is missing or unknown. */
export function resolveRun(results: DemoResults, runId?: string): DemoRun | undefined {
  return results.runs.find((run) => run.run_id === runId) ?? defaultRun(results)
}

/** Ranked-config view of one run, for `BestParamsCard`. Scores are the export's normalised similarity scores. */
export function toRankedConfig(run: DemoRun): RankedConfig {
  return {
    rank: run.rank,
    database_provider: run.store,
    embedding_provider: run.embedding_provider,
    embedding_model: run.embedding_model,
    chunking_method: run.chunking_method,
    chunk_size: run.chunk_size,
    overlap: run.overlap,
    padding: run.padding,
    max_score: run.max_score,
    avg_score: run.avg_score,
    query_avg_score: run.query_avg_score,
    result_count: run.result_count,
    retrieval_method: run.retrieval_method,
    retrieval_provider: run.rerank_provider,
  }
}

/** Chunk-level rows for `DetailedResultsTab`; `rank` is the position within the run's exported top results. */
export function toDetailedResults(run: DemoRun): DetailedResult[] {
  return run.top_results.map((top, index) => ({
    rank: index + 1,
    score: top.score,
    raw_score: top.raw_score,
    dense_score: top.raw_score,
    rerank_score: null,
    database_provider: run.store,
    embedding_provider: run.embedding_provider,
    embedding_model: run.embedding_model,
    chunking_method: run.chunking_method,
    chunk_size: run.chunk_size,
    overlap: run.overlap,
    padding: run.padding,
    chunk_text: top.chunk_text,
    query_text: top.query_text,
    run_id: run.run_id,
    retrieval_method: top.retrieval_method,
  }))
}

/** Picker label, e.g. "redis - rank 1 - all-MiniLM-L6-v2 512/64/0 dense". */
export function runLabel(run: DemoRun): string {
  const dims = `${run.chunk_size}/${run.overlap}/${run.padding}`
  return `${run.store} - rank ${run.rank} - ${run.embedding_model} ${dims} ${run.retrieval_method}`
}

/** Recorded total only, in seconds with one decimal. */
export function formatElapsed(elapsedMs: number): string {
  return `${(elapsedMs / 1000).toFixed(1)} s`
}
