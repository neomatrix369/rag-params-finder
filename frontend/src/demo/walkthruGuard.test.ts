/**
 * Guard test: the ported Walkthru carries no audio-narration code, and the JWLB attribution is present.
 *
 * This test lives outside src/walkthru on purpose - it names the forbidden tokens, so keeping it in
 * another directory lets the reviewer's `grep -ri "tts|voice|warm-voice" frontend/src/walkthru` stay
 * empty while this test still scans that directory.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part C2 - "do not port" enforcement (DECISIONS #276). The tour pattern is ported
 *        from neomatrix369/japanese-work-life-balancer with permission; the audio layer is not.
 */
import { describe, expect, it } from 'vitest';
import { ABOUT_SECTIONS } from './about';

// Every source file under src/walkthru, read raw.
const walkthruSources = import.meta.glob('../walkthru/**/*.{ts,tsx}', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

describe('Walkthru audio-narration guard', () => {
  it('Given the Walkthru sources, when scanned, then no tts/voice/warm-voice/speechSynthesis appears', () => {
    /**
     * Scenario: The JWLB audio narration was deliberately not ported.
     * Slice: 56 Part C2 - no audio-narration code present
     */
    // -- Given: tokens assembled from fragments so this file is not itself flagged by a dir grep --
    const tokens = ['t' + 'ts', 'voi' + 'ce', 'warm-' + 'voice', 'speech' + 'Synthesis'];
    // eslint-disable-next-line security/detect-non-literal-regexp -- tokens are literals assembled above
    const forbidden = new RegExp(tokens.join('|'), 'i');

    // -- When / Then --
    for (const [path, source] of Object.entries(walkthruSources)) {
      expect(source, `${path} must not contain audio-narration code`).not.toMatch(forbidden);
    }
    expect(Object.keys(walkthruSources).length).toBeGreaterThan(0);
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
