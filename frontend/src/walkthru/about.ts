/**
 * Bundled About-box content (Slice 56 Part C1).
 *
 * Reads the numbered Markdown sections from src/walkthru/about/, a mirror of
 * docs/about/ kept in sync by `npm run sync:about` (runs before `npm run build`) and checked for
 * drift by about.test.ts. The mirror exists because docs/ is outside the Vite root and outside
 * the Docker frontend build context. Everything is bundled: no network access at runtime.
 */

export type AboutSection = {
  /** File name without the numeric prefix and extension, e.g. `evals-underway`. */
  id: string;
  markdown: string;
};

const markdownFiles = import.meta.glob('./about/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

const fileName = (path: string): string => path.slice(path.lastIndexOf('/') + 1);

/** Sections in file-name order; adding or deleting a numbered file adds or removes a section. */
export const ABOUT_SECTIONS: AboutSection[] = Object.entries(markdownFiles)
  .sort(([a], [b]) => a.localeCompare(b))
  .map(([path, markdown]) => ({
    id: fileName(path).replace(/^\d+-/, '').replace(/\.md$/, ''),
    markdown,
  }));
