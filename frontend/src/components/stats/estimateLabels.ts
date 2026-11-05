/**
 * Pure label helpers for the stats estimate and scope text (Slice 67D).
 *
 * Deterministic: fixed templates plus the numbers passed in. No clock, randomness, I/O, or
 * arithmetic in JSX. Constants mirror `server/db/ports/stats_common.py` (float32, 500 B metadata).
 */

export const BYTES_PER_DIMENSION = 4;
export const METADATA_BYTES_PER_CHUNK = 500;

export function estimateFormula(): string {
  return `chunks × average dimensions × ${BYTES_PER_DIMENSION} bytes (vectors) + chunks × ${METADATA_BYTES_PER_CHUNK} bytes (metadata); an estimate, not measured on disk.`;
}

export function estimatedMbLabel(mb: number): string {
  return `est. ${mb} MB`;
}

export const FOOTPRINT_SCOPE = 'Scope: this experiment only, as currently stored.';

export const STATS_SCOPE =
  'Scope: all experiments stored in this database. Tiles that this backend does not report show —.';
