/** Pure helpers for InfoTip (Slice 67C): accessible-name sentences and viewport clamping. */

export const VIEWPORT_MARGIN = 8;

/** Accessible name of a hint/about trigger. */
export const aboutLabel = (label: string): string => `About ${label}`;

/** Accessible name of a "how is this calculated" trigger. */
export const explainLabel = (label: string): string => `How ${label} is calculated`;

/**
 * Horizontal nudge (px) that brings a rect inside `[margin, viewportWidth - margin]`.
 * Left overflow wins when the rect is wider than the room. Returns 0 when it already fits.
 */
export function clampShift(
  rect: { left: number; right: number },
  viewportWidth: number,
  margin: number = VIEWPORT_MARGIN,
): number {
  if (rect.left < margin) return margin - rect.left;
  if (rect.right > viewportWidth - margin) return viewportWidth - margin - rect.right;
  return 0;
}
