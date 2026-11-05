/**
 * Tests for the bundled About-box content loader.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 56 Part C1 - section order, honest-copy rules, docs/about mirror drift
 */
import { describe, expect, it } from 'vitest';
import { ABOUT_SECTIONS } from './about';

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

const walkthruSteps = import.meta.glob('./steps/*.md', {
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
    expect(banner?.markdown).toMatch(/Proper evaluation is still to come/);
    expect(banner?.markdown).not.toMatch(/underway/i);
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
     * Scenario: src/walkthru/about is a mirror of docs/about; drift fails the build early.
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
  });
});

describe('QR code removal', () => {
  it('Given the owner dropped the QR code, when the About sections are read, then none mentions or embeds one', () => {
    /**
     * Scenario: No QR wording or image syntax remains in the About content.
     * Slice: 56 Part C1 - owner scope change 2026-11-05 (no QR code)
     */
    // -- Given / When --
    const texts = ABOUT_SECTIONS.map((section) => section.markdown);

    // -- Then --
    expect(texts.length).toBeGreaterThan(0);
    for (const text of texts) {
      expect(text).not.toMatch(/\bQR\b/i);
      expect(text).not.toContain('![');
    }
  });

  it('Given the Walkthru steps, when read, then none points the audience to a QR code', () => {
    /**
     * Scenario: The tour does not promise a QR code the About box no longer has.
     * Slice: 56 Part C1 - owner scope change 2026-11-05 (no QR code)
     */
    // -- Given / When / Then --
    const steps = Object.values(walkthruSteps);
    expect(steps.length).toBeGreaterThan(0);
    for (const text of steps) {
      expect(text).not.toMatch(/\bQR\b/i);
    }
  });

  it('Given the owner dropped the QR code, when the folders are scanned, then no SVG asset is bundled or mirrored', () => {
    /**
     * Scenario: The static QR file is gone from docs/about and its frontend mirror.
     * Slice: 56 Part C1 - owner scope change 2026-11-05 (no QR code)
     */
    // -- Given / When / Then --
    expect(Object.keys(docsSvg)).toEqual([]);
    expect(Object.keys(mirrorSvg)).toEqual([]);
  });
});
