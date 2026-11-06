/**
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67G-B - fixed-template Explorer sentences (pure: no clock, I/O or DOM).
 * Vocabulary: run, planned runs, configuration, trial (Bayesian only).
 * The score definitions mirror `server/core/results_analyzer.py`.
 */
import { pluralize } from '../../utils/sweepFormula';

/** "N of M planned runs have results"; Bayesian sweeps say trials; no plan means no denominator. */
export function plannedResultsLine(withResults: number, planned: number | null, isBayesian: boolean): string {
  const verb = withResults === 1 ? 'has' : 'have';
  if (planned === null) return `${pluralize(withResults, 'configuration')} ${verb} results`;
  return `${withResults} of ${pluralize(planned, isBayesian ? 'planned trial' : 'planned run')} ${verb} results`;
}

/**
 * The one definition of "tied": configurations sharing the #1 max score across the whole experiment.
 * The server counts them on `best_params.tied_count`; without it, count the visible configurations.
 */
export function tiedConfigCount(
  best: { max_score: number; tied_count?: number } | null,
  configs: ReadonlyArray<{ max_score: number }>,
): number {
  if (!best) return 0;
  return best.tied_count ?? configs.filter((config) => config.max_score === best.max_score).length;
}

export function tiedExplain(tied: number, maxScore: number): string {
  return `${pluralize(tied, 'configuration')} share the top max score of ${maxScore}%. Ties are broken by query avg, then smaller chunk size, then smaller overlap, then smaller padding.`;
}

export function maxScoreExplain(): string {
  return 'Scores are min-max normalised to 0-100 across every chunk returned in this experiment: 0 is the lowest chunk score seen, 100 the highest (rerank score when a run has one, dense similarity otherwise). Max score is the best single chunk a configuration retrieved for any query.';
}

export function queryAvgExplain(): string {
  return 'Query avg first takes the mean chunk score of each query, then averages those means, so every query counts equally.';
}

export function chunkAvgExplain(): string {
  return 'Chunk avg is the plain mean of every chunk score the configuration returned, so a query with more chunks weighs more.';
}

const topKPhrase = (topKFinal: number | undefined): string =>
  topKFinal === undefined ? 'top_k_final' : `${topKFinal}`;

export function matchesExplain(matches: number, queryCount: number, topKFinal: number | undefined): string {
  const keeps = topKFinal === undefined ? 'a fixed number of chunks per query (top_k_final)' : `at most ${topKFinal} chunks per query (top_k_final)`;
  return `${matches} ${matches === 1 ? 'match' : 'matches'}: each is one retrieved chunk for one query, after the retrieval-method filter. A run keeps ${keeps} from ${pluralize(queryCount, 'query')}.`;
}

export function resultsColumnExplain(topKFinal: number | undefined): string {
  return `Results counts the chunk rows this configuration returned across all queries (at most ${topKPhrase(topKFinal)} per query).`;
}
