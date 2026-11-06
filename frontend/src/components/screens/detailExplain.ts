/**
 * Pure explanation sentences for the Detail screen cards (Slice 67G-A).
 *
 * Deterministic: fixed templates plus the numbers passed in. No clock, randomness, I/O, or
 * arithmetic in JSX. Vocabulary: run = executed, planned runs, configuration, trial (Bayesian only).
 */

export const totalExplain = (isBayesian: boolean, planned: number): string =>
  isBayesian
    ? `Planned trials: the Bayesian sampler's budget (${planned} trials), not the full grid.`
    : `Planned runs: one run per configuration in the sweep (${planned} planned).`;

export const successfulExplain = (n: number): string =>
  `Runs executed to the end with results stored: ${n}.`;

const FINISHED_WORK = 'Counted as finished work in the progress ring and ETA.';

export const failedExplain = (n: number): string =>
  `Runs executed that stopped on an error: ${n}. ${FINISHED_WORK}`;

export const interruptedExplain = (n: number): string =>
  `Runs executed that were cut short (cancel, pause or server restart): ${n}. ${FINISHED_WORK}`;

export const inProgressExplain = (n: number): string => `Runs executing right now: ${n}.`;

export const discardedExplain = (n: number): string =>
  `Trials the Bayesian sampler dropped before running: ${n}. Shown apart from Not started.`;

export const notStartedExplain = (isBayesian: boolean, n: number): string =>
  isBayesian
    ? `Planned trials minus attempted minus discarded by the sampler: ${n}.`
    : `Planned runs not executed yet: ${n}.`;

export const durationExplain = (isLive: boolean): string =>
  isLive
    ? 'Shown once the sweep has stopped; a dash while it runs or is paused.'
    : 'Time from the first run created to the last run updated; falls back to started to completed.';

export const bayesianTrialsExplain = (planned: number, gridEquivalent: number | undefined): string =>
  gridEquivalent === undefined
    ? `${planned} planned trials; the full-grid size is not recorded.`
    : `${planned} planned trials out of ${gridEquivalent} configurations in the full grid; the sampler searches chunk size × overlap and does not run the whole grid.`;

export function exploreHint(isRunning: boolean, isPaused: boolean): string | undefined {
  if (isRunning) return 'Opens Search Explorer with data stored so far; more results appear as runs finish.';
  if (isPaused) return 'Explore results from completed runs; resume to continue the sweep.';
  return undefined;
}
