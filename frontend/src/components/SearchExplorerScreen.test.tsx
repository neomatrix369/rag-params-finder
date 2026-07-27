/**
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 Phase B — Search explorer hydrate/poll lifecycle, hyperparameters vs
 * detailed-results tabs, tie-break annotations, pagination, retrieval-method filtering,
 * query selection refetch, empty/error states, and back navigation.
 */
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { EXPLORE_POLL_MS } from '../constants';
import type { ExperimentProgressCallback } from '../services/apiClient';
import type { DetailedResult, Experiment, ExploreResponse, RankedConfig } from '../types';
import SearchExplorerScreen from './SearchExplorerScreen';

const apiMocks = vi.hoisted(() => ({
  getExperiment: vi.fn(),
  getExperimentExplore: vi.fn(),
  getExperimentExploreWithProgress: vi.fn(),
}));

vi.mock('../services/apiClient', async () => {
  const actual = await vi.importActual<typeof import('../services/apiClient')>(
    '../services/apiClient',
  );
  return { ...actual, ...apiMocks };
});

const RETRIEVAL_METHODS = ['dense', 'sparse', 'hybrid'] as const;
const CHUNKING_METHODS = ['fixed', 'recursive', 'token', 'sentence', 'semantic'];
const EMBEDDING_MODELS = ['voyage-3.5-lite', 'voyage-3.5', 'all-MiniLM-L6-v2'];
const CHUNK_SIZES = [256, 512, 768, 1024];
const OVERLAPS = [20, 50, 80];
const PADDINGS = [0, 10, 20];
const TIED_MAX_SCORE = 92;

function buildConfig(rank: number, overrides: Partial<RankedConfig> = {}): RankedConfig {
  const idx = rank - 1;
  return {
    rank,
    database_provider: 'mongodb',
    embedding_provider: 'voyage',
    embedding_model: EMBEDDING_MODELS[idx % EMBEDDING_MODELS.length],
    chunking_method: CHUNKING_METHODS[idx % CHUNKING_METHODS.length],
    chunk_size: CHUNK_SIZES[idx % CHUNK_SIZES.length],
    overlap: OVERLAPS[idx % OVERLAPS.length],
    padding: PADDINGS[idx % PADDINGS.length],
    max_score: Math.max(10, 90 - idx * 3),
    avg_score: Math.max(5, 80 - idx * 3),
    query_avg_score: Math.max(5, 82 - idx * 3),
    result_count: 5 + idx,
    retrieval_method: RETRIEVAL_METHODS[idx % RETRIEVAL_METHODS.length],
    retrieval_provider: idx % 2 === 0 ? 'local' : 'voyage',
    ...overrides,
  };
}

function buildDetailedResult(rank: number, overrides: Partial<DetailedResult> = {}): DetailedResult {
  const idx = rank - 1;
  return {
    rank,
    score: Math.max(10, 95 - idx * 4),
    raw_score: Math.max(0.1, 0.95 - idx * 0.04),
    database_provider: 'mongodb',
    embedding_provider: 'voyage',
    embedding_model: EMBEDDING_MODELS[idx % EMBEDDING_MODELS.length],
    chunking_method: CHUNKING_METHODS[idx % CHUNKING_METHODS.length],
    chunk_size: CHUNK_SIZES[idx % CHUNK_SIZES.length],
    overlap: OVERLAPS[idx % OVERLAPS.length],
    padding: PADDINGS[idx % PADDINGS.length],
    chunk_text: `Chunk text for result ${rank}. Short filler content for this result.`,
    query_text: `Sample query number ${rank}?`,
    run_id: `run-${rank}`,
    dense_score: Math.max(0.1, 0.9 - idx * 0.03),
    retrieval_method: RETRIEVAL_METHODS[idx % RETRIEVAL_METHODS.length],
    retrieval_provider: idx % 2 === 0 ? 'local' : 'voyage',
    ...overrides,
  };
}

const LONG_CHUNK_TEXT =
  'Alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa quebec romeo sierra tango uniform victor whiskey.';
const LONG_QUERY_TEXT =
  'What is the very long detailed evaluation question that clearly exceeds sixty characters in length?';
const LONG_QUERY_OPTION =
  'What is the very long detailed question that exceeds eighty characters in total length for truncation testing purposes here?';

/**
 * `screen.getByText` normally matches on a node's *direct* text nodes only, ignoring text owned by
 * nested elements (e.g. `<span>Showing <span>1</span> to <span>15</span> of <span>17</span></span>`
 * reports `"Showing to of"` for the outer span). Pagination copy in this component splits numbers
 * into nested `<span>` tags, so match on the full `textContent` instead.
 */
function getByFullText(expected: string) {
  return screen.getByText((_, element) => element?.textContent === expected);
}

