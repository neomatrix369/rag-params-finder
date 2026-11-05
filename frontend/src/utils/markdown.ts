/**
 * Tiny in-repo Markdown parser for the About box (Slice 56 Part C1, DECISIONS #279 fallback).
 *
 * Covers headings, paragraphs, bullet/numbered lists, blockquotes, fenced code, and the inline
 * marks **bold**, *italic*, `code`, [links](url) and ![images](src). It outputs plain data (never
 * HTML), so rendering cannot inject markup; link targets are limited to http(s), mailto and anchors.
 */

export type Inline =
  | { type: 'text'; text: string }
  | { type: 'code'; text: string }
  | { type: 'bold' | 'italic'; children: Inline[] }
  | { type: 'link'; href: string; children: Inline[] }
  | { type: 'image'; alt: string; src: string };

export type Block =
  | { type: 'heading'; level: number; inline: Inline[] }
  | { type: 'paragraph'; inline: Inline[] }
  | { type: 'quote'; inline: Inline[] }
  | { type: 'list'; ordered: boolean; items: Inline[][] }
  | { type: 'code'; text: string };

// image | link | code | bold | italic - alternatives are tried left to right at each position.
const INLINE = /!\[([^\]]*)\]\(([^)\s]+)\)|\[([^\]]+)\]\(([^)\s]+)\)|`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*/g;
const SAFE_HREF = /^(https?:\/\/|mailto:|#)/i;
const HEADING = /^(#{1,6})\s+(.*)$/;
const BULLET = /^\s*[-*]\s+(.*)$/;
const NUMBERED = /^\s*\d+\.\s+(.*)$/;
const QUOTE = /^>\s?(.*)$/;

function inlineNode(match: RegExpMatchArray): Inline {
  const [, imageAlt, imageSrc, linkText, linkHref, code, bold, italic] = match;
  if (imageSrc !== undefined) return { type: 'image', alt: imageAlt, src: imageSrc };
  if (linkHref !== undefined) {
    const children = parseInline(linkText);
    // An unsafe target (javascript:, data:, relative...) keeps its text but loses the link.
    return SAFE_HREF.test(linkHref)
      ? { type: 'link', href: linkHref, children }
      : { type: 'text', text: linkText };
  }
  if (code !== undefined) return { type: 'code', text: code };
  if (bold !== undefined) return { type: 'bold', children: parseInline(bold) };
  return { type: 'italic', children: parseInline(italic) };
}

export function parseInline(text: string): Inline[] {
  const nodes: Inline[] = [];
  let last = 0;
  for (const match of text.matchAll(INLINE)) {
    const start = match.index as number;
    if (start > last) nodes.push({ type: 'text', text: text.slice(last, start) });
    nodes.push(inlineNode(match));
    last = start + match[0].length;
  }
  if (last < text.length) nodes.push({ type: 'text', text: text.slice(last) });
  return nodes;
}

export function parseMarkdown(source: string): Block[] {
  const remaining = source.split(/\r?\n/);
  const blocks: Block[] = [];
  let paragraph: string[] = [];
  let quote: string[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;

  const flush = (): void => {
    if (paragraph.length > 0) blocks.push({ type: 'paragraph', inline: parseInline(paragraph.join(' ')) });
    if (quote.length > 0) blocks.push({ type: 'quote', inline: parseInline(quote.join(' ')) });
    if (list) blocks.push({ type: 'list', ordered: list.ordered, items: list.items.map(parseInline) });
    paragraph = [];
    quote = [];
    list = null;
  };

  const addListItem = (ordered: boolean, text: string): void => {
    if (list && list.ordered !== ordered) flush();
    if (!list) {
      flush();
      list = { ordered, items: [] };
    }
    list.items.push(text);
  };

  while (remaining.length > 0) {
    const line = remaining.shift() as string;
    if (line.startsWith('```')) {
      flush();
      const code: string[] = [];
      while (remaining.length > 0 && !remaining[0].startsWith('```')) code.push(remaining.shift() as string);
      remaining.shift(); // closing fence (a no-op when the fence never closes)
      blocks.push({ type: 'code', text: code.join('\n') });
      continue;
    }
    const heading = HEADING.exec(line);
    const bullet = BULLET.exec(line);
    const numbered = NUMBERED.exec(line);
    const quoted = QUOTE.exec(line);
    if (heading) {
      flush();
      blocks.push({ type: 'heading', level: heading[1].length, inline: parseInline(heading[2]) });
    } else if (bullet) {
      addListItem(false, bullet[1]);
    } else if (numbered) {
      addListItem(true, numbered[1]);
    } else if (quoted) {
      if (quote.length === 0) flush();
      quote.push(quoted[1]);
    } else if (line.trim() === '') {
      flush();
    } else {
      if (paragraph.length === 0) flush();
      paragraph.push(line.trim());
    }
  }
  flush();
  return blocks;
}
