/**
 * Tests for MarkdownView rendering of parsed Markdown into safe React elements.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 56 Part C1 - headings offset, links, images, lists, code, quote, no raw HTML
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import MarkdownView from './MarkdownView';

describe('MarkdownView', () => {
  it('Given a level-1 heading and offset 2, when rendered, then an h3 is produced', () => {
    /**
     * Scenario: Section titles sit below the dialog title in the heading outline.
     * Slice: 56 Part C1 - Markdown renderer
     */
    // -- Given / When --
    render(<MarkdownView source="# Hello" headingOffset={2} />);

    // -- Then --
    expect(screen.getByRole('heading', { level: 3, name: 'Hello' })).toBeInTheDocument();
  });

  it('Given a deep heading with a large offset, when rendered, then the level caps at 6', () => {
    /**
     * Scenario: Heading levels never exceed h6.
     * Slice: 56 Part C1 - Markdown renderer
     */
    // -- Given / When --
    render(<MarkdownView source="### Deep" headingOffset={5} />);

    // -- Then --
    expect(screen.getByRole('heading', { level: 6, name: 'Deep' })).toBeInTheDocument();
  });

  it('Given default offset, when a heading renders, then its own level is used', () => {
    /**
     * Scenario: headingOffset defaults to zero.
     * Slice: 56 Part C1 - Markdown renderer
     */
    // -- Given / When --
    render(<MarkdownView source="## Two" />);

    // -- Then --
    expect(screen.getByRole('heading', { level: 2, name: 'Two' })).toBeInTheDocument();
  });

  it('Given inline marks and an https link, when rendered, then semantic elements appear', () => {
    /**
     * Scenario: Bold, italic, code and external links render as strong/em/code/a.
     * Slice: 56 Part C1 - Markdown renderer
     */
    // -- Given / When --
    render(<MarkdownView source="**b** *i* `c` [site](https://example.com)" />);

    // -- Then --
    expect(screen.getByText('b').tagName).toBe('STRONG');
    expect(screen.getByText('i').tagName).toBe('EM');
    expect(screen.getByText('c').tagName).toBe('CODE');
    const link = screen.getByRole('link', { name: 'site' });
    expect(link).toHaveAttribute('href', 'https://example.com');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('Given an in-page anchor link, when rendered, then it does not open a new tab', () => {
    /**
     * Scenario: Anchors stay in the page.
     * Slice: 56 Part C1 - Markdown renderer
     */
    // -- Given / When --
    render(<MarkdownView source="[top](#top)" />);

    // -- Then --
    const link = screen.getByRole('link', { name: 'top' });
    expect(link).not.toHaveAttribute('target');
  });

  it('Given a script link, when rendered, then no anchor is created', () => {
    /**
     * Scenario: javascript: targets never become links.
     * Slice: 56 Part C1 - Markdown renderer (security)
     */
    // -- Given / When --
    render(<MarkdownView source="[bad](javascript:alert)" />);

    // -- Then --
    expect(screen.queryByRole('link')).toBeNull();
    expect(screen.getByText('bad')).toBeInTheDocument();
  });

  it('Given raw HTML in the source, when rendered, then it is shown as text, not elements', () => {
    /**
     * Scenario: Markdown never injects HTML.
     * Slice: 56 Part C1 - Markdown renderer (security)
     */
    // -- Given / When --
    const { container } = render(<MarkdownView source="<img src=x onerror=alert(1)>" />);

    // -- Then --
    expect(container.querySelector('img')).toBeNull();
    expect(container.textContent).toContain('<img src=x onerror=alert(1)>');
  });

  it('Given an image that resolves, when rendered, then an img with alt text appears', () => {
    /**
     * Scenario: Bundled assets (the QR SVG) resolve through the injected resolver.
     * Slice: 56 Part C1 - Markdown renderer
     */
    // -- Given / When --
    render(
      <MarkdownView
        source="![QR code](qr.svg)"
        resolveImage={(src) => (src === 'qr.svg' ? '/assets/qr-hash.svg' : undefined)}
      />,
    );

    // -- Then --
    expect(screen.getByRole('img', { name: 'QR code' })).toHaveAttribute('src', '/assets/qr-hash.svg');
  });

  it('Given an image that does not resolve, when rendered, then the alt text is shown instead', () => {
    /**
     * Scenario: Unknown image sources never produce a network request.
     * Slice: 56 Part C1 - Markdown renderer (offline)
     */
    // -- Given / When --
    render(<MarkdownView source="![missing pic](https://example.com/x.png)" />);

    // -- Then --
    expect(screen.queryByRole('img')).toBeNull();
    expect(screen.getByText('missing pic')).toBeInTheDocument();
  });

  it('Given lists, a quote and code, when rendered, then list, blockquote and pre elements appear', () => {
    /**
     * Scenario: Block elements map to semantic HTML.
     * Slice: 56 Part C1 - Markdown renderer
     */
    // -- Given / When --
    const { container } = render(
      <MarkdownView source={'- a\n- b\n\n1. x\n\n> note\n\n```\ncode block\n```'} />,
    );

    // -- Then --
    expect(container.querySelectorAll('ul > li')).toHaveLength(2);
    expect(container.querySelectorAll('ol > li')).toHaveLength(1);
    expect(container.querySelector('blockquote')).toHaveTextContent('note');
    expect(container.querySelector('pre')).toHaveTextContent('code block');
  });
});
