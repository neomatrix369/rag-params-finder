/**
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 Phase B — App screen-routing coverage. Verifies list → detail → explore → back
 * navigation, list-cache propagation (onCacheUpdate), and db-stats lookup (findDbStatsInGroups)
 * without exercising the real screen components (each is stubbed to a minimal test double).
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type {
  Experiment,
  ExperimentDbStatsSummary,
  VectorDbStatsGroup,
} from './types';
import App from './App';

const mockExperiment: Experiment = {
  experiment_id: 'exp-app-1',
  experiment_name: 'app nav experiment',
  config: {},
  created_at: '2026-07-27T00:00:00Z',
  status: 'complete',
};

const mockDbStats: ExperimentDbStatsSummary = {
  experiment_id: mockExperiment.experiment_id,
  experiment_name: mockExperiment.experiment_name,
  status: 'complete',
  created_at: mockExperiment.created_at,
  database_provider: 'mongodb',
  collection_name: 'chunks',
  cluster_host: 'cluster0',
  total_chunks: 42,
  unique_documents: 3,
  embedding_models: ['voyage-3.5-lite'],
  embedding_dimensions: [1024],
  index_names: ['vector_index_1024'],
  retrieval_methods: ['dense'],
  chunking_methods: ['recursive'],
  chunking_breakdown: { recursive: 42 },
  estimated_storage_mb: 1.2,
  estimated_embedding_mb: 1.0,
  estimated_metadata_mb: 0.2,
  runs_with_data: 1,
  avg_chunks_per_run: 42,
  total_results: 10,
  unique_queries: 3,
  run_breakdown: [],
};

const mockVectorDbGroups: VectorDbStatsGroup[] = [
  {
    vector_db_id: 'db-1',
    database_provider: 'mongodb',
    collection_name: 'chunks',
    cluster_host: 'cluster0',
    index_names: ['vector_index_1024'],
    embedding_dimensions: [1024],
    totals: {
      experiment_count: 1,
      total_chunks: 42,
      total_results: 10,
      estimated_storage_mb: 1.2,
      estimated_embedding_mb: 1.0,
      estimated_metadata_mb: 0.2,
    },
    experiments: [mockDbStats],
  },
];

vi.mock('./components/screens/ExperimentsScreen', () => ({
  default: ({
    onSelect,
    onCacheUpdate,
    cacheReady,
  }: {
    onSelect?: (experiment: Experiment) => void;
    onCacheUpdate?: (update: { experiments: Experiment[]; vectorDbGroups: VectorDbStatsGroup[] }) => void;
    cacheReady?: boolean;
  }) => (
    <div>
      <p>Experiments Screen Stub</p>
      <p>cacheReady: {String(cacheReady)}</p>
      <button onClick={() => onSelect?.(mockExperiment)}>Select Experiment</button>
      <button
        onClick={() =>
          onCacheUpdate?.({ experiments: [mockExperiment], vectorDbGroups: mockVectorDbGroups })
        }
      >
        Populate Cache
      </button>
    </div>
  ),
}));

vi.mock('./components/screens/ExperimentDetailScreen', () => ({
  default: ({
    experimentId,
    initialDbStats,
    onBack,
    onExplore,
  }: {
    experimentId: string;
    initialDbStats?: ExperimentDbStatsSummary;
    onBack: () => void;
    onExplore: () => void;
  }) => (
    <div>
      <p>Detail Screen Stub — {experimentId}</p>
      <p>dbStats total_chunks: {initialDbStats?.total_chunks ?? 'none'}</p>
      <button onClick={onBack}>Back To List</button>
      <button onClick={onExplore}>Go Explore</button>
    </div>
  ),
}));

vi.mock('./components/screens/SearchExplorerScreen', () => ({
  default: ({ experimentId, onBack }: { experimentId: string; onBack: () => void }) => (
    <div>
      <p>Explorer Screen Stub — {experimentId}</p>
      <button onClick={onBack}>Explorer Back</button>
    </div>
  ),
}));

describe('App', () => {
  it('Given a fresh mount, when no navigation has happened, then the experiments list screen renders first', () => {
    /**
     * Scenario: App defaults to the experiments list on first paint.
     * Slice: 44 Phase B — App coverage (initial `{ kind: 'list' }` screen state).
     * Given no prior navigation,
     * When App mounts,
     * Then the experiments list stub is shown with an unready cache.
     */
    // -- Given / When --
    render(<App />);

    // -- Then --
    expect(screen.getByText('Experiments Screen Stub')).toBeInTheDocument();
    expect(screen.getByText('cacheReady: false')).toBeInTheDocument();
  });

  it('Given the list screen, when an experiment is selected, then the detail screen renders with its id', () => {
    /**
     * Scenario: Selecting a row transitions list → detail carrying the chosen experiment id.
     * Slice: 44 Phase B — App coverage (openDetail callback, `{ kind: 'detail' }` branch).
     * Given the experiments list stub,
     * When "Select Experiment" is clicked,
     * Then the detail screen stub renders scoped to that experiment id.
     */
    // -- Given --
    render(<App />);

    // -- When --
    fireEvent.click(screen.getByText('Select Experiment'));

    // -- Then --
    expect(screen.getByText(`Detail Screen Stub — ${mockExperiment.experiment_id}`)).toBeInTheDocument();
  });

  it('Given a populated list cache, when an experiment matching a vector-db group is selected, then db stats are resolved onto the detail screen', () => {
    /**
     * Scenario: findDbStatsInGroups resolves the matching db-stats summary for the opened experiment.
     * Slice: 44 Phase B — App coverage (openDetail db-stats lookup via listCache.vectorDbGroups).
     * Given onCacheUpdate has populated vectorDbGroups containing the target experiment,
     * When that experiment is opened,
     * Then the detail screen stub receives the matching total_chunks value.
     */
    // -- Given --
    render(<App />);
    fireEvent.click(screen.getByText('Populate Cache'));
    expect(screen.getByText('cacheReady: true')).toBeInTheDocument();

    // -- When --
    fireEvent.click(screen.getByText('Select Experiment'));

    // -- Then --
    expect(screen.getByText('dbStats total_chunks: 42')).toBeInTheDocument();
  });

  it('Given the detail screen, when Explore is clicked, then the search explorer screen renders with the same experiment id', () => {
    /**
     * Scenario: Detail → explore navigation carries the experiment id through unchanged.
     * Slice: 44 Phase B — App coverage (onExplore callback, `{ kind: 'explore' }` branch).
     * Given the detail screen stub for an experiment,
     * When "Go Explore" is clicked,
     * Then the search explorer stub renders scoped to that same experiment id.
     */
    // -- Given --
    render(<App />);
    fireEvent.click(screen.getByText('Select Experiment'));

    // -- When --
    fireEvent.click(screen.getByText('Go Explore'));

    // -- Then --
    expect(screen.getByText(`Explorer Screen Stub — ${mockExperiment.experiment_id}`)).toBeInTheDocument();
  });

  it('Given the search explorer screen, when its back link is clicked, then the detail screen renders again with the initial experiment restored', () => {
    /**
     * Scenario: Explorer → detail back-navigation restores the detailNav snapshot (initialExperiment/initialDbStats).
     * Slice: 44 Phase B — App coverage (explore onBack callback restoring detailNav state).
     * Given navigation has gone list → detail → explore,
     * When the explorer's back link is clicked,
     * Then the detail screen stub renders again for the same experiment id.
     */
    // -- Given --
    render(<App />);
    fireEvent.click(screen.getByText('Select Experiment'));
    fireEvent.click(screen.getByText('Go Explore'));

    // -- When --
    fireEvent.click(screen.getByText('Explorer Back'));

    // -- Then --
    expect(screen.getByText(`Detail Screen Stub — ${mockExperiment.experiment_id}`)).toBeInTheDocument();
  });

  it('Given the detail screen, when its back link is clicked, then the experiments list screen renders again', () => {
    /**
     * Scenario: Detail → list back-navigation returns to the `{ kind: 'list' }` screen.
     * Slice: 44 Phase B — App coverage (detail onBack callback).
     * Given navigation has gone list → detail,
     * When the detail screen's back link is clicked,
     * Then the experiments list stub renders again.
     */
    // -- Given --
    render(<App />);
    fireEvent.click(screen.getByText('Select Experiment'));

    // -- When --
    fireEvent.click(screen.getByText('Back To List'));

    // -- Then --
    expect(screen.getByText('Experiments Screen Stub')).toBeInTheDocument();
  });

  it('Given no cached vector db stats, when an experiment is opened, then the detail screen renders without broken layout', () => {
    /**
     * Scenario: Opening detail when db-stats is undefined (cache miss) does not crash the screen.
     * Slice: 44 Phase B — App coverage (detail navigation with undefined initialDbStats).
     * Given no populated vector db groups in cache,
     * When an experiment is selected and opened,
     * Then the detail screen stub renders with dbStats total_chunks as "none".
     */
    // -- Given --
    render(<App />);

    // -- When --
    fireEvent.click(screen.getByText('Select Experiment'));

    // -- Then --
    expect(screen.getByText(`Detail Screen Stub — ${mockExperiment.experiment_id}`)).toBeInTheDocument();
    expect(screen.getByText('dbStats total_chunks: none')).toBeInTheDocument();
  });
});
