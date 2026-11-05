/**
 * Tests for the pure replay adapter: DemoRun to the props the explorer components need.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part B - run replay (adapter)
 */
import { describe, expect, it } from 'vitest'
import { Phase } from '../types'
import { REPLAY_PHASES } from './demoResults'
import {
  defaultRun,
  formatElapsed,
  resolveRun,
  runLabel,
  toDetailedResults,
  toPhase,
  toRankedConfig,
} from './replayAdapter'
import { makeDemoResults, makeDemoRun } from '../test/helpers/demoResults'

describe('replayAdapter', () => {
  it('maps every replay stage to a dashboard phase, in order', () => {
    /**
     * Scenario: Replay stages are the same pipeline phases the dashboard already knows.
     * Slice: 56 Part B - run replay
     */
    // -- Given --
    const stages = [...REPLAY_PHASES]

    // -- When --
    const phases = stages.map(toPhase)

    // -- Then --
    expect(phases).toEqual([
      Phase.QUEUED, Phase.PARSING, Phase.CHUNKING, Phase.EMBEDDING,
      Phase.STORING, Phase.QUERYING, Phase.RERANKING, Phase.COMPLETE,
    ])
  })

  it('defaults to the primary store best run, else the first run, else nothing', () => {
    /**
     * Scenario: Default run selection and its fallbacks.
     * Slice: 56 Part B - run replay
     */
    // -- Given --
    const results = makeDemoResults()
    const noPrimary = makeDemoResults({
      stores: { redis: { ...results.stores.redis, is_primary: false } },
    })

    // -- When / Then --
    expect(defaultRun(results)?.run_id).toBe('run-redis-best')
    expect(defaultRun(noPrimary)?.run_id).toBe(results.runs[0].run_id)
    expect(defaultRun(makeDemoResults({ runs: [], stores: {} }))).toBeUndefined()
  })

  it('resolves a known run id, and falls back to the default for unknown or missing ids', () => {
    /**
     * Scenario: resolveRun never throws on a stale run id.
     * Slice: 56 Part B - run replay
     */
    // -- Given --
    const results = makeDemoResults()

    // -- When / Then --
    expect(resolveRun(results, 'run-pg-best')?.store).toBe('postgres')
    expect(resolveRun(results, 'nope')?.run_id).toBe('run-redis-best')
    expect(resolveRun(results)?.run_id).toBe('run-redis-best')
  })

  it('maps a run to a ranked config without altering any recorded value', () => {
    /**
     * Scenario: BestParamsCard input carries the exported values as-is.
     * Slice: 56 Part B - run replay
     */
    // -- Given --
    const run = makeDemoRun({ store: 'postgres', rank: 4, padding: 2, rerank_provider: 'voyage' })

    // -- When --
    const config = toRankedConfig(run)

    // -- Then --
    expect(config).toMatchObject({
      rank: 4,
      database_provider: 'postgres',
      embedding_model: run.embedding_model,
      chunk_size: run.chunk_size,
      overlap: run.overlap,
      padding: 2,
      max_score: run.max_score,
      avg_score: run.avg_score,
      query_avg_score: run.query_avg_score,
      retrieval_method: run.retrieval_method,
      retrieval_provider: 'voyage',
    })
  })

  it('maps top results to detailed rows ranked by exported position', () => {
    /**
     * Scenario: DetailedResultsTab rows keep text, scores and config of the run.
     * Slice: 56 Part B - run replay
     */
    // -- Given --
    const run = makeDemoRun()

    // -- When --
    const rows = toDetailedResults(run)

    // -- Then --
    expect(rows.map((row) => row.rank)).toEqual([1, 2])
    expect(rows[0]).toMatchObject({
      score: 100,
      raw_score: 0.91,
      dense_score: 0.91,
      rerank_score: null,
      run_id: run.run_id,
      chunk_text: run.top_results[0].chunk_text,
      query_text: run.top_results[0].query_text,
      database_provider: 'redis',
      chunk_size: 512,
    })
  })

  it('formats labels and totals', () => {
    /**
     * Scenario: Picker label and recorded total.
     * Slice: 56 Part B - run replay
     */
    // -- Given / When / Then --
    expect(runLabel(makeDemoRun())).toBe('redis - rank 1 - all-MiniLM-L6-v2 512/64/0 dense')
    expect(formatElapsed(12500)).toBe('12.5 s')
  })
})
