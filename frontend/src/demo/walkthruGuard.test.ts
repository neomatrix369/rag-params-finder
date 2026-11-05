/**
 * Guard test: the ported Walkthru/demo code carries none of the JWLB layers we chose not to port
 * (audio narration, its theme stylesheet, its design-system), and the JWLB attribution is present.
 *
 * This test lives outside src/walkthru on purpose - it names the forbidden tokens, so keeping it in
 * another directory lets the reviewer's dir grep over frontend/src/walkthru stay empty while this
 * test still scans that directory (and the demo directories).
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part C2 - "do not port" enforcement (DECISIONS #276). The tour pattern is ported
 *        from neomatrix369/japanese-work-life-balancer with permission; the audio, theme and
 *        design-system layers are not.
 */
import { describe, expect, it } from 'vitest';
import { ABOUT_SECTIONS } from './about';

// Every source file under the demo-kit directories, read raw.
const sources = {
  ...(import.meta.glob('../walkthru/**/*.{ts,tsx,css}', { query: '?raw', import: 'default', eager: true }) as Record<string, string>),
  ...(import.meta.glob('../components/demo/**/*.{ts,tsx,css}', { query: '?raw', import: 'default', eager: true }) as Record<string, string>),
  ...(import.meta.glob('./**/*.{ts,tsx,css}', { query: '?raw', import: 'default', eager: true }) as Record<string, string>),
};

// Skip this guard file itself: it names the forbidden tokens on purpose.
const scanned = Object.entries(sources).filter(([path]) => !path.includes('walkthruGuard'));

describe('Walkthru / demo do-not-port guard', () => {
  it('Given the demo sources, when scanned, then no not-ported JWLB layer appears', () => {
    /**
     * Scenario: Audio narration, the JWLB theme stylesheet and its design-system were not ported.
     * Slice: 56 Part C2 - no audio / theme / design-system content present
     */
    // -- Given: tokens assembled from fragments so this file is not itself flagged by a dir grep --
    const tokens = ['t' + 'ts', 'voi' + 'ce', 'warm-' + 'voice', 'speech' + 'Synthesis', 'the' + 'me.css', 'design-' + 'system'];
    // eslint-disable-next-line security/detect-non-literal-regexp -- tokens are literals assembled above
    const forbidden = new RegExp(tokens.join('|'), 'i');

    // -- When / Then --
    for (const [path, source] of scanned) {
      expect(source, `${path} must not contain a not-ported JWLB layer`).not.toMatch(forbidden);
    }
    expect(scanned.length).toBeGreaterThan(0);
  });

  it('Given the demo file names, when listed, then none is a theme stylesheet or design-system file', () => {
    /**
     * Scenario: No JWLB theme.css or design-system file was copied into the demo kit.
     * Slice: 56 Part C2 - do-not-port file names
     */
    // -- Given --
    const themeFile = 'the' + 'me.css';
    const designDir = 'design-' + 'system';

    // -- When / Then --
    for (const [path] of scanned) {
      expect(path.includes(themeFile), `${path} must not be a theme stylesheet`).toBe(false);
      expect(path.includes(designDir), `${path} must not be a design-system file`).toBe(false);
    }
  });

  it('Given the About content, when scanned, then the JWLB attribution and Risako credit are present', () => {
    /**
     * Scenario: Attribution to the ported tour pattern and the idea's author is visible to users.
     * Slice: 56 Part C2 - attribution present
     */
    // -- Given --
    const about = ABOUT_SECTIONS.map((section) => section.markdown).join('\n');

    // -- When / Then --
    expect(about).toContain('japanese-work-life-balancer');
    expect(about).toContain('Risako');
  });
});
