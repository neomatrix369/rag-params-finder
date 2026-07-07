# Slice 30 — Search Explorer UX Fixes

**Status**: 📋 PLANNED
**Branch**: `slice/30-search-explorer-ux`
**Estimated time**: ~2 h
**MoSCoW**: Could (UX polish — does not block any PCTO requirement)

## Problem

Four UX issues found during live app assessment (2026-07-07):

1. **Tab switch latency**: Clicking between "Hyperparameters" and "Detailed Results" tabs in `SearchExplorerScreen` takes >5 seconds to settle. Root cause: the 2-second polling timer fires during the click handler cycle, triggering a full re-render of heavy memoized state chains. No `useTransition` / `useDeferredValue` to defer the non-urgent re-render.
2. **Zero-score noise**: BM25 queries return some results with score 0 (rank #3, score 0, displayed as 0%). These are noise — not relevant — but display identically to scored results, only the raw number distinguishes them.
3. **Score unit ambiguity**: Dense cosine similarity scores (normalised 0–100%) and BM25 raw keyword scores (raw integer, can exceed 100) are displayed in the same badge format. Users can't tell which method produced which type of number.
4. **VDB card discoverability**: The Vector Database Stats card in `ExperimentDetailScreen` is collapsed by default. Users must discover it manually after a completed experiment.

## Goal

Fix the four issues without changing any API contract or data model — pure frontend changes.

## Acceptance Criteria

### Tab switch latency (Must for this slice)
- [ ] Clicking "Detailed Results" or "Hyperparameters" tab updates the active tab indicator within 200 ms
- [ ] Full tab content is displayed within 1 second of clicking

### Zero-score result de-emphasis (Must for this slice)
- [ ] Results with `nn_normalized_score === 0` appear visually de-emphasised (dimmed) in the Detailed Results tab
- [ ] A "(no match)" label replaces the "0%" score badge for zero-score rows
- [ ] Non-zero results are unaffected

### Score unit hint (Must for this slice)
- [ ] Score badges show a retrieval-method label: "similarity" for dense/reranker, "keyword score" for sparse/BM25
- [ ] Label is derived from `retrieval_method` field on each result row (no new API calls)

### VDB card default-expanded (Should for this slice)
- [ ] The Vector Database Stats collapsible card in `ExperimentDetailScreen` is open by default
- [ ] `localStorage` persistence still works: if user manually collapses it, state is remembered across refreshes

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/components/SearchExplorerScreen.tsx` | `useTransition` for tab switch; zero-score de-emphasis; score unit label |
| `frontend/src/components/ExperimentDetailScreen.tsx` | VDB card default-expanded |

## GWT Scenarios (tests — component/integration)

```
Scenario: tab switch does not freeze the UI
  Given SearchExplorer is loaded with results
  When user clicks "Detailed Results" tab
  Then the active tab indicator updates within 200 ms (pending transition visible)
  And full content renders within 1000 ms

Scenario: zero-score results are visually de-emphasised
  Given Detailed Results includes a result with nn_normalized_score = 0
  Then that result row has reduced opacity
  And its score badge shows "(no match)" not "0%"

Scenario: dense result shows "similarity" label
  Given a result row with retrieval_method = "dense"
  Then its score badge reads "<N>% similarity"

Scenario: sparse result shows "keyword score" label
  Given a result row with retrieval_method = "sparse"
  Then its score badge reads "<N> keyword score"

Scenario: VDB card is open by default
  Given ExperimentDetailScreen loads with a completed experiment
  When no prior localStorage state exists for that card
  Then the Vector Database Stats collapsible is expanded on first load
```

## Before-Checks

- [ ] `npm run typecheck` passes on main
- [ ] `npm run build` passes on main
- [ ] Branch `slice/30-search-explorer-ux` created from latest main

## After-Checks

- [ ] `./scripts/quality-gates.sh` pass (especially `npm run typecheck` + `npm run build`)
- [ ] Specification coverage: every GWT scenario has a corresponding test or manual verification step
- [ ] Branch coverage: 100% target for any new utility functions; exclusions documented (test-writing-craft-quality.mdc §12)
- [ ] Mutation testing: survival budget met if slice is feature-complete (§23)
- [ ] Manual: open SearchExplorer → click tabs → confirm ≤500 ms visual response
- [ ] Manual: run sparse sweep → confirm 0-score rows are visually de-emphasised
- [ ] Manual: open ExperimentDetail → VDB stats card is expanded by default

## Commits

```
fix(slice-30): fix Search Explorer tab switch latency (active indicator ≤200 ms, content ≤1 s)
feat(slice-30): de-emphasise zero-score results + add retrieval-method score labels
fix(slice-30): default VDB stats card to expanded in experiment detail
```
