/**
 * Tests for the per-experiment stored footprint on the detail screen.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-09-28
 * Scope: models, chunking breakdown, and per-run storage
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { ExperimentDbStats } from '../../types';
import ExperimentStoredFootprint from './ExperimentStoredFootprint';

function footprint(overrides: Partial<ExperimentDbStats> = {}): ExperimentDbStats {
  return {
    database_provider: 'elasticsearch',
    collection_name: 'chunks',
    cluster_host: 'elasticsearch-local',
    total_chunks: 120,
    unique_documents: 1,
    embedding_models: ['all-MiniLM-L6-v2'],
    embedding_dimensions: [384],
    index_names: ['rpf-chunks'],
    retrieval_methods: ['dense'],
    chunking_methods: ['recursive'],
    chunking_breakdown: { recursive: 120 },
    estimated_storage_mb: 4,
    estimated_embedding_mb: 3,
    estimated_metadata_mb: 1,
    runs_with_data: 2,
    avg_chunks_per_run: 60,
    total_results: 8,
    unique_queries: 2,
    run_breakdown: [
      { run_id: 'abcdef1234567890', chunks: 80, results: 5 },
      { run_id: '1234567890abcdef', chunks: 40, results: 3 },
    ],
    ...overrides,
  };
}

describe('ExperimentStoredFootprint', () => {
  it('Given stats are still loading, when the footprint renders, then a loading line is shown', () => {
    /**
     * Scenario: The detail screen shows a loading line before db-stats arrives.
     * Slice: experiment detail stored footprint
     * Given loading with no stats,
     * When the footprint renders,
     * Then the loading copy is visible.
     */
    // -- Given / When --
    render(<ExperimentStoredFootprint loading />);

    // -- Then --
    expect(screen.getByText('Loading stored footprint…')).toBeInTheDocument();
  });

  it('Given no stored chunks, when the footprint renders, then the empty line is shown', () => {
    /**
     * Scenario: An experiment that has not stored chunks yet does not invent a breakdown.
     * Slice: experiment detail stored footprint
     * Given no stats,
     * When the footprint renders,
     * Then the empty copy is visible.
     */
    // -- Given / When --
    render(<ExperimentStoredFootprint />);

    // -- Then --
    expect(screen.getByText('Stored footprint appears after chunks are stored.')).toBeInTheDocument();
  });

  it('Given stored chunks, when the footprint renders, then models, chunking, and runs are shown', () => {
    /**
     * Scenario: The detail footprint lists this experiment's models, chunking, and per-run storage.
     * Slice: experiment detail stored footprint
     * Given db-stats with one model, one chunking method, and two runs,
     * When the footprint renders,
     * Then those three facts are visible and the cluster host is not.
     */
    // -- Given / When --
    render(<ExperimentStoredFootprint stats={footprint()} />);

    // -- Then --
    expect(screen.getByText('all-MiniLM-L6-v2')).toBeInTheDocument();
    expect(screen.getByText('recursive 120')).toBeInTheDocument();
    expect(screen.getByText('80 chunks · 5 results')).toBeInTheDocument();
    expect(screen.queryByText('elasticsearch-local')).not.toBeInTheDocument();
    expect(screen.queryByText('rpf-chunks')).not.toBeInTheDocument();
  });
});
