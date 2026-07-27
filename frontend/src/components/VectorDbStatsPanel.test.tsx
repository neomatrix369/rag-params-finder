/**
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 — vector DB stats empty/loading/error/data presentation.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { VectorDbStatsGroup } from '../types';
import VectorDbStatsPanel from './VectorDbStatsPanel';

function group(overrides: Partial<VectorDbStatsGroup> = {}): VectorDbStatsGroup {
  return {
    vector_db_id: 'vdb-1',
    database_provider: 'mongodb',
    collection_name: 'chunks',
    cluster_host: 'cluster0.example.mongodb.net',
    index_names: ['vector_index_1024'],
    embedding_dimensions: [1024],
    totals: {
      experiment_count: 2,
      total_chunks: 1000,
      total_results: 50,
      estimated_storage_mb: 12,
      estimated_embedding_mb: 10,
      estimated_metadata_mb: 2,
      database_used_mb: 40,
      database_storage_limit_mb: 512,
      database_free_mb: 472,
    },
    experiments: [],
    ...overrides,
  };
}

describe('VectorDbStatsPanel', () => {
  it('Given loading with no groups, when rendered, then loading copy is shown', () => {
    /**
     * Scenario: Initial load shows a loading card before groups arrive.
     * Slice: 44 — frontend coverage gate (VectorDbStatsPanel).
     * Given loading=true and empty groups,
     * When the panel renders,
     * Then loading copy is visible.
     */
    // -- Given / When --
    render(<VectorDbStatsPanel groups={[]} loading />);

    // -- Then --
    expect(screen.getByText(/Loading vector database stats/)).toBeInTheDocument();
  });

  it('Given error with no groups, when rendered, then error message is shown', () => {
    /**
     * Scenario: Failed stats fetch shows the error string.
     * Slice: 44 — frontend coverage gate (VectorDbStatsPanel).
     * Given an error and empty groups,
     * When the panel renders,
     * Then the error text is visible.
     */
    // -- Given / When --
    render(<VectorDbStatsPanel groups={[]} error="timeout talking to Atlas" />);

    // -- Then --
    expect(screen.getByText('Could not load vector database stats')).toBeInTheDocument();
    expect(screen.getByText('timeout talking to Atlas')).toBeInTheDocument();
  });

  it('Given empty idle state, when rendered, then first-experiment hint is shown', () => {
    /**
     * Scenario: No data yet points operators at first experiment.
     * Slice: 44 — frontend coverage gate (VectorDbStatsPanel).
     * Given empty groups without loading or error,
     * When the panel renders,
     * Then the first-experiment hint appears.
     */
    // -- Given / When --
    render(<VectorDbStatsPanel groups={[]} />);

    // -- Then --
    expect(
      screen.getByText(/stats will appear after your first experiment/),
    ).toBeInTheDocument();
  });

  it('Given one stats group, when rendered, then host and chunk totals appear', () => {
    /**
     * Scenario: Populated groups show host and aggregate totals.
     * Slice: 44 — frontend coverage gate (VectorDbStatsPanel).
     * Given a MongoDB group with chunk totals,
     * When the panel renders,
     * Then the host label and chunk count are visible.
     */
    // -- Given / When --
    render(<VectorDbStatsPanel groups={[group()]} />);

    // -- Then --
    expect(screen.getAllByText(/cluster0\.example\.mongodb\.net/).length).toBeGreaterThan(0);
    expect(screen.getByText('1,000 chunks · 472 MB free', { exact: false })).toBeInTheDocument();
    expect(screen.getByText('Experiments')).toBeInTheDocument();
  });
});
