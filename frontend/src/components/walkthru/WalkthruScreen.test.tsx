/**
 * Tests for the demo screen (leaderboard + replay + improvement + best settings).
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part C2 - panels + data-tour anchors, collapsed-card open/restore, autoplay pick,
 *        back navigation.
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { makeWalkthruResults } from '../../test/helpers/walkthruResults';
import WalkthruScreen from './WalkthruScreen';

describe('WalkthruScreen', () => {
  it('Given the bundled results, when rendered, then each panel carries its data-tour anchor', () => {
    /**
     * Scenario: The Walkthru spotlights panels by their data-tour anchors.
     * Slice: 56 Part C2 - demo screen anchors
     */
    // -- Given / When --
    const { container } = render(<WalkthruScreen results={makeWalkthruResults()} onBack={() => undefined} />);

    // -- Then --
    for (const anchor of ['leaderboard', 'replay', 'improvement', 'best-settings']) {
      expect(container.querySelector(`[data-tour="${anchor}"]`)).not.toBeNull();
    }
  });

  it('Given no highlight, when rendered, then the improvement card is collapsed', () => {
    /**
     * Scenario: Outside the Walkthru the improvement story starts collapsed.
     * Slice: 56 Part C2 - collapsed by default
     */
    // -- Given / When --
    render(<WalkthruScreen results={makeWalkthruResults()} onBack={() => undefined} />);

    // -- Then: the card title shows but its inner heading does not --
    expect(screen.getByText('The improvement story')).toBeInTheDocument();
    expect(screen.queryByText('What the best settings changed')).toBeNull();
  });

  it('Given the improvement highlight, when set then cleared, then the card opens then restores', () => {
    /**
     * Scenario: The Walkthru's open override opens the card and dropping it restores the collapse.
     * Slice: 56 Part C2 - collapsed-card open + restore
     */
    // -- Given --
    const { rerender } = render(
      <WalkthruScreen results={makeWalkthruResults()} activeHighlight="improvement" onBack={() => undefined} />,
    );
    // -- Then: open --
    expect(screen.getByText('What the best settings changed')).toBeInTheDocument();

    // -- When: highlight dropped (Walkthru exit) --
    rerender(<WalkthruScreen results={makeWalkthruResults()} activeHighlight={null} onBack={() => undefined} />);

    // -- Then: restored to collapsed --
    expect(screen.queryByText('What the best settings changed')).toBeNull();
  });

  it('Given Autoplay on with Redis suggested, when mounted, then the suggested run is selected', () => {
    /**
     * Scenario: On the choice step with Autoplay on, the suggestion drives the replay selection.
     * Slice: 56 Part C2 - choice drives the replay
     */
    // -- Given / When --
    render(
      <WalkthruScreen results={makeWalkthruResults()} autoplay suggestedStore="redis" onBack={() => undefined} />,
    );

    // -- Then: the suggested Redis run row shows as selected (the Select button's label is aria-only,
    // so assert on its visible text) --
    expect(screen.getByText('Selected')).toBeInTheDocument();
  });

  it('Given the back control, when clicked, then onBack fires', () => {
    /**
     * Scenario: The demo screen can be left.
     * Slice: 56 Part C2 - back navigation
     */
    // -- Given --
    const onBack = vi.fn();
    render(<WalkthruScreen results={makeWalkthruResults()} onBack={onBack} />);

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Back to experiments' }));

    // -- Then --
    expect(onBack).toHaveBeenCalled();
  });

  it('Given an empty export, when rendered, then the best-settings card shows a no-runs note', () => {
    /**
     * Scenario: With no bundled runs the best-settings card degrades gracefully.
     * Slice: 56 Part C2 - fallback
     */
    // -- Given --
    const empty = makeWalkthruResults({ runs: [], stores: {} });

    // -- When --
    render(<WalkthruScreen results={empty} onBack={() => undefined} />);

    // -- Then --
    expect(screen.getByText('No runs are bundled with this build.')).toBeInTheDocument();
  });
});
