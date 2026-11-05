/**
 * Tests for the improvement story panel.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part C2 - best/median/worst similarity scores, spread, the question and the
 *        best-vs-worst top chunks side by side.
 */
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { makeDemoResults } from '../../test/helpers/demoResults';
import type { DemoStory } from '../../demo/demoResults';
import ImprovementPanel from './ImprovementPanel';

const story = (): DemoStory => makeDemoResults().story;

describe('ImprovementPanel', () => {
  it('Given the exported story, when rendered, then best/median/worst top-chunk scores and the spread show', () => {
    /**
     * Scenario: The story numbers come straight from the export, labelled as top-chunk similarity.
     * Slice: 56 Part C2 - improvement numbers
     */
    // -- Given / When --
    render(<ImprovementPanel story={story()} />);

    // -- Then --
    expect(screen.getByText('Best top-chunk score').nextSibling).toHaveTextContent('100.0');
    expect(screen.getByText('Median top-chunk score').nextSibling).toHaveTextContent('95.0');
    expect(screen.getByText('Worst top-chunk score').nextSibling).toHaveTextContent('15.0');
    expect(screen.getByText('Top-chunk spread').nextSibling).toHaveTextContent('85.0');
  });

  it('Given the story, when rendered, then the best and worst query averages are shown', () => {
    /**
     * Scenario: Alongside the top-chunk score, the query-average metric is shown for both runs.
     * Slice: 56 Part C2 - honesty: show the query average, never retyped
     */
    // -- Given --
    const base = story();
    const withAverages: DemoStory = {
      ...base,
      best: { ...base.best, query_avg_score: 10 },
      worst: { ...base.worst, query_avg_score: 26 },
    };

    // -- When --
    render(<ImprovementPanel story={withAverages} />);

    // -- Then --
    expect(screen.getByText(/best 10\.0, worst 26\.0/)).toBeInTheDocument();
  });

  it('Given best query-average below worst, when rendered, then the ordering-caveat note appears', () => {
    /**
     * Scenario: Ranking by top single-chunk similarity can disagree with the all-query average.
     * Slice: 56 Part C2 - honesty: ordering caveat when the average moves the other way
     */
    // -- Given --
    const base = story();
    const conflicting: DemoStory = {
      ...base,
      best: { ...base.best, query_avg_score: 10 },
      worst: { ...base.worst, query_avg_score: 26 },
    };

    // -- When --
    render(<ImprovementPanel story={conflicting} />);

    // -- Then --
    expect(
      screen.getByText(/ranked by their top single-chunk similarity first; the average across all queries can move/),
    ).toBeInTheDocument();
  });

  it('Given best query-average at or above worst, when rendered, then the caveat note is absent', () => {
    /**
     * Scenario: When the two metrics agree, no caveat is shown.
     * Slice: 56 Part C2 - honesty: no caveat when metrics agree
     */
    // -- Given --
    const base = story();
    const agreeing: DemoStory = {
      ...base,
      best: { ...base.best, query_avg_score: 30 },
      worst: { ...base.worst, query_avg_score: 10 },
    };

    // -- When --
    render(<ImprovementPanel story={agreeing} />);

    // -- Then --
    expect(screen.queryByText(/the average across all queries can move/)).toBeNull();
  });

  it('Given the chosen question, when rendered, then its text and the top-1 gap appear', () => {
    /**
     * Scenario: The panel names the question and its worst→best top-1 similarity jump.
     * Slice: 56 Part C2 - the question
     */
    // -- Given / When --
    render(<ImprovementPanel story={story()} />);

    // -- Then --
    expect(screen.getByText('What is the Pell Grant deadline?')).toBeInTheDocument();
    expect(screen.getByText(/15\.0 → 100\.0/)).toBeInTheDocument();
    expect(screen.getByText(/gap 85\.0/)).toBeInTheDocument();
  });

  it('Given both runs, when rendered, then the best and worst top chunks show side by side', () => {
    /**
     * Scenario: Two columns compare the best and worst runs' retrieved chunks.
     * Slice: 56 Part C2 - side-by-side chunks
     */
    // -- Given / When --
    render(<ImprovementPanel story={story()} />);

    // -- Then --
    const best = screen.getByText('Best run — top chunks').closest('div') as HTMLElement;
    const worst = screen.getByText('Worst run — top chunks').closest('div') as HTMLElement;
    expect(within(best).getByText('chunk 1 for run-redis-best')).toBeInTheDocument();
    expect(within(worst).getByText('chunk 1 for run-mongo-worst')).toBeInTheDocument();
  });

  it('Given a run with no exported chunks, when rendered, then an empty-state line shows', () => {
    /**
     * Scenario: A run whose chunks were not exported still renders without error.
     * Slice: 56 Part C2 - chunk empty state
     */
    // -- Given --
    const base = story();
    const empty: DemoStory = { ...base, worst_top_chunks: [] };

    // -- When --
    render(<ImprovementPanel story={empty} />);

    // -- Then --
    expect(screen.getByText('No chunks were exported for this run.')).toBeInTheDocument();
  });
});