/** Three tied top configs (annotation branches) + 14 filler configs — forces table pagination. */
const rankedConfigs: RankedConfig[] = [
  buildConfig(1, {
    max_score: TIED_MAX_SCORE,
    query_avg_score: 90,
    chunk_size: 256,
    overlap: 20,
    padding: undefined,
    retrieval_method: 'dense',
    chunking_method: 'recursive',
    embedding_model: 'voyage-3.5-lite',
  }),
  buildConfig(2, {
    max_score: TIED_MAX_SCORE,
    query_avg_score: 80,
    chunk_size: 512,
    overlap: 50,
    padding: 10,
    retrieval_method: 'sparse',
    chunking_method: 'fixed',
    embedding_model: 'voyage-3.5',
  }),
  buildConfig(3, {
    max_score: TIED_MAX_SCORE,
    query_avg_score: 90,
    chunk_size: 768,
    overlap: 50,
    padding: 0,
    retrieval_method: 'hybrid',
    chunking_method: 'semantic',
    embedding_model: 'all-MiniLM-L6-v2',
  }),
  ...Array.from({ length: 14 }, (_, i) => buildConfig(i + 4)),
];

/** 18 detailed results — forces detailed-results pagination; item 1 has long chunk/query text; item 2 has no query text. */
const detailedResults: DetailedResult[] = [
  buildDetailedResult(1, { chunk_text: LONG_CHUNK_TEXT, query_text: LONG_QUERY_TEXT }),
  buildDetailedResult(2, { query_text: '', padding: undefined }),
  ...Array.from({ length: 16 }, (_, i) => buildDetailedResult(i + 3)),
];

const queries = ['What is RAG?', 'How does chunking affect retrieval quality?', LONG_QUERY_OPTION];

const richExploreResponse: ExploreResponse = {
  experiment_id: 'explore-exp-1',
  experiment_name: 'rich sweep',
  query_count: queries.length,
  total_matches: detailedResults.length,
  queries,
  best_params: buildConfig(1, {
    max_score: TIED_MAX_SCORE,
    avg_score: 85,
    query_avg_score: 90,
    chunk_size: 256,
    overlap: 20,
    padding: 0,
    tied_count: 3,
    retrieval_method: 'dense',
    chunking_method: 'recursive',
    embedding_model: 'voyage-3.5-lite',
  }),
  ranked_configs: rankedConfigs,
  detailed_results: detailedResults,
};

const filteredExploreResponse: ExploreResponse = {
  ...richExploreResponse,
  total_matches: 5,
  detailed_results: detailedResults.slice(0, 5),
};

const noTiesRankedConfigs: RankedConfig[] = [
  buildConfig(1, { max_score: 70, avg_score: 60, query_avg_score: 65, retrieval_method: 'dense' }),
  buildConfig(2, { max_score: 50, avg_score: 40, query_avg_score: 45, retrieval_method: 'sparse' }),
];

const noTiesExploreResponse: ExploreResponse = {
  experiment_id: 'explore-no-ties',
  experiment_name: 'no ties sweep',
  query_count: 1,
  total_matches: 2,
  queries: ['Only one query'],
  best_params: buildConfig(1, {
    max_score: 70,
    avg_score: 60,
    query_avg_score: 65,
    tied_count: 1,
    retrieval_method: 'dense',
  }),
  ranked_configs: noTiesRankedConfigs,
  detailed_results: [buildDetailedResult(1), buildDetailedResult(2)],
};

const emptyExploreResponse: ExploreResponse = {
  experiment_id: 'explore-empty',
  experiment_name: 'empty sweep',
  query_count: 0,
  total_matches: 0,
  queries: [],
  best_params: null,
  ranked_configs: [],
  detailed_results: [],
};

/** One config missing embedding/retrieval provider + padding (best + top card) and one in the
 * paginated table only (rank 4) — exercises every `|| 'local'` / `?? 0` fallback branch. */
const fallbackLabelsBestConfig = buildConfig(1, {
  embedding_provider: '',
  retrieval_provider: null,
  padding: undefined,
  max_score: 60,
  avg_score: 50,
  query_avg_score: 55,
});
const fallbackLabelsResponse: ExploreResponse = {
  experiment_id: 'explore-fallback-labels',
  experiment_name: 'fallback labels sweep',
  query_count: 0,
  total_matches: 1,
  queries: [],
  best_params: { ...fallbackLabelsBestConfig, tied_count: 1 },
  ranked_configs: [
    fallbackLabelsBestConfig,
    buildConfig(2),
    buildConfig(3),
    buildConfig(4, { embedding_provider: '', retrieval_provider: null }),
  ],
  detailed_results: [buildDetailedResult(1)],
};

/** Exactly one ranked config — every sweep-dimension count is 1, forcing the singular
 * (no trailing "s") branch of each pluralized Cartesian-product label. */
const singleConfig = buildConfig(1, {
  max_score: 77,
  avg_score: 70,
  query_avg_score: 72,
  tied_count: 1,
});
const singleConfigExploreResponse: ExploreResponse = {
  experiment_id: 'explore-single-config',
  experiment_name: 'single config sweep',
  query_count: 1,
  total_matches: 1,
  queries: ['Only query'],
  best_params: singleConfig,
  ranked_configs: [singleConfig],
  detailed_results: [buildDetailedResult(1)],
};

/** Two tied configs differing only in overlap — drives the #1 "smallest overlap" reason and the
 * #2 "larger overlap" diff branches of the tiebreaker annotation chain. */
