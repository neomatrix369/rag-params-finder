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
    expect(results.story.question === null || results.story.question.text.length > 0).toBe(true);
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

  // A minimal payload that passes every check, used as the base for deep bad-shape mutations.
  const validRun = () => ({
    run_id: 'r1',
    store: 'redis',
    group_id: 'g1',
    rank: 1,
    store_rank: 1,
    embedding_model: 'm',
    chunking_method: 'recursive',
    chunk_size: 512,
    retrieval_method: 'dense',
    max_score: 10,
    query_avg_score: 5,
    elapsed_ms: 100,
    phase: 'complete',
    top_results: [{ query_text: 'q', score: 10, chunk_text: 'c' }],
  });
  const validPayload = () => ({
    schema_version: 1,
    runs: [validRun()],
    stores: { redis: { run_count: 1, best_run_id: 'r1' } },
    story: { spread: { max_score: 1, query_avg_score: 1 }, question: null },
  });

  it('Given question null or a well-formed object, when validated, then both pass', () => {
    /**
     * Scenario: The exporter emits question=null when best and worst share no question.
     * Slice: 56 Part C2 - question may be null (latent-crash fix)
     */
    // -- Given / When / Then --
    expect(() => assertDemoResults(validPayload())).not.toThrow();
    const withQuestion = {
      ...validPayload(),
      story: {
        spread: { max_score: 1, query_avg_score: 1 },
        question: { text: 't', focus: 'f', best_top1: 1, worst_top1: 0, gap: 1 },
      },
    };
    expect(() => assertDemoResults(withQuestion)).not.toThrow();
  });

  it.each([
    ['story.question.text', { question: { focus: 'f', best_top1: 1, worst_top1: 0, gap: 1 } }],
    ['story.question.best_top1', { question: { text: 't', focus: 'f', worst_top1: 0, gap: 1 } }],
  ])('Given a malformed question missing %s, when validated, then it throws naming that field', (field, storyPatch) => {
    /**
     * Scenario: A non-null question with a missing field is rejected.
     * Slice: 56 Part C2 - question shape check
     */
    // -- Given --
    const payload = { ...validPayload(), story: { spread: { max_score: 1, query_avg_score: 1 }, ...storyPatch } };

    // -- When / Then --
    expect(() => assertDemoResults(payload)).toThrow(`demo-results.json: missing or malformed "${field}"`);
  });

  it.each([
    ['runs (empty array)', { runs: [] }],
    ['runs[0].run_id', { runs: [{ ...validRun(), run_id: 123 }] }],
    ['runs[0].max_score', { runs: [{ ...validRun(), max_score: 'high' }] }],
    ['runs[0].top_results', { runs: [{ ...validRun(), top_results: 'nope' }] }],
    ['runs[0].top_results[0].query_text', { runs: [{ ...validRun(), top_results: [{ score: 1, chunk_text: 'c' }] }] }],
  ])('Given a malformed runs payload (%s), when validated, then it throws naming the first failing field', (field, patch) => {
    /**
     * Scenario: A malformed runs entry is caught at load time, naming its index and field.
     * Slice: 56 Part C2 - deep runs validation (data-flow review)
     */
    // -- Given --
    const payload = { ...validPayload(), ...patch };

    // -- When / Then --
    expect(() => assertDemoResults(payload)).toThrow(`demo-results.json: missing or malformed "${field}"`);
  });

  it.each([
    ['stores["redis"].run_count', { stores: { redis: { best_run_id: 'r1' } } }],
    ['stores["redis"].best_run_id', { stores: { redis: { run_count: 1 } } }],
  ])('Given a store summary missing %s, when validated, then it throws naming that field', (field, patch) => {
    /**
     * Scenario: A store summary missing the fields the leaderboard reads is rejected.
     * Slice: 56 Part C2 - stores validation (data-flow review)
     */
    // -- Given --
    const payload = { ...validPayload(), ...patch };

    // -- When / Then --
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
