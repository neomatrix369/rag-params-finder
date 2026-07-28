/**
 * Tests for AppPageChrome tone and optional slots.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 Phase B — canvas/darkFrame, footnote, meta/hint slots
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import AppPageChrome from './AppPageChrome';

describe('AppPageChrome', () => {
  it('Given canvas tone with all slots, when rendered, then title and footnote appear', () => {
    /**
     * Scenario: Default chrome shows brand, title, and CLI footnote.
     * Slice: 44 Phase B — AppPageChrome
     */
    // -- Given / When --
    render(
      <AppPageChrome
        pageEyebrow="Experiments"
        pageTitle="All sweeps"
        pageHint="Read-only dashboard"
        pageMeta={<span>meta-id</span>}
        topRight={<button type="button">Action</button>}
      >
        <main>Body</main>
      </AppPageChrome>,
    );

    // -- Then --
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByText('All sweeps')).toBeInTheDocument();
    expect(screen.getByText('meta-id')).toBeInTheDocument();
    expect(screen.getByText('Read-only dashboard')).toBeInTheDocument();
    expect(screen.getByText('Body')).toBeInTheDocument();
  });

  it('Given darkFrame without footnote, when rendered, then footnote summary is absent', () => {
    /**
     * Scenario: Dense detail pages can hide the expandable footnote.
     * Slice: 44 Phase B — AppPageChrome
     */
    // -- Given / When --
    render(
      <AppPageChrome
        pageTitle="Detail"
        tone="darkFrame"
        showDashboardFootnote={false}
      />,
    );

    // -- Then --
    expect(screen.getByText('Detail')).toBeInTheDocument();
    expect(screen.queryByText(/CLI/i)).toBeNull();
  });
});