const overlapTiebreakConfig0 = buildConfig(1, {
  max_score: 88,
  query_avg_score: 80,
  chunk_size: 500,
  overlap: 10,
  padding: 5,
});
const overlapTiebreakConfig1 = buildConfig(2, {
  max_score: 88,
  query_avg_score: 80,
  chunk_size: 500,
  overlap: 20,
  padding: 5,
});
const overlapTiebreakResponse: ExploreResponse = {
  experiment_id: 'explore-overlap-tiebreak',
  experiment_name: 'overlap tiebreak sweep',
  query_count: 0,
  total_matches: 2,
  queries: [],
  best_params: { ...overlapTiebreakConfig0, tied_count: 2 },
  ranked_configs: [overlapTiebreakConfig0, overlapTiebreakConfig1],
  detailed_results: [buildDetailedResult(1)],
};

/** Two tied configs differing only in padding — drives the #1 "smallest padding" reason and the
 * #2 "larger padding" diff branches of the tiebreaker annotation chain. */
const paddingTiebreakConfig0 = buildConfig(1, {
  max_score: 90,
  query_avg_score: 80,
  chunk_size: 500,
  overlap: 20,
  padding: 5,
});
const paddingTiebreakConfig1 = buildConfig(2, {
  max_score: 90,
  query_avg_score: 80,
  chunk_size: 500,
  overlap: 20,
  padding: 15,
});
const paddingTiebreakResponse: ExploreResponse = {
  experiment_id: 'explore-padding-tiebreak',
  experiment_name: 'padding tiebreak sweep',
  query_count: 0,
  total_matches: 2,
  queries: [],
  best_params: { ...paddingTiebreakConfig0, tied_count: 2 },
  ranked_configs: [paddingTiebreakConfig0, paddingTiebreakConfig1],
  detailed_results: [buildDetailedResult(1)],
};

/** Two tied configs identical in every tiebreaker field — drives the "identical parameters" /
 * "identical performance" fallback copy when no reason/diff can be found. */
const identicalTiebreakConfig0 = buildConfig(1, {
  max_score: 85,
  query_avg_score: 80,
  chunk_size: 500,
  overlap: 20,
  padding: 5,
});
const identicalTiebreakConfig1 = buildConfig(2, {
  ...identicalTiebreakConfig0,
  rank: 2,
});
const identicalTiebreakResponse: ExploreResponse = {
  experiment_id: 'explore-identical-tiebreak',
  experiment_name: 'identical tiebreak sweep',
  query_count: 0,
  total_matches: 2,
  queries: [],
  best_params: { ...identicalTiebreakConfig0, tied_count: 2 },
  ranked_configs: [identicalTiebreakConfig0, identicalTiebreakConfig1],
  detailed_results: [buildDetailedResult(1)],
};

function minimalExperiment(status: Experiment['status']): Experiment {
  return {
    experiment_id: richExploreResponse.experiment_id,
    experiment_name: richExploreResponse.experiment_name,
    config: {},
    created_at: '2026-07-27T00:00:00Z',
    status,
  };
}

