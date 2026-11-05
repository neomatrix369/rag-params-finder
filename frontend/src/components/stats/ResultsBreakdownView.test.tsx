/**
 * Rendered tests for the Query Results breakdown, in the footprint and in the stats tile.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67E - formula line, (observed) semantics, hidden when unavailable, tile fallback.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { ExperimentDbStats } from '../../types';
import { vectorDbGroup } from '../../test/helpers/vectorDbStats';
import ExperimentStoredFootprint from './ExperimentStoredFootprint';
import VectorDbStatsPanel from './VectorDbStatsPanel';

function footprint(overrides: Partial<ExperimentDbStats> = {}): ExperimentDbStats {
  return {
    database_provider: 'mongodb',
    collection_name: 'chunks',
    cluster_host: null,
    total_chunks: 120,
    unique_documents: 1,
    embedding_models: ['m'],
    embedding_dimensions: [384],
    index_names: [],
    retrieval_methods: ['dense'],
    chunking_methods: ['recursive'],
    chunking_breakdown: { recursive: 120 },
    estimated_storage_mb: 4,
    estimated_embedding_mb: 3,
    estimated_metadata_mb: 1,
    runs_with_data: 12,
    avg_chunks_per_run: 10,
    total_results: 480,
    unique_queries: 480,
    result_runs: 12,
    golden_queries: 40,
    golden_queries_source: 'config',
    partial_runs: 0,
    run_breakdown: [],
    ...overrides,
  };
}

function tile(totals: Record<string, number | null>) {
  return vectorDbGroup({
    totals: {
      experiment_count: 2,
      total_chunks: 1000,
      total_results: 6480,
      estimated_storage_mb: 12,
      estimated_embedding_mb: 10,
      estimated_metadata_mb: 2,
      ...totals,
    },
  });
}

const text = (id: string): string => screen.getByTestId(id).textContent ?? '';

describe('ExperimentStoredFootprint results breakdown', () => {
  it('Given 12 runs x 40 golden queries and 480 results, when rendered, then the equality shows without (observed)', () => {
    /**
     * Scenario: The product matches the stored total.
     * Slice: 67E - experiment level
     */
    // -- Given / When --
    render(<ExperimentStoredFootprint stats={footprint()} />);

    // -- Then --
    expect(text('results-formula')).toBe('12 runs × 40 golden queries = 480 results');
    expect(text('results-breakdown')).toContain('One result row per query per run; top-k only sets how many chunks each row holds.');
  });

  it('Given 470 stored results against a 480 product, when rendered, then (observed) replaces a false equality', () => {
    /**
     * Scenario: A mismatch must not print a false "=" total.
     * Slice: 67E - observed semantics
     */
    // -- Given / When --
    render(<ExperimentStoredFootprint stats={footprint({ total_results: 470 })} />);

    // -- Then --
    expect(text('results-formula')).toBe('12 runs × 40 golden queries = 470 results (observed)');
  });

  it('Given one run and one golden query, when rendered, then singular labels are used', () => {
    /**
     * Scenario: 1 x 1 = 1.
     * Slice: 67E - singular
     */
    // -- Given / When --
    render(<ExperimentStoredFootprint stats={footprint({ result_runs: 1, golden_queries: 1, total_results: 1 })} />);

    // -- Then --
    expect(text('results-formula')).toBe('1 run × 1 golden query = 1 result');
  });

  it('Given zero stored results, when rendered, then the line reads 0 results (observed) with no NaN', () => {
    /**
     * Scenario: Runs exist but wrote nothing.
     * Slice: 67E - zero results
     */
    // -- Given / When --
    render(<ExperimentStoredFootprint stats={footprint({ total_results: 0 })} />);

    // -- Then --
    expect(text('results-formula')).toBe('12 runs × 40 golden queries = 0 results (observed)');
    expect(screen.getByTestId('results-breakdown').textContent).not.toMatch(/NaN|undefined/);
  });

  it('Given large counts, when rendered, then numbers use en-US grouping', () => {
    /**
     * Scenario: 6-7 digit values stay readable and locale-independent.
     * Slice: 67E - fixed locale
     */
    // -- Given / When --
    render(
      <ExperimentStoredFootprint
        stats={footprint({ result_runs: 162, golden_queries: 40, total_results: 6480 })}
      />,
    );

    // -- Then --
    expect(text('results-formula')).toBe('162 runs × 40 golden queries = 6,480 results');
  });

  it.each([
    ['old payload', { result_runs: undefined, golden_queries: undefined, golden_queries_source: undefined, partial_runs: undefined }],
    ['Redis/ES null golden', { golden_queries: null, golden_queries_source: null, partial_runs: null }],
  ])('Given %s, when rendered, then no breakdown and no NaN or undefined appear', (_name, overrides) => {
    /**
     * Scenario: Missing golden facts hide the breakdown.
     * Slice: 67E - hide when unavailable
     */
    // -- Given / When --
    const { container } = render(<ExperimentStoredFootprint stats={footprint(overrides)} />);

    // -- Then --
    expect(screen.queryByTestId('results-breakdown')).toBeNull();
    expect(container.textContent).not.toMatch(/NaN|undefined/);
    expect(screen.getByTestId('footprint-summary')).toBeInTheDocument();
  });

  it('Given an inferred golden count, when rendered, then the inferred marker shows', () => {
    /**
     * Scenario: max_per_run is flagged as inferred.
     * Slice: 67E - inferred marker
     */
    // -- Given / When --
    render(<ExperimentStoredFootprint stats={footprint({ golden_queries_source: 'max_per_run' })} />);

    // -- Then --
    expect(text('results-source-note')).toContain('(inferred)');
  });

  it('Given partial runs, when the experiment is running versus finished, then the wording differs', () => {
    /**
     * Scenario: A running experiment is only "below golden so far".
     * Slice: 67E - partial-runs note
     */
    // -- Given / When --
    const { rerender } = render(<ExperimentStoredFootprint stats={footprint({ partial_runs: 2 })} />);
    const running = text('results-partial-note');
    rerender(<ExperimentStoredFootprint stats={footprint({ partial_runs: 2 })} isTerminal />);
    const finished = text('results-partial-note');

    // -- Then --
    expect(running).toBe('2 runs below the golden count so far (still running or incomplete).');
    expect(finished).toBe('2 runs returned fewer results than the golden count.');
  });

  it('Given no partial runs, when rendered, then no partial note shows', () => {
    /**
     * Scenario: Silence when everything is complete.
     * Slice: 67E - partial-runs note
     */
    // -- Given / When --
    render(<ExperimentStoredFootprint stats={footprint({ partial_runs: 0 })} />);

    // -- Then --
    expect(screen.queryByTestId('results-partial-note')).toBeNull();
  });
});

