/**
 * Pure storage-usage helper for the vector-database stats panel (Slice 67E, guard cleanup).
 * Deterministic: depends only on its arguments.
 */
export function usagePercent(used: number | null | undefined, limit: number | null | undefined): number | null {
  if (used == null || limit == null || limit <= 0) return null;
  return Math.min(100, Math.round((used / limit) * 100));
}
