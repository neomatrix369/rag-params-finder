import type { ReactNode } from 'react';
import { parseMarkdown, type Block, type Inline } from '../../utils/markdown';

type MarkdownViewProps = {
  source: string;
  /** Added to each heading level (capped at h6) so section titles sit below a dialog title. */
  headingOffset?: number;
  /** Maps an image source to a bundled URL. Unresolved images render their alt text only. */
  resolveImage?: (src: string) => string | undefined;
};

const HEADING_CLASS = 'mt-1 font-display text-lg font-semibold text-ink';

function renderInline(
  nodes: Inline[],
  resolveImage: MarkdownViewProps['resolveImage'],
): ReactNode[] {
  return nodes.map((node, index) => {
    switch (node.type) {
      case 'text':
        return node.text;
      case 'code':
        return (
          <code key={index} className="rounded bg-canvas px-1 py-0.5 text-[0.85em]">
            {node.text}
          </code>
        );
      case 'bold':
        return <strong key={index}>{renderInline(node.children, resolveImage)}</strong>;
      case 'italic':
        return <em key={index}>{renderInline(node.children, resolveImage)}</em>;
      case 'link':
        return (
          <a
            key={index}
            href={node.href}
            {...(node.href.startsWith('#') ? {} : { target: '_blank', rel: 'noopener noreferrer' })}
            className="font-medium text-accent-strong underline underline-offset-2"
          >
            {renderInline(node.children, resolveImage)}
          </a>
        );
      default: {
        const url = resolveImage?.(node.src);
        return url ? (
          <img key={index} src={url} alt={node.alt} className="my-2 h-36 w-36 rounded-lg border border-line bg-white" />
        ) : (
          node.alt
        );
      }
    }
  });
}

function renderBlock(
  block: Block,
  index: number,
  headingOffset: number,
  resolveImage: MarkdownViewProps['resolveImage'],
): ReactNode {
  switch (block.type) {
    case 'heading': {
      const Tag = `h${Math.min(block.level + headingOffset, 6)}` as 'h3';
      return (
        <Tag key={index} className={HEADING_CLASS}>
          {renderInline(block.inline, resolveImage)}
        </Tag>
      );
    }
    case 'paragraph':
      return (
        <p key={index} className="mt-3 text-sm leading-relaxed text-ink">
          {renderInline(block.inline, resolveImage)}
        </p>
      );
    case 'quote':
      return (
        <blockquote
          key={index}
          className="mt-3 rounded-lg border-l-4 border-amber-500 bg-amber-50 px-4 py-3 text-sm leading-relaxed text-ink"
        >
          {renderInline(block.inline, resolveImage)}
        </blockquote>
      );
    case 'list': {
      const Tag = block.ordered ? 'ol' : 'ul';
      return (
        <Tag
          key={index}
          className={`mt-3 space-y-1 pl-5 text-sm leading-relaxed text-ink ${block.ordered ? 'list-decimal' : 'list-disc'}`}
        >
          {block.items.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInline(item, resolveImage)}</li>
          ))}
        </Tag>
      );
    }
    default:
      return (
        <pre key={index} className="mt-3 overflow-x-auto rounded-lg bg-frame p-3 font-mono text-xs text-white">
          {block.text}
        </pre>
      );
  }
}

/** Renders Markdown as React elements (never raw HTML). See utils/markdown.ts for the supported subset. */
export default function MarkdownView({ source, headingOffset = 0, resolveImage }: MarkdownViewProps) {
  return <>{parseMarkdown(source).map((block, index) => renderBlock(block, index, headingOffset, resolveImage))}</>;
}
