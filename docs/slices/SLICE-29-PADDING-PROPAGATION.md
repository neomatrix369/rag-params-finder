# Slice 29 — Padding Parameter Cross-Cutting Propagation

**Status**: ✅ COMPLETE
**Estimated time**: ~2 h
**MoSCoW**: Must (backend bug + types) · Must (ExperimentDetailScreen) · Should (SearchExplorerScreen) · Could (help-text labels)
**Flow**: Brownfield — propagation gap in mature feature (PR #48 padding sweep dimension)
**Execution order**: **29** after 22; before 26 → 27 → 19 → 16 → 11 → 23 → 10

## Slice workflow

**Slice name:** `slice-29-padding-propagation`

**Outcome:** Multi-padding sweeps display distinct ranked configs; `padding` visible in all UI locations alongside `chunk_size`/`overlap`.

**Files:**
- `server/core/results_analyzer.py` — bug fix + padding in response dicts
- `server/api/experiments.py` — padding in sweep_summary
- `tests/test_tiebreaker_ranking.py` — fixture updates + new distinct-by-padding test
- `frontend/src/types/index.ts` — four interfaces updated
- `frontend/src/components/ExperimentDetailScreen.tsx` — sweep badges + runs table
- `frontend/src/components/SearchExplorerScreen.tsx` — all display locations
- `docs/slices/PROGRESS.md` — Slice 29 row + decision log entry

**Exit criteria:**
- [x] `_run_config_key()` includes padding — multi-padding sweeps show distinct ranked configs
- [x] `uv run pytest tests/ -q` passes with no regressions
- [x] `npm run typecheck && npm run build` pass
- [x] `./scripts/quality-gates.sh` green
- [x] ExperimentDetailScreen shows padding in sweep-dimensions badges and runs table
- [x] SearchExplorerScreen shows padding in best-params card and ranked-configs table

**Commit pattern:**
```
fix(results): include padding in config key and response dicts

Runs differing only by padding were silently merged into one ranked
config. Propagates padding through results_analyzer, API responses,
TypeScript types, and all UI display locations (mirrors chunk_size/overlap).
```

**Skills:** `/tdd` · `/slice-workflow` · `/clean-commit` · `/verify-slice`

## Branch

`slice/29-padding-propagation`

---

## Problem

PR #48 added `padding` as a swept chunking dimension (like `chunk_size` and `overlap`).
Core pipeline integration is complete — `RunParams.padding`, `RunStatus.padding`, sweep expansion,
and chunker pipeline all carry the value.

However propagation stopped there:

1. **Correctness bug**: `_run_config_key()` in `results_analyzer.py` builds the config identity
   tuple from `(chunk_size, overlap, embedding_model, retrieval_method)`. `padding` is absent, so
   two runs that differ only by padding value map to the same key — they are merged into one ranked
   config in the Search Explorer. Users see a single result entry instead of two distinct configs.

2. **API gap**: `RankedConfig` and `DetailedResult` dicts constructed in `results_analyzer.py` don't
   include `padding`, so the `/explore` endpoint response never carries it.

3. **Frontend gap**: Four TypeScript interfaces (`SweepSummary`, `RunStatus`, `RankedConfig`,
   `DetailedResult`) are missing the `padding` field. All UI locations that display
   `chunk_size`/`overlap` omit padding.

## Goal

Propagate `padding` uniformly through every layer that already carries `chunk_size` and `overlap`,
so the field is:
- Correctly key'd in ranked config identity (bug fix)
- Returned in all API responses that power the Search Explorer
- Typed correctly in the frontend
- Visible in ExperimentDetailScreen (sweep badges + runs table)
- Visible in SearchExplorerScreen (best-params card, ranked-configs table, detailed results)

Old experiments without padding data are handled gracefully (default 0, no visual noise).

## Why this slice (impact)

| Stakeholder | Impact |
|-------------|--------|
| Sweep operators | Cannot distinguish padding variants in Search Explorer today |
| Result correctness | Multi-padding sweeps silently merge distinct configurations |
| UI completeness | Runs table shows Size/Overlap but not Padding |

## Design

### Backend: `server/core/results_analyzer.py`

**Bug fix** — `_run_config_key()`: add `padding` to the identity tuple:
```python
# before
return (chunk_size, overlap, embedding_model, retrieval_method)
# after
return (chunk_size, overlap, padding, embedding_model, retrieval_method)
```

**Response dicts**: add `"padding": run.get("padding", 0)` to both `detailed` and `ranked_configs`
dict construction blocks.

### Backend: `server/api/experiments.py`

`sweep_summary` dict (returned on experiment creation): add
`"paddings": config.chunking.params.paddings`.

### Frontend types: `frontend/src/types/index.ts`

Add to four interfaces (all optional for backward compat):
- `SweepSummary.paddings?: number[]`
- `RunStatus.padding?: number`
- `RankedConfig.padding?: number`
- `DetailedResult.padding?: number`

### Frontend: `ExperimentDetailScreen`

Three locations mirror the `chunk_size`/`overlap` pattern:
- Sweep dimensions badges: add Paddings badge
- Runs table "Size/Overlap" column → extend to include padding (e.g. `512/50/0`)
- Failed/interrupted inline display: extend same format

### Frontend: `SearchExplorerScreen`

Nine locations mirror the `chunk_size`/`overlap` pattern:
- Best params card: add Padding row
- Config card display: extend to include padding
- Unique dimensions: add `uniquePaddings` extraction
- Cartesian product text: include padding dimension
- Tiebreaker ranking logic: add `padding` to comparison chain
- Config key string: include padding
- Ranked configs table cell: extend display
- Detailed results display: extend display
- Help/label text: mention padding in dimension descriptions

## Acceptance Criteria

### Backend (Must)

- [ ] `_run_config_key()` includes `padding` — two runs differing only by padding produce two distinct entries in `ranked_configs`
- [ ] `GET /experiments/{id}/explore` `RankedConfig` and `DetailedResult` objects include `padding` field
- [ ] `GET /experiments` (create response) `sweep_summary` includes `paddings` list
- [ ] `test_tiebreaker_ranking.py` fixtures updated; new test: two runs identical except padding → two distinct ranked configs
- [ ] `uv run pytest tests/ -q` passes with no regressions

### Frontend (Must)

- [ ] All four TypeScript interfaces include `padding` / `paddings` field (optional for backward compat)
- [ ] `npm run typecheck && npm run build` pass with zero errors

### UI — ExperimentDetailScreen (Must)

- [ ] Sweep dimensions panel shows Paddings badge alongside Chunk Sizes / Overlaps
- [ ] Runs table shows padding per run (e.g. `512/50/0`)
- [ ] Padding = 0 displays cleanly for legacy experiments (no visual noise)

### UI — SearchExplorerScreen (Should)

- [ ] Best params card shows Padding row
- [ ] Ranked configs table includes padding in config cell
- [ ] Detailed results table includes padding
- [ ] Config keys correctly distinguish entries that differ only by padding

### Quality (Must)

- [ ] `./scripts/quality-gates.sh` green end-to-end

## Files

| File | Change |
|------|--------|
| `server/core/results_analyzer.py` | **EDIT** — `_run_config_key()` + two dict construction blocks |
| `server/api/experiments.py` | **EDIT** — `sweep_summary` dict add `paddings` |
| `tests/test_tiebreaker_ranking.py` | **EDIT** — update fixtures + add distinct-by-padding test |
| `frontend/src/types/index.ts` | **EDIT** — add `padding`/`paddings` to four interfaces |
| `frontend/src/components/ExperimentDetailScreen.tsx` | **EDIT** — sweep badges + runs table (3 locations) |
| `frontend/src/components/SearchExplorerScreen.tsx` | **EDIT** — all display locations (9 locations) |
| `docs/slices/PROGRESS.md` | **EDIT** — Slice 29 row + decision log entry |

## GWT Scenarios (tests)

```
Scenario: padding distinguishes ranked configs
  Given experiment e1 has two runs identical except padding=0 vs padding=50
  When  GET /experiments/e1/explore
  Then  ranked_configs contains two distinct entries with different padding values

Scenario: padding included in explore response
  Given experiment e1 has completed runs with padding=50
  When  GET /experiments/e1/explore
  Then  each RankedConfig and DetailedResult has padding=50

Scenario: padding zero displays without noise (UI)
  Given experiment e1 ran with default padding=0
  When  user views ExperimentDetailScreen
  Then  runs table shows "512/50/0" or equivalent clean display
```

## Before-checks

- [x] PR #48 (padding sweep dimension) merged to main — 2026-07-05
- [x] PR #47 (semantic chunker overlap fix) merged to main — 2026-07-05
- [x] `./scripts/quality-gates.sh` green on `main`
- [x] Branch `slice/29-padding-propagation` from latest `main`

## After-checks

- [x] `./scripts/quality-gates.sh` pass (100 tests, 11/11 gates green)
- [x] API smoke: `tests/test_padding_propagation_api.py` — explore returns 2 ranked configs (padding 0 vs 50); detail returns `sweep_summary.paddings` + per-run `padding`
- [x] Analyzer smoke: `test_padding_distinguishes_ranked_configs` + full `test_padding.py` suite (10 tests)
- [ ] Live UI smoke (manual): server not stable in this session (uvicorn exit 137 after boot) — run locally with `./start-services.sh --local`, config `/tmp/smoke-slice29-padding.yaml`, then verify Search Explorer + ExperimentDetail runs table

## Out of scope

- ExperimentsScreen list-level display (padding is per-run, not per-experiment summary)
- Config form / YAML editor changes
- CLI output changes
