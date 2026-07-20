# Slice 11 — Search Explorer Enhancements (Visualization + Query Filtering)

**Status**: 📋 PLANNED
**Branch**: `slice/11-search-explorer`
**MoSCoW**: Could
**Depends on**: none *(soft: Slice **30** UX baseline recommended — see execution order)*
**Estimated time**: ~30–45 min
**Execution order**: After **30** (UX fixes) and **31** (list filter); see [`TRAIL.md`](../plan/TRAIL.md)

## Scope boundary

| In scope (Slice 11) | Out of scope (other slices) |
|---------------------|----------------------------|
| Hyperparameter / results **visualization** in Search Explorer | Export CSV/JSONL → **Slice 28** (#49, @cschanhniem) |
| **Query filtering** (persona, focus, text) in Search Explorer | Tab latency, score badges, VDB card → **Slice 30** |
| Ranked-config comparison views using existing `/explore` data | Dashboard-triggered runs (not in active plan) |

## Problem

Search Explorer loads analyzed sweep results via `GET /experiments/{id}/explore` but lacks:

1. **Visualization** — operators cannot quickly compare configs (e.g. bar/radar of top metrics across chunking/retrieval combos).
2. **Query filtering** — large persona JSON sweeps show all queries at once; no filter by persona, focus tag, or query substring.

Export was split to Slice 28; UX polish to Slice 30 — this slice completes the original “enhancements” bundle minus those items.

## Goal

Add visualization and query-filter controls to `SearchExplorerScreen` without new backend endpoints — compose on `analyze_results()` output already returned by `/explore`.

## Acceptance Criteria

### Visualization (Should)
- [ ] At least one chart compares top-N configs by primary ranking metric (same metric as Search Explorer table default)
- [ ] Chart updates when user changes experiment or active query filter
- [ ] Empty / single-config experiments degrade gracefully (message, not broken layout)

### Query filtering (Must for this slice)
- [ ] Filter by **persona** when multiple personas exist in results
- [ ] Filter by **focus** tag when present on query rows
- [ ] Free-text filter matches query text (case-insensitive substring)
- [ ] Filters compose (persona + focus + text); clearing filters restores full set

### Quality
- [ ] `./scripts/quality-gates.sh --quick` pass
- [ ] No regression in existing Search Explorer tab navigation (Slice 30 owns latency ACs)

## Before-Checks [GATE]

- [ ] `./scripts/quality-gates.sh --quick` green on `main`
- [ ] Branch `slice/11-search-explorer` from latest `main`
- [ ] Slice **30** merged or explicitly waived if visualization depends on UX baseline from 30

## After-Checks

- [ ] `./scripts/quality-gates.sh` pass
- [ ] Manual: completed experiment → Search Explorer → apply filters → chart reflects subset
- [ ] `docs/user-guide/dashboard-guide.md` updated (visualization + filter controls)
- [ ] Specification coverage: every GWT clause has ≥1 test where applicable (frontend: component/integration)
- [ ] Branch coverage: 100% target on new TS modules; exclusions documented if any
- [ ] Mutation testing: run for new/changed frontend modules (or document explicit feature-complete waiver)

## Files (expected)

- `frontend/src/components/SearchExplorerScreen.tsx` — filter state + chart region
- `frontend/src/components/SearchExplorerChart.tsx` — new (or Tremor chart primitive if already in stack)
- `frontend/src/types/index.ts` — filter types if needed
- `tests/` or `frontend` vitest — filter + empty-state tests

## Relation to other slices

- **Slice 28**: export only; no overlap
- **Slice 30**: UX fixes (latency, zero-score, labels) — land 30 first if tab performance blocks chart work

**Latency coordination**: Slice 30 establishes tab-switching baseline (<200ms). Slice 11 must not regress this baseline. If chart render adds >50ms to tab latency, treat as a Slice 11 blocker — request Slice 30 review before merge. Slice 30 may adjust the baseline or suggest Slice 11 optimizations (lazy render, memoized filters).

- **Slice 23**: Tier 2–3 retrieval methods may add new result shapes — filters must not assume single retrieval type
