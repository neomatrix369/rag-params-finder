/**
 * Offline loader for the bundled demo data (Slice 56 Part C2).
 *
 * Imports the committed JSON mirror of docs/about/demo-results.json (kept in sync by
 * `npm run sync:about`, drift-checked by loadDemoResults.test.ts). A JSON import is only inferred,
 * not type-checked against `DemoResults`, so the shape is verified at load time by
 * `assertDemoResults`: a mismatch between the exporter output and the hand-mirrored types throws a
 * clear error naming the missing field, rather than failing silently far from here. No `fetch`, no
 * network: the data is part of the bundle.
 */
import type { DemoResults } from './demoResults';
import data from './demo-results.json';

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

/** Narrows the imported JSON to `DemoResults`, throwing a field-named error on any shape mismatch. */
export function assertDemoResults(value: unknown): asserts value is DemoResults {
  const fail = (field: string): never => {
    throw new Error(`demo-results.json: missing or malformed "${field}"`);
  };
  if (!isObject(value)) fail('(root object)');
  const root = value as Record<string, unknown>;
  if (typeof root.schema_version !== 'number') fail('schema_version');
  if (!Array.isArray(root.runs)) fail('runs');
  if (!isObject(root.stores)) fail('stores');
  if (!isObject(root.story)) fail('story');
  const story = root.story as Record<string, unknown>;
  if (!isObject(story.spread)) fail('story.spread');
  const spread = story.spread as Record<string, unknown>;
  if (typeof spread.max_score !== 'number') fail('story.spread.max_score');
  if (typeof spread.query_avg_score !== 'number') fail('story.spread.query_avg_score');
}

assertDemoResults(data);

export const DEMO_RESULTS: DemoResults = data;

/** Returns the bundled demo results. A function so call sites read like a data source, not a constant. */
export function loadDemoResults(): DemoResults {
  return DEMO_RESULTS;
}
