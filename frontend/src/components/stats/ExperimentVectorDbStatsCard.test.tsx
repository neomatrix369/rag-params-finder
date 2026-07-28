/**
 * Tests for ExperimentVectorDbStatsCard loading / empty / populated states.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 Phase B — loading, empty, full stats with run overflow
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { ExperimentDbStatsSummary } from '../../types';
import ExperimentVectorDbStatsCard from './ExperimentVectorDbStatsCard';

function stats(overrides: Partial<ExperimentDbStatsSummary> = {}): ExperimentDbStatsSummary {
  return {
    experiment_id: 'exp-vdb',
    experiment_name: 'vdb demo',
    status: 'complete',
    created_at: '2026-07-27T00:00:00Z',
    database_provider: 'mongodb',
    collection_name: 'chunks',
    cluster_host: 'localhost:27017',
    total_chunks: 100,
    unique_documents: 2,
    embedding_models: ['all-MiniLM-L6-v2'],
    embedding_dimensions: [384],
    index_names: ['vector_index_384'],
    retrieval_methods: ['dense', 'hybrid'],
    chunking_methods: ['fixed'],
    chunking_breakdown: { fixed: 100 },
    estimated_storage_mb: 4.5,
    estimated_embedding_mb: 3.0,
    estimated_metadata_mb: 1.5,
    runs_with_data: 2,
    avg_chunks_per_run: 50,
    total_results: 20,
    unique_queries: 5,
    run_breakdown: Array.from({ length: 10 }, (_, i) => ({
      run_id: `run-${i}-abcdef01`,
      chunks: 10,
      results: 2,
    })),
    ...overrides,
  };
}

describe('ExperimentVectorDbStatsCard', () => {
  it('Given loading without stats, when rendered, then loading copy is shown', () => {
    /**
     * Scenario: Initial load shows placeholder.
     * Slice: 44 Phase B — ExperimentVectorDbStatsCard
     */
    // -- Given / When --
    render(<ExperimentVectorDbStatsCard experimentId="exp-vdb" loading />);

    // -- Then --
    expect(screen.getByText(/Loading vector database stats/i)).toBeInTheDocument();
  });

  it('Given no stats and not loading, when rendered, then empty guidance is shown', () => {
    /**
     * Scenario: Missing stats show guidance copy.
     * Slice: 44 Phase B — ExperimentVectorDbStatsCard
     */
    // -- Given / When --
    render(<ExperimentVectorDbStatsCard experimentId="exp-vdb" />);

    // -- Then --
    expect(screen.getByText(/No vector database stats yet/i)).toBeInTheDocument();
  });

  it('Given populated stats with many runs, when expanded, then overflow hint is shown', () => {
    /**
     * Scenario: Run preview truncates with +N more after expand.
     * Slice: 44 Phase B — ExperimentVectorDbStatsCard
     */
    // -- Given --
    render(<ExperimentVectorDbStatsCard experimentId="exp-vdb" stats={stats()} />);
    expect(screen.getByText(/100 chunks/i)).toBeInTheDocument();

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: /Vector Database/i }));

    // -- Then --
    expect(screen.getByText(/\+ 2 more runs/i)).toBeInTheDocument();
    expect(screen.getByText('dense')).toBeInTheDocument();
  });

  it('Given empty embedding models, when rendered, then dash placeholders appear', () => {
    /**
     * Scenario: Empty model list renders em dash.
     * Slice: 44 Phase B — ExperimentVectorDbStatsCard
     */
    // -- Given / When --
    render(
      <ExperimentVectorDbStatsCard
        experimentId="exp-vdb"
        stats={stats({
          embedding_models: [],
          retrieval_methods: [],
          chunking_methods: [],
          run_breakdown: [],
        })}
      />,
    );

    // -- Then --
    expect(screen.getByText('Vector Database')).toBeInTheDocument();
  });
});
