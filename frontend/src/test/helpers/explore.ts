/**
 * Shared Search Explorer ranked-config / detailed-result fixtures.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-07-28
 * Scope: Slice 45 — FE shared test helpers
 */
import type { DetailedResult, RankedConfig } from '../../types';

export const EXPLORE_RETRIEVAL_METHODS = ['dense', 'sparse', 'hybrid'] as const;
export const EXPLORE_CHUNKING_METHODS = ['fixed', 'recursive', 'token', 'sentence', 'semantic'];
export const EXPLORE_EMBEDDING_MODELS = ['voyage-3.5-lite', 'voyage-3.5', 'all-MiniLM-L6-v2'];
export const EXPLORE_CHUNK_SIZES = [256, 512, 768, 1024];
export const EXPLORE_OVERLAPS = [20, 50, 80];
export const EXPLORE_PADDINGS = [0, 10, 20];

/** Ranked hyperparameter row; `rank` drives deterministic cycling of dimensions. */
export function buildConfig(rank: number, overrides: Partial<RankedConfig> = {}): RankedConfig {
  const idx = rank - 1;
  return {
    rank,
    database_provider: 'mongodb',
    embedding_provider: 'voyage',
    embedding_model: EXPLORE_EMBEDDING_MODELS[idx % EXPLORE_EMBEDDING_MODELS.length],
    chunking_method: EXPLORE_CHUNKING_METHODS[idx % EXPLORE_CHUNKING_METHODS.length],
    chunk_size: EXPLORE_CHUNK_SIZES[idx % EXPLORE_CHUNK_SIZES.length],
    overlap: EXPLORE_OVERLAPS[idx % EXPLORE_OVERLAPS.length],
    padding: EXPLORE_PADDINGS[idx % EXPLORE_PADDINGS.length],
    max_score: Math.max(10, 90 - idx * 3),
    avg_score: Math.max(5, 80 - idx * 3),
    query_avg_score: Math.max(5, 82 - idx * 3),
    result_count: 5 + idx,
    retrieval_method: EXPLORE_RETRIEVAL_METHODS[idx % EXPLORE_RETRIEVAL_METHODS.length],
    retrieval_provider: idx % 2 === 0 ? 'local' : 'voyage',
    ...overrides,
  };
}

/** Detailed chunk hit row for the explorer results tab. */
export function buildDetailedResult(
  rank: number,
  overrides: Partial<DetailedResult> = {},
): DetailedResult {
  const idx = rank - 1;
  return {
    rank,
    score: Math.max(10, 95 - idx * 4),
    raw_score: Math.max(0.1, 0.95 - idx * 0.04),
    database_provider: 'mongodb',
    embedding_provider: 'voyage',
    embedding_model: EXPLORE_EMBEDDING_MODELS[idx % EXPLORE_EMBEDDING_MODELS.length],
    chunking_method: EXPLORE_CHUNKING_METHODS[idx % EXPLORE_CHUNKING_METHODS.length],
    chunk_size: EXPLORE_CHUNK_SIZES[idx % EXPLORE_CHUNK_SIZES.length],
    overlap: EXPLORE_OVERLAPS[idx % EXPLORE_OVERLAPS.length],
    padding: EXPLORE_PADDINGS[idx % EXPLORE_PADDINGS.length],
    chunk_text: `Chunk text for result ${rank}. Short filler content for this result.`,
    query_text: `Sample query number ${rank}?`,
    run_id: `run-${rank}`,
    dense_score: Math.max(0.1, 0.9 - idx * 0.03),
    retrieval_method: EXPLORE_RETRIEVAL_METHODS[idx % EXPLORE_RETRIEVAL_METHODS.length],
    retrieval_provider: idx % 2 === 0 ? 'local' : 'voyage',
    ...overrides,
  };
}
