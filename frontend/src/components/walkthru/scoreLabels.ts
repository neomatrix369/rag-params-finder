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

export const STORY_BASELINE_NOTE =
  'Scores are on a 0–100 scale across this export: the lowest-scoring run = 0 and the highest = 100. The spread is best minus worst in points, not a percentage. This story covers the primary store only.';
