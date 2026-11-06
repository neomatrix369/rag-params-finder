/**
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67G-B - fixed-template Explorer sentences and the single tie-count definition.
 */
import { describe, expect, it } from 'vitest';
import {
  chunkAvgExplain,
  maxScoreExplain,
  matchesExplain,
  plannedResultsLine,
  queryAvgExplain,
  resultsColumnExplain,
  tiedConfigCount,
  tiedExplain,
} from './explorerLabels';

describe('plannedResultsLine', () => {
  it.each([
    [3, 8, false, '3 of 8 planned runs have results'],
    [1, 1, false, '1 of 1 planned run has results'],
    [4, 5, true, '4 of 5 planned trials have results'],
  ])('Given %i with results of %i planned (bayesian=%s), when worded, then "%s"', (n, m, bayesian, expected) => {
    /**
     * Scenario: glossary wording; Bayesian says trials, grid says runs; singular verb agrees.
     * Slice: 67G-B.
     */
    // -- When / Then --
    expect(plannedResultsLine(n, m, bayesian)).toBe(expected);
  });

  it('Given no known planned total, when worded, then only the observed count is stated', () => {
    /**
     * Scenario: old experiment without a plan prints no denominator.
     * Slice: 67G-B.
     */
    // -- When / Then --
    expect(plannedResultsLine(3, null, false)).toBe('3 configurations have results');
    expect(plannedResultsLine(1, null, false)).toBe('1 configuration has results');
  });
});

describe('tiedConfigCount', () => {
  it('Given a server tied_count, when counted, then the server value (all configs) wins over the visible ones', () => {
    /**
     * Scenario: one definition of "tied": configs sharing the #1 max score across the whole experiment.
     * Slice: 67G-B.
     */
    // -- When / Then --
    expect(tiedConfigCount({ max_score: 90, tied_count: 7 }, [{ max_score: 90 }, { max_score: 90 }])).toBe(7);
  });

  it('Given no tied_count, when counted, then every visible config at the best score is counted, not only the top three', () => {
    /**
     * Scenario: fallback counts across all ranked configs.
     * Slice: 67G-B.
     */
    // -- Given --
    const ranked = [90, 90, 90, 90, 80].map((max_score) => ({ max_score }));

    // -- When / Then --
    expect(tiedConfigCount({ max_score: 90 }, ranked)).toBe(4);
    expect(tiedConfigCount(null, ranked)).toBe(0);
  });
});

describe('explain sentences', () => {
  it('Given tied configs, when explained, then the sentence states the count, the score and the tiebreak order', () => {
    /**
     * Scenario: tied count tip.
     * Slice: 67G-B.
     */
    // -- When / Then --
    expect(tiedExplain(3, 92)).toBe(
      '3 configurations share the top max score of 92%. Ties are broken by query avg, then smaller chunk size, then smaller overlap, then smaller padding.',
    );
  });

  it('Given the score definitions, when explained, then normalisation is stated once in the max score sentence', () => {
    /**
     * Scenario: score % tips.
     * Slice: 67G-B.
     */
    // -- When / Then --
    expect(maxScoreExplain()).toBe(
      'Scores are min-max normalised to 0-100 across every chunk returned in this experiment: 0 is the lowest chunk score seen, 100 the highest (rerank score when a run has one, dense similarity otherwise). Max score is the best single chunk a configuration retrieved for any query.',
    );
    expect(queryAvgExplain()).toBe(
      "Query avg first takes the mean chunk score of each query, then averages those means, so every query counts equally.",
    );
    expect(chunkAvgExplain()).toBe(
      'Chunk avg is the plain mean of every chunk score the configuration returned, so a query with more chunks weighs more.',
    );
  });

  it.each([
    [17, 3, 5, '17 matches: each is one retrieved chunk for one query, after the retrieval-method filter. A run keeps at most 5 chunks per query (top_k_final) from 3 queries.'],
    [1, 1, undefined, '1 match: each is one retrieved chunk for one query, after the retrieval-method filter. A run keeps a fixed number of chunks per query (top_k_final) from 1 query.'],
  ])('Given %i matches, %i queries and top_k_final %s, when explained, then "%s"', (matches, queries, topK, expected) => {
    /**
     * Scenario: per-query counts and top_k tip.
     * Slice: 67G-B.
     */
    // -- When / Then --
    expect(matchesExplain(matches, queries, topK)).toBe(expected);
  });

  it('Given a Results column, when explained, then it is chunk rows, not queries', () => {
    /**
     * Scenario: Results column tip.
     * Slice: 67G-B.
     */
    // -- When / Then --
    expect(resultsColumnExplain(5)).toBe(
      'Results counts the chunk rows this configuration returned across all queries (at most 5 per query).',
    );
    expect(resultsColumnExplain(undefined)).toBe(
      'Results counts the chunk rows this configuration returned across all queries (at most top_k_final per query).',
    );
  });
});
