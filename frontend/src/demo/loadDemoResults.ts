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

/** String fields the UI reads from each run. */
const RUN_STRING_FIELDS = [
  'run_id',
  'store',
  'group_id',
  'embedding_model',
  'chunking_method',
  'retrieval_method',
  'phase',
] as const;
/** Number fields the UI reads from each run. */
const RUN_NUMBER_FIELDS = ['rank', 'store_rank', 'chunk_size', 'max_score', 'query_avg_score', 'elapsed_ms'] as const;

/**
 * Narrows the imported JSON to `DemoResults`, throwing a field-named error on any shape mismatch.
 * Validates the top-level shape, the story (including `question`, which may be null or a well-formed
 * object), every field of each run the UI reads (reporting the first failing entry index and field),
 * and that each store summary carries a run_count and best_run_id.
 */
export function assertDemoResults(value: unknown): asserts value is DemoResults {
  const fail = (field: string): never => {
    throw new Error(`demo-results.json: missing or malformed "${field}"`);
  };
  const str = (obj: Record<string, unknown>, field: string, path: string): void => {
    // eslint-disable-next-line security/detect-object-injection -- field is from a fixed literal list
    if (typeof obj[field] !== 'string') fail(`${path}.${field}`);
  };
  const num = (obj: Record<string, unknown>, field: string, path: string): void => {
    // eslint-disable-next-line security/detect-object-injection -- field is from a fixed literal list
    if (typeof obj[field] !== 'number') fail(`${path}.${field}`);
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

  // question is null (best and worst share no question) OR a well-formed object.
  if (story.question !== null) {
    if (!isObject(story.question)) fail('story.question');
    const q = story.question as Record<string, unknown>;
    str(q, 'text', 'story.question');
    str(q, 'focus', 'story.question');
    num(q, 'best_top1', 'story.question');
    num(q, 'worst_top1', 'story.question');
    num(q, 'gap', 'story.question');
  }

  const runs = root.runs as unknown[];
  if (runs.length === 0) fail('runs (empty array)');
  runs.forEach((entry, i) => {
    const path = `runs[${i}]`;
    if (!isObject(entry)) fail(path);
    const run = entry as Record<string, unknown>;
    for (const field of RUN_STRING_FIELDS) str(run, field, path);
    for (const field of RUN_NUMBER_FIELDS) num(run, field, path);
    if (!Array.isArray(run.top_results)) fail(`${path}.top_results`);
    (run.top_results as unknown[]).forEach((top, j) => {
      const tpath = `${path}.top_results[${j}]`;
      if (!isObject(top)) fail(tpath);
      const result = top as Record<string, unknown>;
      str(result, 'query_text', tpath);
      num(result, 'score', tpath);
      str(result, 'chunk_text', tpath);
    });
  });

  for (const [name, summary] of Object.entries(root.stores as Record<string, unknown>)) {
    const path = `stores["${name}"]`;
    if (!isObject(summary)) fail(path);
    const store = summary as Record<string, unknown>;
    num(store, 'run_count', path);
    str(store, 'best_run_id', path);
  }
}

assertDemoResults(data);

export const DEMO_RESULTS: DemoResults = data;

/** Returns the bundled demo results. A function so call sites read like a data source, not a constant. */
export function loadDemoResults(): DemoResults {
  return DEMO_RESULTS;
}
