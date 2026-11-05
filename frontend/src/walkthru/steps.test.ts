/**
 * Tests for the Walkthru front-matter parser.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part C2 - step-file parse; a malformed file fails with its own name.
 */
import { describe, expect, it } from 'vitest';
import { WALKTHRU_STEPS, loadSteps, parseStep } from './steps';

const GOOD = `---
id: leaderboard
title: One question, many stores
duration_s: 11
route: walkthru
highlight: leaderboard
choose:
  target: leaderboard
  suggest: redis
---
Same dataset, same questions, different store.
`;

describe('parseStep', () => {
  it('Given a well-formed step file, when parsed, then every front-matter field is read', () => {
    /**
     * Scenario: A complete step with a nested choice block parses into a typed step.
     * Slice: 56 Part C2 - step-file parse
     */
    // -- Given / When --
    const step = parseStep('01-leaderboard.md', GOOD);

    // -- Then --
    expect(step).toEqual({
      id: 'leaderboard',
      title: 'One question, many stores',
      durationS: 11,
      route: 'walkthru',
      highlight: 'leaderboard',
      choose: { target: 'leaderboard', suggest: 'redis' },
      body: 'Same dataset, same questions, different store.',
    });
  });

  it('Given a step without highlight or choose, when parsed, then both default to null', () => {
    /**
     * Scenario: The final "Try it" step is a centred callout with no choice.
     * Slice: 56 Part C2 - step-file parse
     */
    // -- Given --
    const raw = `---
id: try-it
title: Try it yourself
duration_s: 9
route: walkthru
highlight:
---
Open the About box.
`;

    // -- When --
    const step = parseStep('05-try-it.md', raw);

    // -- Then --
    expect(step.highlight).toBeNull();
    expect(step.choose).toBeNull();
  });

  it.each([
    ['no opening fence', 'id: x\n---\nbody', /missing opening/],
    ['no closing fence', '---\nid: x\nbody', /missing closing/],
    ['missing required key', '---\ntitle: X\nduration_s: 5\nroute: walkthru\n---\nbody', /missing required key "id"/],
    ['bad duration', '---\nid: x\ntitle: X\nduration_s: nope\nroute: walkthru\n---\nbody', /positive number/],
    ['unknown route', '---\nid: x\ntitle: X\nduration_s: 5\nroute: moon\n---\nbody', /unknown route/],
    ['choice without suggest', '---\nid: x\ntitle: X\nduration_s: 5\nroute: walkthru\nchoose:\n  target: t\n---\nbody', /both "target" and "suggest"/],
    ['empty body', '---\nid: x\ntitle: X\nduration_s: 5\nroute: walkthru\n---\n', /empty body/],
    ['unparseable line', '---\nid: x\ntitle: X\nduration_s: 5\nroute: walkthru\n!!bad!!\n---\nbody', /cannot parse line/],
  ])(
    'Given a malformed step (%s), when parsed, then it fails naming the file',
    (_label, raw, expected) => {
      /**
       * Scenario: Every malformed shape fails fast with the offending file name.
       * Slice: 56 Part C2 - malformed file fails with its name
       */
      // -- Given / When / Then --
      expect(() => parseStep('99-broken.md', raw)).toThrow(/99-broken\.md/);
      expect(() => parseStep('99-broken.md', raw)).toThrow(expected);
    },
  );
});

describe('loadSteps / WALKTHRU_STEPS', () => {
  it('Given several files, when loaded, then they are ordered by file name', () => {
    /**
     * Scenario: Numbered file names drive step order.
     * Slice: 56 Part C2 - step ordering
     */
    // -- Given --
    const files = {
      './02-replay.md': '---\nid: replay\ntitle: B\nduration_s: 5\nroute: walkthru\n---\nbody b',
      './01-leaderboard.md': GOOD,
    };

    // -- When --
    const steps = loadSteps(files);

    // -- Then --
    expect(steps.map((s) => s.id)).toEqual(['leaderboard', 'replay']);
  });

  it('Given the bundled step files, when loaded, then the five shipped steps are present in order', () => {
    /**
     * Scenario: The shipped Walkthru has the five Part C2 steps.
     * Slice: 56 Part C2 - bundled steps
     */
    // -- Given / When / Then --
    expect(WALKTHRU_STEPS.map((s) => s.id)).toEqual([
      'leaderboard',
      'replay',
      'improvement',
      'best-settings',
      'try-it',
    ]);
    expect(WALKTHRU_STEPS[0].choose).toEqual({ target: 'leaderboard', suggest: 'redis' });
    expect(WALKTHRU_STEPS[4].highlight).toBeNull();
  });
});
