/**
 * Shared experiment list fixtures for Vitest suites.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-07-28
 * Scope: Slice 45 — FE shared test helpers
 */
import type { Experiment } from '../../types';

/** Minimal list-row experiment; override any field via Partial. */
export function experiment(
  status: Experiment['status'],
  failedCount = 0,
  overrides: Partial<Experiment> = {},
): Experiment {
  return {
    experiment_id: `experiment-${status}`,
    experiment_name: `${status} sweep`,
    config: {},
    created_at: '2026-07-18T12:00:00Z',
    status,
    run_count: 3,
    failed_count: failedCount,
    ...overrides,
  };
}