describe('SearchExplorerScreen', () => {
  beforeEach(() => {
    apiMocks.getExperiment.mockReset();
    apiMocks.getExperimentExplore.mockReset();
    apiMocks.getExperimentExploreWithProgress.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('Given a pending explore fetch, when the screen first mounts, then a loading panel is shown', () => {
    /**
     * Scenario: First paint never flashes an empty canvas before the fetch effect resolves.
     * Slice: 44 Phase B — SearchExplorerScreen coverage.
     * Given the explore fetch promise has not yet resolved,
     * When the screen mounts,
     * Then the loading feedback panel renders with the initial hydrate copy.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockImplementation(() => new Promise(() => undefined));

    // -- When --
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />);

    // -- Then --
    expect(screen.getByText('Loading results…')).toBeInTheDocument();
  });

  it('Given a rich explore payload, when hydrate resolves, then tied top configs render with tiebreaker annotations', async () => {
    /**
     * Scenario: Tied #1 configs surface a tiebreaker explanation and per-card annotations.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (BestParamsCard, ConfigCard tie branches).
     * Given three top configs share the max score with different query-avg/chunk-size,
     * When the hyperparameters tab renders,
     * Then the tiebreaker banner and the query-avg / larger-chunk annotations both appear.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(richExploreResponse);

    // -- When --
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />);
    await screen.findByText('Best Overall Parameters');

    // -- Then --
    expect(screen.getByText('3 configs tied at 92%', { exact: false })).toBeInTheDocument();
    expect(screen.getByText('Best by tiebreaker')).toBeInTheDocument();
    expect(screen.getAllByText('Tied')).toHaveLength(2);
    expect(screen.getByText(/highest query avg \(90%\)/)).toBeInTheDocument();
    expect(screen.getByText(/lower query avg \(80% vs 90%\)/)).toBeInTheDocument();
    expect(screen.getByText(/larger chunks \(768 vs 256\)/)).toBeInTheDocument();
  });

  it('Given more than three configs, when Sweep Dimensions is expanded and the table is paginated, then hidden dimensions and page two both appear', async () => {
    /**
     * Scenario: Collapsible sweep-dimension summary and the all-configurations table paginate correctly.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (sweepExpanded toggle, Pagination Next/items-per-page).
     * Given 17 ranked configs (more than the default 15-per-page and more than the top-3 preview),
     * When the sweep dimensions panel is expanded and Next is clicked,
     * Then the cartesian-product summary and page two of the table both render.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(richExploreResponse);
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />);
    await screen.findByText('All Configurations (17)');

    // -- When --
    fireEvent.click(screen.getByText('Sweep Dimensions'));

    // -- Then --
    expect(screen.getByText(/Cartesian product:/)).toBeInTheDocument();

    // -- When --
    expect(getByFullText('Showing 1 to 15 of 17')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));

    // -- Then --
    expect(getByFullText('Showing 16 to 17 of 17')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();

    // -- When --
    fireEvent.change(screen.getByLabelText('Per page:'), { target: { value: '25' } });

    // -- Then --
    expect(getByFullText('Showing 1 to 17 of 17')).toBeInTheDocument();
  });

  it('Given page two of the all-configurations table, when Previous is clicked, then page one re-renders', async () => {
    /**
     * Scenario: The Pagination "Previous" control decrements the page just like "Next" increments it.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (Pagination onPageChange decrement branch).
     * Given the hyperparameters table has been advanced to page two,
     * When the Previous button is clicked,
     * Then page one's row range renders again and Previous becomes disabled.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(richExploreResponse);
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />);
    await screen.findByText('All Configurations (17)');
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(getByFullText('Showing 16 to 17 of 17')).toBeInTheDocument();

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Previous' }));

    // -- Then --
    expect(getByFullText('Showing 1 to 15 of 17')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();
  });

  it('Given the detailed results tab, when a query filter and a long chunk are exercised, then truncation, expand, and pagination all work', async () => {
    /**
     * Scenario: Detailed-results tab truncates long text/queries and paginates independently.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (DetailedResultsTab expand + Pagination).
     * Given 18 detailed results including one long chunk/query and one with no query text,
     * When the Detailed Results tab is opened and the long chunk is clicked to expand,
     * Then the truncated preview is replaced by the full text and paging to page two works.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(richExploreResponse);
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />);
    await screen.findByText('Best Overall Parameters');

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Detailed Results' }));

    // -- Then --
    expect(screen.getByText('Individual chunk results', { exact: false })).toBeInTheDocument();
    expect(
      screen.getByText(
        (_, element) =>
          element?.tagName.toLowerCase() === 'p' &&
          Boolean(element.textContent?.includes('Alpha bravo charlie')) &&
          Boolean(element.textContent?.includes('...')),
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText('Query:').length).toBeGreaterThan(0);

    // -- When --
    fireEvent.click(screen.getByText('Click to expand'));

    // -- Then --
    expect(screen.getByText(LONG_CHUNK_TEXT, { exact: false })).toBeInTheDocument();
    expect(screen.queryByText('Click to expand')).toBeNull();

    // -- When --
    expect(getByFullText('Showing 1 to 15 of 18')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));

    // -- Then --
    expect(getByFullText('Showing 16 to 18 of 18')).toBeInTheDocument();

    // -- When --
    fireEvent.change(screen.getByLabelText('Per page:'), { target: { value: '25' } });

    // -- Then --
    expect(getByFullText('Showing 1 to 18 of 18')).toBeInTheDocument();

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Hyperparameters' }));

    // -- Then --
    expect(screen.getByText('Best Overall Parameters')).toBeInTheDocument();
  });

  it('Given an expanded chunk in the detailed results tab, when it is clicked again, then it collapses back to the truncated preview', async () => {
    /**
     * Scenario: Expand/collapse is a genuine toggle, not a one-way reveal.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (toggleExpand collapse branch).
     * Given the long chunk in the detailed results tab has already been expanded,
     * When the chunk text is clicked a second time,
     * Then the truncated preview and its "Click to expand" affordance return.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(richExploreResponse);
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />);
    await screen.findByText('Best Overall Parameters');
    fireEvent.click(screen.getByRole('button', { name: 'Detailed Results' }));
    fireEvent.click(screen.getByText('Click to expand'));
    expect(screen.getByText(LONG_CHUNK_TEXT, { exact: false })).toBeInTheDocument();

    // -- When --
    fireEvent.click(screen.getByText(LONG_CHUNK_TEXT, { exact: false }));

    // -- Then --
    expect(screen.getByText('Click to expand')).toBeInTheDocument();
    expect(screen.queryByText(LONG_CHUNK_TEXT, { exact: false })).toBeNull();
  });

  it('Given the sidebar back link, when clicked, then onBack fires', async () => {
    /**
     * Scenario: The explorer rail back link hands control back to the caller.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (back navigation).
     * Given a rendered explorer with a resolved hydrate,
     * When the back link is clicked,
     * Then the onBack callback is invoked exactly once.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(richExploreResponse);
    const onBack = vi.fn();
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={onBack} />);
    await screen.findByText('Best Overall Parameters');

    // -- When --
    fireEvent.click(screen.getByText('← Back to experiment'));

    // -- Then --
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it('Given an experiment with zero stored results, when hydrate resolves, then the empty state renders without a best-params card', async () => {
    /**
     * Scenario: A hydrated but empty experiment shows the explicit empty state, not a blank canvas.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (empty ranked_configs / total_matches branch).
     * Given the explore payload has no ranked configs, no queries, and no best params,
     * When hydrate resolves,
     * Then "No results found" renders and the best-params card and query selector are both absent.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(emptyExploreResponse);

    // -- When --
    render(<SearchExplorerScreen experimentId={emptyExploreResponse.experiment_id} onBack={vi.fn()} />);
    await screen.findByText('No results found');

    // -- Then --
    expect(screen.getByText('This experiment has no query results stored yet.')).toBeInTheDocument();
    expect(screen.queryByText('Best Overall Parameters')).toBeNull();
    expect(screen.queryByRole('combobox')).toBeNull();
  });

  it('Given a failing explore fetch, when hydrate rejects, then the error banner shows the message and the waiting state is suppressed', async () => {
    /**
     * Scenario: A failed hydrate surfaces the error message instead of the generic waiting copy.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (error path).
     * Given getExperimentExploreWithProgress rejects with an Error,
     * When hydrate settles,
     * Then the error banner shows the message and "Waiting for results" is not shown.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockRejectedValueOnce(new Error('Explore fetch boom'));

    // -- When --
    render(<SearchExplorerScreen experimentId="explore-error" onBack={vi.fn()} />);
    await screen.findByText('Explore fetch boom');

    // -- Then --
    expect(screen.queryByText('Waiting for results')).toBeNull();
  });

  it('Given three retrieval methods checked, when methods are unchecked one at a time, then the last method cannot be unchecked', async () => {
    /**
     * Scenario: Retrieval-method filtering never leaves the explorer with zero visible methods.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (handleToggleMethod guard branch).
     * Given all three retrieval methods start checked after hydrate,
     * When methods are unchecked down to the last one and the last is clicked again,
     * Then the match count shrinks twice but the final checkbox stays checked.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(richExploreResponse);
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />);
    await screen.findByText('Best Overall Parameters');
    expect(screen.getByText('18 MATCHES')).toBeInTheDocument();

    // -- When --
    fireEvent.click(screen.getByRole('checkbox', { name: /sparse/ }));

    // -- Then --
    const remainingAfterFirstUncheck = screen.getByText(/\d+ MATCHES/).textContent;
    expect(remainingAfterFirstUncheck).not.toBe('18 MATCHES');

    // -- When --
    fireEvent.click(screen.getByRole('checkbox', { name: /dense/ }));
    const hybridCheckbox = screen.getByRole('checkbox', { name: /hybrid/ });
    expect(hybridCheckbox).toBeChecked();

    // -- When / Then --
    fireEvent.click(hybridCheckbox);
    expect(hybridCheckbox).toBeChecked();
  });

  it('Given an unchecked retrieval method, when it is checked again, then it re-enters the active filter set', async () => {
    /**
     * Scenario: Unchecking a method and then re-checking it restores it to the visible filter set.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (handleToggleMethod re-add branch).
     * Given the sparse method has already been unchecked,
     * When the sparse checkbox is clicked again,
     * Then it becomes checked and the match count returns to its original total.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(richExploreResponse);
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />);
    await screen.findByText('Best Overall Parameters');
    const sparseCheckbox = screen.getByRole('checkbox', { name: /sparse/ });
    fireEvent.click(sparseCheckbox);
    expect(sparseCheckbox).not.toBeChecked();

    // -- When --
    fireEvent.click(sparseCheckbox);

    // -- Then --
    expect(sparseCheckbox).toBeChecked();
    expect(screen.getByText('18 MATCHES')).toBeInTheDocument();
  });

  it('Given the sidebar configurations header, when clicked, then the target-configuration list expands and collapses', async () => {
    /**
     * Scenario: The "Target Configurations" header itself toggles the expanded list, not only the "+N more" link.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (ConfigSidebar header-button toggle branch).
     * Given the sidebar starts collapsed to 5 target configurations,
     * When the header button is clicked,
     * Then all configurations appear, and clicking the header again re-collapses the list.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(richExploreResponse);
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />);
    await screen.findByText('Best Overall Parameters');
    const header = screen.getByText('Target Configurations');

    // -- When --
    fireEvent.click(header);

    // -- Then --
    expect(screen.queryByText('+ 12 more')).toBeNull();

    // -- When --
    fireEvent.click(header);

    // -- Then --
    expect(screen.getByText('+ 12 more')).toBeInTheDocument();
  });

  it('Given more than five target configurations, when "more" is expanded, then all configs appear in the sidebar', async () => {
    /**
     * Scenario: The sidebar's target-configuration list is collapsible once it exceeds five entries.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (ConfigSidebar configsExpanded toggle).
     * Given 17 ranked configs feed the sidebar,
     * When the "+ N more" control is clicked,
     * Then the collapsed count expands to show every configuration.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(richExploreResponse);
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />);
    await screen.findByText('Best Overall Parameters');
    expect(screen.getByText('+ 12 more')).toBeInTheDocument();

    // -- When --
    fireEvent.click(screen.getByText('+ 12 more'));

    // -- Then --
    expect(screen.queryByText('+ 12 more')).toBeNull();
  });

  it('Given a selected query filter, when the dropdown changes, then a new explore fetch runs and refreshes the results', async () => {
    /**
     * Scenario: Selecting a query re-fetches explore data scoped to that query, without clearing the prior view.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (selectedQuery effect / refresh copy branch).
     * Given hydrate has already completed once,
     * When a query is selected from the dropdown,
     * Then a second fetch is issued and, once it resolves, the match count reflects the filtered payload.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(richExploreResponse);
    let resolveFiltered: (value: ExploreResponse) => void = () => undefined;
    apiMocks.getExperimentExploreWithProgress.mockImplementationOnce(
      () => new Promise<ExploreResponse>((resolve) => { resolveFiltered = resolve; }),
    );
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />);
    await screen.findByText('Best Overall Parameters');
    const [querySelect] = screen.getAllByRole('combobox');

    // -- When --
    fireEvent.change(querySelect, { target: { value: queries[0] } });

    // -- Then --
    expect(screen.getByText('Refreshing explorer (filtered query)…')).toBeInTheDocument();
    expect(apiMocks.getExperimentExploreWithProgress).toHaveBeenCalledTimes(2);

    // -- When --
    await act(async () => {
      resolveFiltered(filteredExploreResponse);
    });

    // -- Then --
    await waitFor(() => expect(screen.getByText('5 MATCHES')).toBeInTheDocument());

    // -- When --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(richExploreResponse);
    fireEvent.change(querySelect, { target: { value: '' } });

    // -- Then --
    expect(screen.getByText('Refreshing explorer…')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('18 MATCHES')).toBeInTheDocument());
  });

  it('Given no tied configs, when hydrate resolves, then the non-tie summary copy renders instead of a tiebreaker banner', async () => {
    /**
     * Scenario: Distinct max scores render the plain top-N summary instead of tiebreaker copy.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (hasTies=false branch).
     * Given two ranked configs with different max scores and tied_count=1 on best_params,
     * When the hyperparameters tab renders,
     * Then the "Top N parameter configurations" summary appears and no tiebreaker banner does.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(noTiesExploreResponse);

    // -- When --
    render(<SearchExplorerScreen experimentId={noTiesExploreResponse.experiment_id} onBack={vi.fn()} />);
    await screen.findByText('Best Overall Parameters');

    // -- Then --
    expect(
      screen.getByText('Top 2 parameter configurations that yielded', { exact: false }),
    ).toBeInTheDocument();
    expect(screen.queryByText('Tiebreaker applied:')).toBeNull();
    expect(screen.queryByText(/configs tied at/)).toBeNull();
  });

  it('Given the background poll fires while the experiment is no longer running, when the interval elapses, then polling stops without an explore refetch', async () => {
    /**
     * Scenario: The background poll self-disables once the experiment leaves the running state.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (poll effect early-return branch).
     * Given the experiment status resolves to "complete" on the poll tick,
     * When EXPLORE_POLL_MS elapses,
     * Then getExperiment is called once and getExperimentExplore is never called.
     */
    // -- Given --
    vi.useFakeTimers();
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(richExploreResponse);
    apiMocks.getExperiment.mockResolvedValueOnce(minimalExperiment('complete'));
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByText('Best Overall Parameters')).toBeInTheDocument();

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(EXPLORE_POLL_MS);
    });

    // -- Then --
    expect(apiMocks.getExperiment).toHaveBeenCalledTimes(1);
    expect(apiMocks.getExperimentExplore).not.toHaveBeenCalled();
  });

  it('Given the background poll fires while the experiment is still running, when the interval elapses, then explore data refreshes in place', async () => {
    /**
     * Scenario: While running, the background poll refreshes ranked configs without re-showing the loader.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (poll effect refresh branch).
     * Given the experiment status resolves to "running" on the poll tick,
     * When EXPLORE_POLL_MS elapses,
     * Then getExperimentExplore is called and the sidebar reflects the newly polled config count.
     */
    // -- Given --
    vi.useFakeTimers();
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(richExploreResponse);
    apiMocks.getExperiment.mockResolvedValueOnce(minimalExperiment('running'));
    const polledResponse: ExploreResponse = {
      ...richExploreResponse,
      ranked_configs: [...rankedConfigs, buildConfig(18)],
    };
    apiMocks.getExperimentExplore.mockResolvedValueOnce(polledResponse);
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByText('Configs: 17')).toBeInTheDocument();

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(EXPLORE_POLL_MS);
    });

    // -- Then --
    expect(apiMocks.getExperimentExplore).toHaveBeenCalledWith(richExploreResponse.experiment_id, undefined);
    expect(screen.getByText('Configs: 18')).toBeInTheDocument();
  });

  it('Given configs missing optional provider/padding fields, when they render, then "local" and zero-padding fallbacks are shown', async () => {
    /**
     * Scenario: Missing embedding/retrieval provider and padding fall back to display defaults everywhere they appear.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (`|| 'local'` / `?? 0` fallback branches).
     * Given the best config, its top card, and a paginated table row all omit optional provider/padding fields,
     * When the hyperparameters tab renders,
     * Then each of those cards/rows displays "local" and "0" instead of blank values.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(fallbackLabelsResponse);

    // -- When --
    const { container } = render(
      <SearchExplorerScreen experimentId={fallbackLabelsResponse.experiment_id} onBack={vi.fn()} />,
    );
    await screen.findByText('Best Overall Parameters');

    // -- Then --
    expect(screen.getAllByText('local').length).toBeGreaterThanOrEqual(4);
    expect(container.textContent).toContain('256/20/0');
  });

  it('Given exactly one ranked config, when Sweep Dimensions is expanded, then every sweep-dimension label uses singular wording', async () => {
    /**
     * Scenario: A single-configuration sweep renders "1 model", not "1 models".
     * Slice: 44 Phase B — SearchExplorerScreen coverage (Cartesian-product pluralization singular branch).
     * Given the explore payload has exactly one ranked config,
     * When Sweep Dimensions is expanded,
     * Then the Cartesian-product summary uses singular nouns throughout.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(singleConfigExploreResponse);
    const { container } = render(
      <SearchExplorerScreen experimentId={singleConfigExploreResponse.experiment_id} onBack={vi.fn()} />,
    );
    await screen.findByText('Best Overall Parameters');

    // -- When --
    fireEvent.click(screen.getByText('Sweep Dimensions'));

    // -- Then --
    expect(container.textContent).toContain('1 model ×');
    expect(container.textContent).toContain('= 1 configuration');
    expect(container.textContent).not.toContain('1 models');
    expect(container.textContent).not.toContain('1 configurations');
  });

  it('Given two tied configs differing only in overlap, when the tiebreaker annotations render, then overlap is cited as the deciding factor', async () => {
    /**
     * Scenario: When query avg and chunk size are equal, overlap becomes the tiebreaker reason.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (annotation chain: overlap reason/diff branches).
     * Given two tied configs equal in query avg and chunk size but differing in overlap,
     * When the hyperparameters tab renders,
     * Then #1's annotation cites the smaller overlap and #2's cites the larger overlap.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(overlapTiebreakResponse);

    // -- When --
    render(<SearchExplorerScreen experimentId={overlapTiebreakResponse.experiment_id} onBack={vi.fn()} />);
    await screen.findByText('Best Overall Parameters');

    // -- Then --
    expect(screen.getByText(/smallest overlap \(10 vs 20\)/)).toBeInTheDocument();
    expect(screen.getByText(/larger overlap \(20 vs 10\)/)).toBeInTheDocument();
  });

  it('Given two tied configs differing only in padding, when the tiebreaker annotations render, then padding is cited as the deciding factor', async () => {
    /**
     * Scenario: When query avg, chunk size, and overlap are all equal, padding becomes the tiebreaker reason.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (annotation chain: padding reason/diff branches).
     * Given two tied configs equal in query avg, chunk size, and overlap but differing in padding,
     * When the hyperparameters tab renders,
     * Then #1's annotation cites the smaller padding and #2's cites the larger padding.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(paddingTiebreakResponse);

    // -- When --
    render(<SearchExplorerScreen experimentId={paddingTiebreakResponse.experiment_id} onBack={vi.fn()} />);
    await screen.findByText('Best Overall Parameters');

    // -- Then --
    expect(screen.getByText(/smallest padding \(5 vs 15\)/)).toBeInTheDocument();
    expect(screen.getByText(/larger padding \(15 vs 5\)/)).toBeInTheDocument();
  });

  it('Given two tied configs identical across every tiebreaker field, when the annotations render, then the "identical" fallback copy is shown', async () => {
    /**
     * Scenario: When no tiebreaker field differs, the annotation falls back to an "identical" message.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (annotation chain: reasons/diff length === 0 branches).
     * Given two tied configs with identical query avg, chunk size, overlap, and padding,
     * When the hyperparameters tab renders,
     * Then #1's annotation reports identical parameters and #2's reports identical performance.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(identicalTiebreakResponse);

    // -- When --
    render(<SearchExplorerScreen experimentId={identicalTiebreakResponse.experiment_id} onBack={vi.fn()} />);
    await screen.findByText('Best Overall Parameters');

    // -- Then --
    expect(screen.getByText(/identical parameters/)).toBeInTheDocument();
    expect(screen.getByText(/identical performance/)).toBeInTheDocument();
  });

  it('Given the hydrate fetch aborts unexpectedly while the screen is still mounted, then no error banner appears and the waiting state renders', async () => {
    /**
     * Scenario: An AbortError rejection is swallowed silently rather than surfaced as a user-facing error.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (AbortError early-return branch in the catch block).
     * Given getExperimentExploreWithProgress rejects with a DOMException named "AbortError",
     * When hydrate settles while the component remains mounted,
     * Then no error banner renders and the "Waiting for results" empty state appears instead.
     */
    // -- Given --
    apiMocks.getExperimentExploreWithProgress.mockRejectedValueOnce(
      new DOMException('The operation was aborted', 'AbortError'),
    );

    // -- When --
    render(<SearchExplorerScreen experimentId="explore-abort" onBack={vi.fn()} />);
    await screen.findByText('Waiting for results');

    // -- Then --
    expect(screen.queryByText(/aborted/i)).toBeNull();
    expect(
      screen.getByText("The experiment is still running. Results will appear as soon as they're available."),
    ).toBeInTheDocument();
  });

  it('Given the background poll request rejects, when the interval elapses, then the prior explorer data stays visible without crashing', async () => {
    /**
     * Scenario: A failed background poll is logged and ignored, leaving the last-known data on screen.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (poll effect catch branch).
     * Given the experiment status resolves to "running" but the follow-up explore poll rejects,
     * When EXPLORE_POLL_MS elapses,
     * Then the previously hydrated config count remains on screen and no exception escapes.
     */
    // -- Given --
    vi.useFakeTimers();
    apiMocks.getExperimentExploreWithProgress.mockResolvedValueOnce(richExploreResponse);
    apiMocks.getExperiment.mockResolvedValueOnce(minimalExperiment('running'));
    apiMocks.getExperimentExplore.mockRejectedValueOnce(new Error('poll boom'));
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByText('Configs: 17')).toBeInTheDocument();

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(EXPLORE_POLL_MS);
    });

    // -- Then --
    expect(apiMocks.getExperimentExplore).toHaveBeenCalledTimes(1);
    expect(screen.getByText('Configs: 17')).toBeInTheDocument();
  });

  it('Given the initial hydrate never resolves, when the background poll succeeds and progress updates stream in, then the sidebar and byte-progress banner both populate from the poll', async () => {
    /**
     * Scenario: A slow/stuck initial fetch does not block the background poll from populating the UI, and
     * download-progress updates render live once data exists alongside a still-loading hydrate.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (poll setSelectedMethods-from-empty branch,
     * applyProg downloading/message branches, and the "loading && data" byte-progress banner branches).
     * Given the initial hydrate promise never settles and selectedMethods is still empty,
     * When the background poll resolves with data and the hydrate progress callback streams byte updates,
     * Then the sidebar reflects the polled config count and the refreshing banner shows byte progress.
     */
    // -- Given --
    vi.useFakeTimers();
    let capturedOnProgress: ExperimentProgressCallback | undefined;
    apiMocks.getExperimentExploreWithProgress.mockImplementationOnce(
      (_experimentId: string, _query: string | undefined, onProgress: ExperimentProgressCallback | undefined) => {
        capturedOnProgress = onProgress;
        return new Promise<ExploreResponse>(() => undefined);
      },
    );
    apiMocks.getExperiment.mockResolvedValueOnce(minimalExperiment('running'));
    apiMocks.getExperimentExplore.mockResolvedValueOnce(richExploreResponse);
    render(<SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />);
    expect(screen.getByText('Loading results…')).toBeInTheDocument();

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(EXPLORE_POLL_MS);
    });

    // -- Then --
    expect(screen.getByText('Configs: 17')).toBeInTheDocument();

    // -- When --
    act(() => {
      capturedOnProgress?.({ type: 'message', text: 'Custom stall notice', variant: 'warning' });
      capturedOnProgress?.({ type: 'message', text: 'Custom informational step' });
      capturedOnProgress?.({ type: 'downloading', receivedBytes: 200, totalBytes: null });
      capturedOnProgress?.({ type: 'downloading', receivedBytes: 500, totalBytes: 1000 });
    });

    // -- Then --
    expect(screen.getByText('Refreshing explorer data…')).toBeInTheDocument();
    expect(screen.getAllByText(/500 B \/ 1000 B/).length).toBeGreaterThan(0);
  });

  it('Given the screen unmounts before hydrate resolves, when the pending fetch settles afterward, then no update is applied to unmounted state', async () => {
    /**
     * Scenario: Late-arriving hydrate results after unmount are dropped via the `aliveRef` guard.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (`aliveRef.current` guards in the success path).
     * Given the explore fetch promise is still pending when the component unmounts,
     * When that promise resolves after unmount,
     * Then resolving it does not throw and no further mock calls occur.
     */
    // -- Given --
    let resolveLate: (value: ExploreResponse) => void = () => undefined;
    apiMocks.getExperimentExploreWithProgress.mockImplementationOnce(
      () => new Promise<ExploreResponse>((resolve) => { resolveLate = resolve; }),
    );
    const { unmount } = render(
      <SearchExplorerScreen experimentId={richExploreResponse.experiment_id} onBack={vi.fn()} />,
    );

    // -- When --
    unmount();
    await act(async () => {
      resolveLate(richExploreResponse);
    });

    // -- Then --
    expect(apiMocks.getExperimentExploreWithProgress).toHaveBeenCalledTimes(1);
  });

  it('Given a stalled hydrate fetch, when the stall threshold elapses, then a "still waiting" warning appears in the activity feed', async () => {
    /**
     * Scenario: A slow hydrate surfaces a human-readable stall warning instead of hanging silently.
     * Slice: 44 Phase B — SearchExplorerScreen coverage (createStallWatcher alive/onWarning callbacks).
     * Given the explore fetch promise never settles,
     * When the loading-stall threshold elapses,
     * Then a "Still waiting" entry is appended to the loading feed.
     */
    // -- Given --
    vi.useFakeTimers();
    apiMocks.getExperimentExploreWithProgress.mockImplementationOnce(
      () => new Promise<ExploreResponse>(() => undefined),
    );
    render(<SearchExplorerScreen experimentId="explore-stall" onBack={vi.fn()} />);
    expect(screen.getByText('Loading results…')).toBeInTheDocument();

    // -- When --
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    // -- Then --
    expect(screen.getByText(/Still waiting/)).toBeInTheDocument();
  });
});
