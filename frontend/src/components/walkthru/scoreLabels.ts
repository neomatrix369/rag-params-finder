/**
 * Pure label helpers for the Compare / Walkthru score explanations (Slice 67D).
 *
 * Deterministic: fixed templates plus the numbers passed in. No clock, randomness, I/O, or
 * arithmetic in JSX; the components only render what these functions return.
 */

/** Shown in place of the score when a group holds one run (min-max normalisation makes it 100 by construction). */
export const LONE_RUN_LABEL = 'Only run in this group';

export function scoreCellLabel(maxScore: number, groupRunCount: number): string {
  return groupRunCount === 1 ? LONE_RUN_LABEL : maxScore.toFixed(1);
}

export const SCORE_NOTE =
  "Similarity score is the highest single-chunk similarity found in the run (the max, not the average), normalised per group to 0–100: the group's lowest run is 0 and its highest is 100. A group with one run has nothing to compare against, so it shows no score.";

/** `collapsed` is the number of duplicate rows removed; undefined when the source did not report it. */
export function dedupNote(collapsed?: number): string {
  if (collapsed === undefined) {
    return 'When a store ran the same config more than once, only the latest run is shown; earlier duplicates are collapsed.';
  }
  const noun = collapsed === 1 ? 'duplicate row was' : 'duplicate rows were';
  return `${collapsed} ${noun} collapsed: when a store ran the same config more than once, only the latest run is shown.`;
}

/** Where `rank` is counted: inside each group (live Compare) or across the whole export (Walkthru). */
export type RankScope = 'group' | 'export';

export function rankExplain(scope: RankScope): string {
  const where = scope === 'group' ? 'inside its group' : 'across the whole export';
  return `Rank is the run's position when runs are ordered by similarity score, counted ${where}; 1 is the highest score. It measures similarity only, not answer quality.`;
}

export const SCORE_COLUMN_EXPLAIN =
  'Normalised per group to 0–100: the lowest run in the group is 0 and the highest is 100. A group with one run shows "Only run in this group" instead of 100, because there is nothing to compare it with.';

export const OVERLAP_EXPLAIN =
  'A config counts as run on more than one store when the same dataset, questions and config were run on at least two stores. Only those groups show how stores differ.';

export function storyRunsExplain(runCount: number): string {
  const noun = runCount === 1 ? 'run' : 'runs';
  return `Every number here summarises ${runCount} ${noun} from the primary store only. Scores are on a 0–100 scale across this export, so the baseline is the lowest-scoring run (0), not an average.`;
}

export type StoryTile = 'best' | 'median' | 'worst' | 'spread';

const STORY_TILE_EXPLAIN: Record<StoryTile, string> = {
  best: "The highest top-chunk similarity score among this story's runs (best run = 100 after normalisation).",
  median: "The middle top-chunk similarity score among this story's runs.",
  worst: "The lowest top-chunk similarity score among this story's runs (baseline = 0 after normalisation).",
  spread: 'Best minus worst, in points on the 0–100 scale. It is a difference in points, not a percentage improvement.',
};

export function storyTileExplain(tile: StoryTile): string {
  // eslint-disable-next-line security/detect-object-injection -- tile is a closed union type
  return STORY_TILE_EXPLAIN[tile];
}

export const STORY_BASELINE_NOTE =
  'Scores are on a 0–100 scale across this export: the lowest-scoring run = 0 and the highest = 100. The spread is best minus worst in points, not a percentage. This story covers the primary store only.';
