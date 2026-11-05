/**
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67 — the exact regexes the determinism guard applies, shared with its positive control.
 */

/** Pure modules must not read a clock (no-argument Date), randomness, storage, network or DOM. */
export const NON_DETERMINISTIC =
  /\b(Date\.now|new Date\(\s*\)|Math\.random|performance\.now|fetch\(|localStorage|sessionStorage|window\.|document\.)/;

/** Screens must render counts produced elsewhere, never compute them inline. */
export const JSX_COUNT_ARITHMETIC =
  /\.length\s*[*×]|[*×]\s*[\w.?]+\.length\b|\.filter\([^\n]*\)\.length|\/\s*[\w.?]+\)?\s*\*\s*100/;
