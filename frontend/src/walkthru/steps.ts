/**
 * Walkthru step definitions, parsed from the bundled Markdown files.
 *
 * Pattern ported from neomatrix369/japanese-work-life-balancer (ui/src/tour/steps.ts) at commit
 * ccdbee1b4a4501b5e5394aafab225a583d630354, with the owner's permission (DECISIONS #276). The idea
 * is credited to Risako. The audio narration, bundled stylesheet and component design library from that repo are NOT ported.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part C2 - tiny front-matter parser (no new dependency); a malformed file fails
 *        the parse with its own file name.
 *
 * Each step is one Markdown file in docs/about/walkthru/, mirrored to src/demo/walkthru/ by
 * `npm run sync:about`. Front-matter keys are flat (id, title, duration_s, route, highlight) plus a
 * nested `choose: {target, suggest}` block. The body is short honest copy; the numbers are read
 * from the bundled demo data at render time, never typed into the step.
 */

/** Screen a step runs on; App maps this onto its own screen state. */
export type WalkthruRoute = 'demo';

export interface WalkthruChoice {
  /** `data-tour` anchor of the list the choice is made on. */
  target: string;
  /** Store whose best run is suggested (e.g. `redis`). */
  suggest: string;
}

export interface WalkthruStep {
  id: string;
  title: string;
  /** Dwell time (seconds) used only while Autoplay is on. */
  durationS: number;
  route: WalkthruRoute;
  /** `data-tour` anchor to spotlight; null = centred callout. */
  highlight: string | null;
  /** Choice step metadata, or null. */
  choose: WalkthruChoice | null;
  /** Rendered body copy (Markdown-free plain text). */
  body: string;
}

const ROUTES: readonly WalkthruRoute[] = ['demo'];

function fail(fileName: string, reason: string): never {
  throw new Error(`Malformed walkthru step "${fileName}": ${reason}`);
}

/** Splits a raw file into its front-matter text and body, or fails with the file name. */
function splitFrontMatter(fileName: string, raw: string): { front: string; body: string } {
  const normalised = raw.replace(/\r\n/g, '\n');
  if (!normalised.startsWith('---\n')) fail(fileName, 'missing opening "---" front-matter fence');
  const end = normalised.indexOf('\n---', 4);
  if (end === -1) fail(fileName, 'missing closing "---" front-matter fence');
  const front = normalised.slice(4, end + 1);
  const body = normalised.slice(end + 4).replace(/^\n+/, '').trim();
  return { front, body };
}

type RawFields = { flat: Map<string, string>; choose: Map<string, string> | null };

/** Reads the flat `key: value` lines and the nested `choose:` block. */
function readFields(fileName: string, front: string): RawFields {
  const flat = new Map<string, string>();
  let choose: Map<string, string> | null = null;
  let inChoose = false;

  for (const line of front.split('\n')) {
    if (line.trim() === '') continue;
    const indented = /^\s+/.test(line);
    const match = /^(\s*)([A-Za-z_]+):\s*(.*)$/.exec(line);
    if (!match) fail(fileName, `cannot parse line "${line.trim()}"`);
    const [, , key, value] = match;

    if (!indented) {
      if (key === 'choose') {
        choose = new Map();
        inChoose = true;
        if (value.trim() !== '') fail(fileName, '"choose" must be a nested block, not an inline value');
        continue;
      }
      inChoose = false;
      flat.set(key, value.trim());
      continue;
    }

    if (!inChoose || choose === null) fail(fileName, `unexpected indented line "${line.trim()}"`);
    choose.set(key, value.trim());
  }

  return { flat, choose };
}

/** Parses one step file; throws with the file name on any malformed input. */
export function parseStep(fileName: string, raw: string): WalkthruStep {
  const { front, body } = splitFrontMatter(fileName, raw);
  const { flat, choose: chooseFields } = readFields(fileName, front);

  const required = ['id', 'title', 'duration_s', 'route'] as const;
  for (const key of required) {
    if (!flat.get(key)) fail(fileName, `missing required key "${key}"`);
  }

  const durationS = Number(flat.get('duration_s'));
  if (!Number.isFinite(durationS) || durationS <= 0) {
    fail(fileName, `"duration_s" must be a positive number, got "${flat.get('duration_s')}"`);
  }

  const route = flat.get('route') as WalkthruRoute;
  if (!ROUTES.includes(route)) fail(fileName, `unknown route "${route}" (expected one of ${ROUTES.join(', ')})`);

  const highlightRaw = flat.get('highlight') ?? '';
  const highlight = highlightRaw.trim() === '' ? null : highlightRaw.trim();

  let choose: WalkthruChoice | null = null;
  if (chooseFields !== null) {
    const target = chooseFields.get('target');
    const suggest = chooseFields.get('suggest');
    if (!target || !suggest) fail(fileName, '"choose" needs both "target" and "suggest"');
    choose = { target, suggest };
  }

  if (body === '') fail(fileName, 'empty body');

  return {
    id: flat.get('id') as string,
    title: flat.get('title') as string,
    durationS,
    route,
    highlight,
    choose,
    body,
  };
}

const fileName = (path: string): string => path.slice(path.lastIndexOf('/') + 1);

/** Parses a map of `path -> raw markdown` into steps, ordered by file name. */
export function loadSteps(files: Record<string, string>): WalkthruStep[] {
  return Object.entries(files)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([path, raw]) => parseStep(fileName(path), raw));
}

const stepFiles = import.meta.glob('../demo/walkthru/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

/** The bundled Walkthru steps in file-name order. */
export const WALKTHRU_STEPS: WalkthruStep[] = loadSteps(stepFiles);
