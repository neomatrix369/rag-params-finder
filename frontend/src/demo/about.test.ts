/**
 * Tests for the bundled About-box content loader.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 56 Part C1 - section order, honest-copy rules, docs/about mirror drift
 */
import { describe, expect, it } from 'vitest';
import { ABOUT_SECTIONS, resolveAboutAsset } from './about';

const docsMarkdown = import.meta.glob('../../../docs/about/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

const docsSvg = import.meta.glob('../../../docs/about/*.svg', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

const mirrorSvg = import.meta.glob('./about/*.svg', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

const fileName = (path: string): string => path.slice(path.lastIndexOf('/') + 1);

describe('ABOUT_SECTIONS', () => {
  it('Given the bundled files, when loaded, then the nine shipped sections are in spec order', () => {
    /**
     * Scenario: Sections follow the Part C1 order; the golden-master section (Part J) is absent.
     * Slice: 56 Part C1 - About content
     */
    // -- Given / When --
    const ids = ABOUT_SECTIONS.map((section) => section.id);

    // -- Then --
    expect(ids).toEqual([
      'problem',
      'how-it-works',
      'improvement',
      'redis-8',
      'evals-underway',
      'coming-next',
      'try-it',
      'feedback',
      'thanks',
    ]);
  });

  it('Given the About copy, when scanned, then it avoids correctness claims and names the credits', () => {
    /**
     * Scenario: Copy honesty rules - "similarity score" wording; only the disclaimer
     *   sections may mention accuracy/correctness/hit-rate, and only to deny them.
     * Slice: 56 Part C1 - About content
     */
    // -- Given --
    const all = ABOUT_SECTIONS.map((section) => section.markdown).join('\n');
    const claimingSections = ABOUT_SECTIONS.filter(
      (section) => section.id !== 'evals-underway' && section.id !== 'improvement',
    );
    const banner = ABOUT_SECTIONS.find((section) => section.id === 'evals-underway');

    // -- When / Then --
    claimingSections.forEach((section) => {
      expect(section.markdown).not.toMatch(/accura|correct|\bhit\b/i);
    });
    expect(banner?.markdown).toMatch(/Evaluations are underway/);
    expect(banner?.markdown).toMatch(/not accuracy, correctness or hit-rate/);
    expect(all).toMatch(/similarity score/i);
    expect(all).toContain('Samuel Agbede');
    expect(all).toContain('Redis');
    expect(all).toContain('japanese-work-life-balancer');
    expect(all).toContain('Risako');
    expect(all).toContain('MIT');
    expect(all).toContain('https://github.com/neomatrix369/rag-params-finder');
  });

  it('Given docs/about, when compared with the bundled mirror, then they are identical', () => {
    /**
     * Scenario: src/demo/about is a mirror of docs/about; drift fails the build early.
     * Slice: 56 Part C1 - Before-Check (docs/ is outside the Docker build context)
     */
    // -- Given --
    const docs = Object.fromEntries(
      Object.entries(docsMarkdown)
        .filter(([path]) => /^\d{2}-.+\.md$/.test(fileName(path)))
        .map(([path, text]) => [fileName(path), text]),
    );
    const mirror = Object.fromEntries(
      ABOUT_SECTIONS.map((section, index) => [
        `${String(index + 1).padStart(2, '0')}-${section.id}.md`,
        section.markdown,
      ]),
    );

    // -- When / Then --
    expect(Object.keys(docs).length).toBeGreaterThan(0);
    expect(Object.values(mirror)).toEqual(Object.values(docs));
    expect(Object.fromEntries(Object.entries(mirrorSvg).map(([p, t]) => [fileName(p), t]))).toEqual(
      Object.fromEntries(Object.entries(docsSvg).map(([p, t]) => [fileName(p), t])),
    );
  });
});

describe('resolveAboutAsset', () => {
  it('Given the QR file name, when resolved, then a bundled URL is returned', () => {
    /**
     * Scenario: The committed static QR SVG is served from the bundle.
     * Slice: 56 Part C1 - offline QR
     */
    // -- Given / When / Then --
    expect(resolveAboutAsset('qr.svg')).toEqual(expect.stringContaining('qr'));
  });

  it('Given an unknown name, when resolved, then undefined is returned', () => {
    /**
     * Scenario: Unknown assets never fall back to a remote URL.
     * Slice: 56 Part C1 - offline QR
     */
    // -- Given / When / Then --
    expect(resolveAboutAsset('https://example.com/x.svg')).toBeUndefined();
  });
});
