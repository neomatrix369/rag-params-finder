/**
 * Tests for AboutDialog content: section order, banner removal, offline rendering.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 56 Part C1 - About box GWT scenarios (sections, banner, network off)
 */
import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ABOUT_SECTIONS } from '../../demo/about';
import { WalkthruContext, type WalkthruActions } from '../../walkthru/WalkthruContext';
import AboutDialog from './AboutDialog';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('AboutDialog', () => {
  it('Given the dialog is closed, when rendered, then nothing is shown', () => {
    /**
     * Scenario: Closed About dialog mounts nothing.
     * Slice: 56 Part C1 - About box
     */
    // -- Given / When --
    render(<AboutDialog open={false} onClose={vi.fn()} />);

    // -- Then --
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('Given the dialog is open, when rendered, then the nine shipped sections appear in order', () => {
    /**
     * Scenario: Sections 1-9 render in spec order; section 10 (golden master, Part J) is absent.
     * Slice: 56 Part C1 - About box ("10 sections in order", link only if Part J shipped)
     */
    // -- Given / When --
    render(<AboutDialog open onClose={vi.fn()} />);

    // -- Then --
    const dialog = screen.getByRole('dialog', { name: 'About RAG Params Finder' });
    const sections = Array.from(dialog.querySelectorAll('section[data-section]')).map((el) =>
      el.getAttribute('data-section'),
    );
    expect(sections).toEqual(ABOUT_SECTIONS.map((section) => section.id));
    expect(sections).toHaveLength(9);
    expect(sections[0]).toBe('problem');
    expect(sections[4]).toBe('evals-underway');
    expect(within(dialog).getByRole('heading', { level: 3, name: /Which settings should my RAG app use/ })).toBeVisible();
    expect(within(dialog).queryByText(/golden master/i)).toBeNull();
  });

  it('Given the open dialog, when read, then problem is a question and the credits are shown', () => {
    /**
     * Scenario: Key content is present - the problem as a question, repo link, thanks, and no QR image.
     * Slice: 56 Part C1 - About box
     */
    // -- Given / When --
    render(<AboutDialog open onClose={vi.fn()} />);

    // -- Then --
    expect(screen.getAllByRole('heading', { name: /\?$/ })[0]).toHaveTextContent(/Which settings/);
    expect(screen.queryByRole('img')).toBeNull();
    expect(screen.getByText(/Samuel Agbede/)).toBeInTheDocument();
    const repoLinks = screen.getAllByRole('link', { name: 'github.com/neomatrix369/rag-params-finder' });
    expect(repoLinks[0]).toHaveAttribute('href', 'https://github.com/neomatrix369/rag-params-finder');
    expect(screen.getByRole('link', { name: 'japanese-work-life-balancer' })).toBeInTheDocument();
  });

  it('Given the evals banner section, when it is left out of the sections, then the banner is gone', () => {
    /**
     * Scenario: The banner is removable by one change - deleting docs/about/05-evals-underway.md,
     *   which here is the same as dropping that entry from the section list.
     * Slice: 56 Part C1 - About box (banner removable)
     */
    // -- Given --
    const withBanner = render(<AboutDialog open onClose={vi.fn()} />);
    expect(screen.getByText(/Proper evaluation is still to come/)).toBeInTheDocument();
    expect(screen.queryByText(/underway/i)).toBeNull();
    withBanner.unmount();

    // -- When --
    render(
      <AboutDialog
        open
        onClose={vi.fn()}
        sections={ABOUT_SECTIONS.filter((section) => section.id !== 'evals-underway')}
      />,
    );

    // -- Then --
    expect(screen.queryByText(/Proper evaluation is still to come/)).toBeNull();
    expect(screen.getByRole('heading', { name: /Which settings/ })).toBeInTheDocument();
  });

  it('Given fetch throws, when the dialog opens, then all content renders and no request is made', () => {
    /**
     * Scenario: Network off - all Markdown is bundled; nothing is fetched.
     * Slice: 56 Part C1 - About box (offline)
     */
    // -- Given --
    const fetchMock = vi.fn(() => {
      throw new Error('network is off');
    });
    vi.stubGlobal('fetch', fetchMock);

    // -- When --
    render(<AboutDialog open onClose={vi.fn()} />);

    // -- Then --
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getAllByRole('heading', { level: 3 })).toHaveLength(8);
  });

  it('Given the dialog is open, when Close is clicked, then onClose is called', () => {
    /**
     * Scenario: The About dialog forwards close requests.
     * Slice: 56 Part C1 - About box
     */
    // -- Given --
    const onClose = vi.fn();
    render(<AboutDialog open onClose={onClose} />);

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    // -- Then --
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('Given no Walkthru provider, when opened, then the demo entry buttons are hidden', () => {
    /**
     * Scenario: Rendered outside the App, the About box shows content only (no dangling controls).
     * Slice: 56 Part C2 - demo buttons gated on the context being available
     */
    // -- Given / When --
    render(<AboutDialog open onClose={vi.fn()} />);

    // -- Then --
    expect(screen.queryByRole('button', { name: /Start Walkthru/ })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Open the demo' })).toBeNull();
  });

  it('Given the Walkthru context, when the demo buttons are clicked, then they close the dialog and act', () => {
    /**
     * Scenario: Start Walkthru and Open the demo both close the About box, then run their action.
     * Slice: 56 Part C2 - enabled Start Walkthru button + demo entry point
     */
    // -- Given --
    const onClose = vi.fn();
    const actions: WalkthruActions = { startWalkthru: vi.fn(), openDemo: vi.fn(), available: true };
    render(
      <WalkthruContext.Provider value={actions}>
        <AboutDialog open onClose={onClose} />
      </WalkthruContext.Provider>,
    );

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: /Start Walkthru/ }));
    // -- Then --
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(actions.startWalkthru).toHaveBeenCalledTimes(1);

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Open the demo' }));
    // -- Then --
    expect(onClose).toHaveBeenCalledTimes(2);
    expect(actions.openDemo).toHaveBeenCalledTimes(1);
  });
});
