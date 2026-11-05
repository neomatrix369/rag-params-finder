/**
 * Tests for the offline demo-data loader and the docs/about mirror.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part C2 - typed offline load + demo-results.json drift against docs/about.
 */
import { describe, expect, it } from 'vitest';
import { makeDemoResults } from '../test/helpers/demoResults';
import { DEMO_RESULTS, assertDemoResults, loadDemoResults } from './loadDemoResults';

// Raw text of both the source of truth and the bundled mirror, for the drift check.
const docsJson = import.meta.glob('../../../docs/about/demo-results.json', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

const mirrorJson = import.meta.glob('./demo-results.json', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

describe('loadDemoResults', () => {
  it('Given the bundled JSON, when loaded, then it is a well-formed DemoResults payload', () => {
    /**
     * Scenario: The loader returns real, typed demo data with no network call.
     * Slice: 56 Part C2 - offline data loader
     */
    // -- Given / When --
    const results = loadDemoResults();

    // -- Then --
    expect(results).toBe(DEMO_RESULTS);
    expect(results.schema_version).toBeGreaterThanOrEqual(1);
    expect(results.runs.length).toBeGreaterThan(0);
    expect(Object.keys(results.stores).length).toBeGreaterThan(0);
    expect(results.manifest.inputs.databases.length).toBeGreaterThan(0);
    expect(results.story.question.text.length).toBeGreaterThan(0);
  });

  it('Given a primary store, when inspected, then exactly one store is flagged primary', () => {
    /**
     * Scenario: The leaderboard's suggested pick needs a single primary (Redis 8) store.
     * Slice: 56 Part C2 - data contract
     */
    // -- Given / When --
    const primaries = Object.values(DEMO_RESULTS.stores).filter((s) => s.is_primary);

    // -- Then --
    expect(primaries).toHaveLength(1);
  });

  it('Given a well-formed payload, when validated, then assertDemoResults accepts it', () => {
    /**
     * Scenario: The exporter's real shape passes the load-time check.
     * Slice: 56 Part C2 - runtime shape check (happy path)
     */
    // -- Given / When / Then --
    expect(() => assertDemoResults(makeDemoResults())).not.toThrow();
  });

  it.each([
    ['(root object)', 42],
    ['schema_version', { runs: [], stores: {}, story: {} }],
    ['runs', { schema_version: 1, stores: {}, story: {} }],
    ['stores', { schema_version: 1, runs: [], story: {} }],
    ['story', { schema_version: 1, runs: [], stores: {} }],
    ['story.spread', { schema_version: 1, runs: [], stores: {}, story: {} }],
    ['story.spread.max_score', { schema_version: 1, runs: [], stores: {}, story: { spread: {} } }],
    [
      'story.spread.query_avg_score',
      { schema_version: 1, runs: [], stores: {}, story: { spread: { max_score: 1 } } },
    ],
  ])('Given a payload missing %s, when validated, then it throws naming that field', (field, payload) => {
    /**
     * Scenario: A shape mismatch fails fast with the offending field name.
     * Slice: 56 Part C2 - runtime shape check (sad paths)
     */
    // -- Given / When / Then --
    expect(() => assertDemoResults(payload)).toThrow(`demo-results.json: missing or malformed "${field}"`);
  });

  it('Given docs/about/demo-results.json, when compared with the bundled mirror, then they are identical', () => {
    /**
     * Scenario: src/demo/demo-results.json is a byte-for-byte mirror; drift fails the build early.
     * Slice: 56 Part C2 - mirror drift (docs/ is outside the Docker build context)
     */
    // -- Given --
    const docs = Object.values(docsJson)[0];
    const mirror = Object.values(mirrorJson)[0];

    // -- When / Then --
    expect(docs).toBeDefined();
    expect(mirror).toEqual(docs);
  });
});
