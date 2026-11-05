/**
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 Phase B — App screen-routing coverage. Verifies list → detail → explore → back
 * navigation and list-cache propagation (onCacheUpdate)
 * without exercising the real screen components (each is stubbed to a minimal test double).
 */
import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type {
  Experiment,
  VectorDbStatsGroup,
} from './types';
import App from './App';
import { useWalkthruActions } from './walkthru/WalkthruContext';

/** Minimal in-stub control panel so App tests can reach the Walkthru entry points. */
function WalkthruStubControls() {
  const { startWalkthru, openDemo } = useWalkthruActions();
  return (
    <div>
      <button onClick={startWalkthru}>Start Walkthru Stub</button>
      <button onClick={openDemo}>Open Demo Stub</button>
    </div>
  );
}

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
      <WalkthruStubControls />
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
      <WalkthruStubControls />
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

  it('Given the list, when Open the demo is clicked, then the demo screen renders without a Walkthru overlay', () => {
    /**
     * Scenario: The demo screen is reachable directly, not only through the Walkthru.
     * Slice: 56 Part C2 - demo entry point.
     */
    // -- Given --
    render(<App />);

    // -- When --
    fireEvent.click(screen.getByText('Open Demo Stub'));

    // -- Then --
    expect(screen.getByText('RAG settings, store by store')).toBeInTheDocument();
    expect(screen.queryByTestId('walkthru-root')).toBeNull();
  });

  it('Given the list, when Start Walkthru is clicked, then the demo screen and the overlay at step 1 appear', () => {
    /**
     * Scenario: Starting the Walkthru routes to the demo screen and opens the overlay.
     * Slice: 56 Part C2 - Walkthru start wiring.
     */
    // -- Given --
    render(<App />);

    // -- When --
    fireEvent.click(screen.getByText('Start Walkthru Stub'));

    // -- Then --
    expect(screen.getByText('RAG settings, store by store')).toBeInTheDocument();
    const overlay = screen.getByTestId('walkthru-root');
    expect(within(overlay).getByText('Step 1 of 5')).toBeInTheDocument();
    expect(within(overlay).getByRole('button', { name: 'Exit walkthru' })).toBeInTheDocument();
  });

  it('Given the Walkthru, when ArrowRight is pressed to the end, then it reaches step 5 and Esc exits to the list', () => {
    /**
     * Scenario: ArrowRight walks from step 1 to step 5; Esc restores the starting screen.
     * Slice: 56 Part C2 - smoke: keyboard reaches the last step + Esc restores screen.
     */
    // -- Given --
    render(<App />);
    fireEvent.click(screen.getByText('Start Walkthru Stub'));
    const overlay = () => screen.getByTestId('walkthru-root');

    // -- When --
    for (let i = 0; i < 4; i += 1) {
      fireEvent.keyDown(window, { key: 'ArrowRight' });
    }

    // -- Then --
    expect(within(overlay()).getByText('Step 5 of 5')).toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByTestId('walkthru-root')).toBeNull();
    expect(screen.getByText('Experiments Screen Stub')).toBeInTheDocument();
  });

  it('Given the Walkthru started from the detail screen, when Esc is pressed, then the detail screen is restored', () => {
    /**
     * Scenario: Esc mid-Walkthru returns to the exact screen the user started from, not the list.
     * Slice: 56 Part C2 - Esc restores the previous screen.
     */
    // -- Given: go list → detail, then start the Walkthru from there --
    render(<App />);
    fireEvent.click(screen.getByText('Select Experiment'));
    expect(screen.getByText(`Detail Screen Stub — ${mockExperiment.experiment_id}`)).toBeInTheDocument();
    fireEvent.click(screen.getByText('Start Walkthru Stub'));
    expect(screen.getByTestId('walkthru-root')).toBeInTheDocument();

    // -- When --
    fireEvent.keyDown(window, { key: 'Escape' });

    // -- Then: the previous (detail) screen is back, not the list --
    expect(screen.queryByTestId('walkthru-root')).toBeNull();
    expect(screen.getByText(`Detail Screen Stub — ${mockExperiment.experiment_id}`)).toBeInTheDocument();
  });

  it('Given the improvement step, when reached, then the collapsed card opens and Esc restores it', () => {
    /**
     * Scenario: A step targeting a collapsed CollapsibleCard opens it; exit restores the collapse.
     * Slice: 56 Part C2 - collapsed-card open + restore on exit.
     */
    // -- Given --
    render(<App />);
    fireEvent.click(screen.getByText('Start Walkthru Stub'));
    // Improvement content is collapsed initially (step 1).
    expect(screen.queryByText('What the best settings changed')).toBeNull();

    // -- When: advance to step 3 (improvement) via ArrowRight --
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    fireEvent.keyDown(window, { key: 'ArrowRight' });

    // -- Then: the card is forced open --
    expect(screen.getByText('What the best settings changed')).toBeInTheDocument();

    // -- When: exit with Esc --
    fireEvent.keyDown(window, { key: 'Escape' });

    // -- Then: back on the list and the card override is dropped --
    expect(screen.getByText('Experiments Screen Stub')).toBeInTheDocument();
    expect(screen.queryByText('What the best settings changed')).toBeNull();
  });

});
