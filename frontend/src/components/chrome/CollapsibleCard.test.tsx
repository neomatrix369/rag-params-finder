/**
 * Tests for CollapsibleCard open/close and localStorage persistence.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 Phase B — toggle, storageKey, compact title
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import CollapsibleCard from './CollapsibleCard';
import { aboutLabel } from './infoTipUtils';

describe('CollapsibleCard', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('Given defaultOpen true, when rendered, then children are visible', () => {
    /**
     * Scenario: Default-open card shows body content.
     * Slice: 44 Phase B — CollapsibleCard
     */
    // -- Given / When --
    render(
      <CollapsibleCard title="Stats" defaultOpen>
        <p>Body content</p>
      </CollapsibleCard>,
    );

    // -- Then --
    expect(screen.getByText('Body content')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Stats/ })).toHaveAttribute('aria-expanded', 'true');
  });

  it('Given open card, when toggled, then children hide and storage updates', () => {
    /**
     * Scenario: Toggle persists open state to localStorage.
     * Slice: 44 Phase B — CollapsibleCard
     */
    // -- Given --
    render(
      <CollapsibleCard title="Panel" storageKey="test-panel" defaultOpen>
        <span>Inner</span>
      </CollapsibleCard>,
    );

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: /Panel/ }));

    // -- Then --
    expect(screen.queryByText('Inner')).toBeNull();
    expect(localStorage.getItem('test-panel')).toBe('false');
  });

  it('Given stored closed state, when mounted, then children are hidden', () => {
    /**
     * Scenario: localStorage overrides defaultOpen.
     * Slice: 44 Phase B — CollapsibleCard
     */
    // -- Given --
    localStorage.setItem('stored-closed', 'false');

    // -- When --
    render(
      <CollapsibleCard title="Stored" storageKey="stored-closed" defaultOpen compact>
        <span>Hidden</span>
      </CollapsibleCard>,
    );

    // -- Then --
    expect(screen.queryByText('Hidden')).toBeNull();
    expect(screen.getByRole('button', { name: /Stored/ })).toHaveAttribute('aria-expanded', 'false');
  });

  it('Given a collapsed card, when open=true is passed, then children show and the card is expanded', () => {
    /**
     * Scenario: An open override forces a collapsed card open (Walkthru step entry, Part C2).
     * Slice: 56 Part C1 - CollapsibleCard open override
     */
    // -- Given --
    const { rerender } = render(
      <CollapsibleCard title="Panel" defaultOpen={false}>
        <span>Inner</span>
      </CollapsibleCard>,
    );
    expect(screen.queryByText('Inner')).toBeNull();

    // -- When --
    rerender(
      <CollapsibleCard title="Panel" defaultOpen={false} open>
        <span>Inner</span>
      </CollapsibleCard>,
    );

    // -- Then --
    expect(screen.getByText('Inner')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Panel/ })).toHaveAttribute('aria-expanded', 'true');
  });

  it('Given an open card, when open=false is passed, then children hide', () => {
    /**
     * Scenario: The override can also force a card closed.
     * Slice: 56 Part C1 - CollapsibleCard open override
     */
    // -- Given / When --
    render(
      <CollapsibleCard title="Panel" defaultOpen open={false}>
        <span>Inner</span>
      </CollapsibleCard>,
    );

    // -- Then --
    expect(screen.queryByText('Inner')).toBeNull();
  });

  it('Given a forced-open card, when the override is removed, then the user state returns', () => {
    /**
     * Scenario: Dropping the override restores the card's own state with no bookkeeping.
     * Slice: 56 Part C1 - CollapsibleCard open override (restore on Walkthru exit)
     */
    // -- Given --
    const { rerender } = render(
      <CollapsibleCard title="Panel" defaultOpen={false} open>
        <span>Inner</span>
      </CollapsibleCard>,
    );
    expect(screen.getByText('Inner')).toBeInTheDocument();

    // -- When --
    rerender(
      <CollapsibleCard title="Panel" defaultOpen={false}>
        <span>Inner</span>
      </CollapsibleCard>,
    );

    // -- Then --
    expect(screen.queryByText('Inner')).toBeNull();
  });

  it('Given an override, when the header is clicked, then state and storage are untouched', () => {
    /**
     * Scenario: While overridden, toggling does nothing and writes nothing to localStorage.
     * Slice: 56 Part C1 - CollapsibleCard open override
     */
    // -- Given --
    render(
      <CollapsibleCard title="Panel" storageKey="forced" defaultOpen={false} open>
        <span>Inner</span>
      </CollapsibleCard>,
    );

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: /Panel/ }));

    // -- Then --
    expect(screen.getByText('Inner')).toBeInTheDocument();
    expect(localStorage.getItem('forced')).toBeNull();
  });

  it('Given an explain prop, when rendered, then the tip is a sibling button, not nested in the toggle', () => {
    /**
     * Scenario: CollapsibleCard.explain adds an InfoTip beside the header without nesting buttons.
     * Slice: 67C — explain UI.
     * Given a card with explain,
     * When the info button is tapped,
     * Then the tip opens, the card stays expanded, and no button contains another button.
     */
    // -- Given --
    render(
      <CollapsibleCard title="Stats" explain="How stats are counted">
        <p>Body</p>
      </CollapsibleCard>,
    );
    const toggle = screen.getByRole('button', { name: /^Stats/ });
    const info = screen.getByRole('button', { name: aboutLabel('Stats') });
    // -- When --
    fireEvent.click(info);
    // -- Then --
    expect(screen.getByText('How stats are counted')).toBeVisible();
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(toggle.contains(info)).toBe(false);
  });
});
