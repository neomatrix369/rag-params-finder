/**
 * Tests for the tiny in-repo Markdown parser used by the About box.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 56 Part C1 - headings, paragraphs, lists, quotes, code, inline marks, safe links
 */
import { describe, expect, it } from 'vitest';
import { parseInline, parseMarkdown } from './markdown';

describe('parseInline', () => {
  it('Given plain text, when parsed, then a single text node is returned', () => {
    /**
     * Scenario: Text without marks is not split.
     * Slice: 56 Part C1 - Markdown renderer
     */
    // -- Given / When --
    const nodes = parseInline('just words');

    // -- Then --
    expect(nodes).toEqual([{ type: 'text', text: 'just words' }]);
  });

  it('Given bold, italic and code marks, when parsed, then each becomes its own node', () => {
    /**
     * Scenario: Inline marks are recognised between text runs.
     * Slice: 56 Part C1 - Markdown renderer
     */
    // -- Given / When --
    const nodes = parseInline('a **bold** b *soft* c `code` d');

    // -- Then --
    expect(nodes).toEqual([
      { type: 'text', text: 'a ' },
      { type: 'bold', children: [{ type: 'text', text: 'bold' }] },
      { type: 'text', text: ' b ' },
      { type: 'italic', children: [{ type: 'text', text: 'soft' }] },
      { type: 'text', text: ' c ' },
      { type: 'code', text: 'code' },
      { type: 'text', text: ' d' },
    ]);
  });

  it('Given an https link and an image, when parsed, then both nodes carry their targets', () => {
    /**
     * Scenario: Links and images keep href/src and alt text.
     * Slice: 56 Part C1 - Markdown renderer
     */
    // -- Given / When --
    const nodes = parseInline('[repo](https://example.com/x) ![qr code](qr.svg)');

    // -- Then --
    expect(nodes).toEqual([
      { type: 'link', href: 'https://example.com/x', children: [{ type: 'text', text: 'repo' }] },
      { type: 'text', text: ' ' },
      { type: 'image', alt: 'qr code', src: 'qr.svg' },
    ]);
  });

  it.each([['java', 'script:alert'].join(''), 'data:text/html,hi', '/relative/path', 'ftp://host/file'])(
    'Given an unsafe link target %s, when parsed, then only the link text survives',
    (href) => {
      /**
       * Scenario: Only http(s), mailto and in-page anchors become links.
       * Slice: 56 Part C1 - Markdown renderer (no script URLs)
       */
      // -- Given / When --
      const nodes = parseInline(`[click](${href})`);

      // -- Then --
      expect(nodes).toEqual([{ type: 'text', text: 'click' }]);
    },
  );

  it.each(['mailto:a@b.co', '#section'])(
    'Given a safe link target %s, when parsed, then a link node is produced',
    (href) => {
      /**
       * Scenario: mailto and anchor targets are allowed.
       * Slice: 56 Part C1 - Markdown renderer
       */
      // -- Given / When --
      const nodes = parseInline(`[go](${href})`);

      // -- Then --
      expect(nodes).toEqual([{ type: 'link', href, children: [{ type: 'text', text: 'go' }] }]);
    },
  );
});

describe('parseMarkdown', () => {
  it('Given headings, paragraphs and a wrapped line, when parsed, then blocks are in order', () => {
    /**
     * Scenario: Consecutive text lines join into one paragraph.
     * Slice: 56 Part C1 - Markdown renderer
     */
    // -- Given --
    const source = '# Title\n\nfirst line\nsecond line\n\n### Small';

    // -- When --
    const blocks = parseMarkdown(source);

    // -- Then --
    expect(blocks).toEqual([
      { type: 'heading', level: 1, inline: [{ type: 'text', text: 'Title' }] },
      { type: 'paragraph', inline: [{ type: 'text', text: 'first line second line' }] },
      { type: 'heading', level: 3, inline: [{ type: 'text', text: 'Small' }] },
    ]);
  });

  it('Given bullet and numbered lists, when parsed, then ordered flag and items are kept', () => {
    /**
     * Scenario: Switching list kind starts a new list; a paragraph before a list is flushed.
     * Slice: 56 Part C1 - Markdown renderer
     */
    // -- Given --
    const source = 'intro\n- one\n* two\n1. first\n2. second\n\nafter';

    // -- When --
    const blocks = parseMarkdown(source);

    // -- Then --
    expect(blocks.map((b) => b.type)).toEqual(['paragraph', 'list', 'list', 'paragraph']);
    expect(blocks[1]).toEqual({
      type: 'list',
      ordered: false,
      items: [[{ type: 'text', text: 'one' }], [{ type: 'text', text: 'two' }]],
    });
    expect(blocks[2]).toMatchObject({ type: 'list', ordered: true });
  });

  it('Given a blockquote spanning two lines, when parsed, then one quote block is returned', () => {
    /**
     * Scenario: Quote lines are merged (this is how the evals banner is authored).
     * Slice: 56 Part C1 - Markdown renderer
     */
    // -- Given / When --
    const blocks = parseMarkdown('> **Note.** line one\n> line two');

    // -- Then --
    expect(blocks).toEqual([
      {
        type: 'quote',
        inline: [
          { type: 'bold', children: [{ type: 'text', text: 'Note.' }] },
          { type: 'text', text: ' line one line two' },
        ],
      },
    ]);
  });

  it('Given fenced code, when parsed, then lines are kept verbatim and marks are not parsed', () => {
    /**
     * Scenario: Code fences preserve content; an unterminated fence runs to the end.
     * Slice: 56 Part C1 - Markdown renderer
     */
    // -- Given / When --
    const closed = parseMarkdown('```\n**not bold**\nsecond\n```\nafter');
    const open = parseMarkdown('```\nrunaway');

    // -- Then --
    expect(closed[0]).toEqual({ type: 'code', text: '**not bold**\nsecond' });
    expect(closed[1].type).toBe('paragraph');
    expect(open).toEqual([{ type: 'code', text: 'runaway' }]);
  });

  it('Given empty input, when parsed, then no blocks are returned', () => {
    /**
     * Scenario: Empty source is harmless.
     * Slice: 56 Part C1 - Markdown renderer
     */
    // -- Given / When / Then --
    expect(parseMarkdown('')).toEqual([]);
  });
});
