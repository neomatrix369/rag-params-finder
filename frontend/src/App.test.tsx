/**
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 Phase B — App screen-routing coverage. Verifies list → detail → explore → back
 * navigation and list-cache propagation (onCacheUpdate)
 * without exercising the real screen components (each is stubbed to a minimal test double).
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type {
  Experiment,
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
    experiments: [],
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
    onBack,
    onExplore,
  }: {
    experimentId: string;
    onBack: () => void;
    onExplore: () => void;
  }) => (
    <div>
      <p>Detail Screen Stub — {experimentId}</p>
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

  it('Given a populated list cache, when an experiment is selected, then the detail screen still opens', () => {
    /**
     * Scenario: A ready list cache does not block opening an experiment.
     * Slice: 44 Phase B — App coverage (openDetail after onCacheUpdate).
     * Given onCacheUpdate has marked the list cache ready,
     * When that experiment is opened,
     * Then the detail screen stub renders for the same experiment id.
     */
    // -- Given --
    render(<App />);
    fireEvent.click(screen.getByText('Populate Cache'));
    expect(screen.getByText('cacheReady: true')).toBeInTheDocument();

    // -- When --
    fireEvent.click(screen.getByText('Select Experiment'));

    // -- Then --
    expect(screen.getByText(`Detail Screen Stub — ${mockExperiment.experiment_id}`)).toBeInTheDocument();
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
     * Scenario: Explorer → detail back-navigation restores the detailNav snapshot (initialExperiment).
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

});
