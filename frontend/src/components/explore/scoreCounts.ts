/**
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67D - pure score counts for the Explorer (no clock, I/O or DOM).
 */
/** How many of the given configurations share exactly this max score (the "tied at #1" count). */
export function countConfigsAtScore(configs: ReadonlyArray<{ max_score: number }>, score: number): number {
  return configs.filter((config) => config.max_score === score).length;
}
