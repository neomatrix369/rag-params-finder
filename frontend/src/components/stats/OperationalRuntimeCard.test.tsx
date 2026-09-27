/**
 * Tests for the operational-context store runtime card.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-09-27
 * Scope: vector and run-state backend, container, and image
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import OperationalRuntimeCard from './OperationalRuntimeCard';

const apiMocks = vi.hoisted(() => ({
  getStorageHealth: vi.fn(),
}));

vi.mock('../../services/apiClient', async () => {
  const actual = await vi.importActual<typeof import('../../services/apiClient')>(
    '../../services/apiClient',
  );
  return { ...actual, ...apiMocks };
});

const localHealth = {
  ok: true,
  storage_backend: 'mongodb',
  storage_mode: 'elasticsearch-local',
  vector_store_backend: 'elasticsearch',
  run_state_mode: 'mongodb-local',
  stores: {
    vector: {
      provider: 'elasticsearch',
      mode: 'elasticsearch-local',
      ok: true,
      latency_ms: 4,
      container: 'rag-params-finder-elasticsearch-local',
      image: 'docker.elastic.co/elasticsearch/elasticsearch:9.5.0',
    },
    run_state: {
      provider: 'mongodb',
      mode: 'mongodb-local',
      ok: true,
      latency_ms: 3,
      container: 'rag-params-finder-mongodb-local',
      image: 'mongodb/mongodb-atlas-local:8.3.3',
    },
  },
};

describe('OperationalRuntimeCard', () => {
  beforeEach(() => {
    apiMocks.getStorageHealth.mockReset();
    localStorage.clear();
  });

  it('Given a local split store, when health loads, then backend container and image are shown', async () => {
    /**
     * Scenario: Local vector and run-state identity is visible beside the footprint.
     * Slice: operational context — store runtime
     */
    // -- Given --
    apiMocks.getStorageHealth.mockResolvedValue(localHealth);

    // -- When --
    render(<OperationalRuntimeCard experimentId="exp-runtime" />);

    // -- Then --
    expect(screen.queryByText('docker.elastic.co/elasticsearch/elasticsearch:9.5.0')).not.toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('elasticsearch-local · mongodb-local')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /Store runtime/i }));
    expect(screen.getByText('docker.elastic.co/elasticsearch/elasticsearch:9.5.0')).toBeInTheDocument();
    expect(screen.getByText('rag-params-finder-elasticsearch-local')).toBeInTheDocument();
    expect(screen.getByText('rag-params-finder-mongodb-local')).toBeInTheDocument();
    expect(screen.queryByText('127.0.0.1')).not.toBeInTheDocument();
  });

  it('Given health cannot be loaded, when the request fails, then unavailable copy is shown', async () => {
    /**
     * Scenario: A failed health probe does not invent container details.
     * Slice: operational context — store runtime
     */
    // -- Given --
    apiMocks.getStorageHealth.mockRejectedValue(new Error('offline'));

    // -- When --
    render(<OperationalRuntimeCard experimentId="exp-runtime-down" />);

    // -- Then --
    fireEvent.click(screen.getByRole('button', { name: /Store runtime/i }));
    await waitFor(() => {
      expect(screen.getByText(/Store runtime is unavailable/i)).toBeInTheDocument();
    });
  });
});
