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
});