describe('VectorDbStatsPanel Query Results tile', () => {
  it('Given a uniform group, when rendered, then the info hint carries the formula and the tile keeps the plain total', () => {
    /**
     * Scenario: 162 runs x 40 golden queries behind the info button.
     * Slice: 67E - group level
     */
    // -- Given / When --
    render(
      <VectorDbStatsPanel
        groups={[tile({ total_result_runs: 162, golden_queries_min: 40, golden_queries_max: 40 })]}
      />,
    );

    // -- Then --
    expect(text('results-group-hint')).toContain('162 runs × 40 golden queries = 6,480 results');
    expect(screen.getByText('6,480')).toBeInTheDocument();
  });

  it('Given a mixed group, when rendered, then the hint shows the observed total and range without "="', () => {
    /**
     * Scenario: Different golden sizes across experiments.
     * Slice: 67E - group level mixed
     */
    // -- Given / When --
    render(
      <VectorDbStatsPanel
        groups={[tile({ total_result_runs: 162, golden_queries_min: 20, golden_queries_max: 40 })]}
      />,
    );

    // -- Then --
    const hint = text('results-group-hint');
    expect(hint).toContain('6,480 results (observed); experiments have 20 to 40 golden queries.');
    expect(hint).not.toContain('=');
  });

  it.each([
    ['golden fields absent', {}],
    ['golden fields null', { total_result_runs: 0, golden_queries_min: null, golden_queries_max: null }],
  ])('Given %s, when rendered, then there is no hint and the tile still shows the plain total', (_name, totals) => {
    /**
     * Scenario: Split-store groups hide the breakdown, not the number.
     * Slice: 67E - group unavailable
     */
    // -- Given / When --
    const { container } = render(<VectorDbStatsPanel groups={[tile(totals)]} />);

    // -- Then --
    expect(screen.queryByTestId('results-group-hint')).toBeNull();
    expect(screen.getByText('6,480')).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/NaN|undefined/);
  });
});
