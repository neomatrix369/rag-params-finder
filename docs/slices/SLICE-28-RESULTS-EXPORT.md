# Slice 28 — Experiment Results Export (CSV / JSONL)

**Status**: 📋 PLANNED *(external contributor — not core-team active queue)*
**Owner**: [@cschanhniem](https://github.com/cschanhniem) — [issue #49](https://github.com/neomatrix369/rag-params-finder/issues/49) author and assignee
**GitHub**: [Issue #49](https://github.com/neomatrix369/rag-params-finder/issues/49)
**Estimated time**: ~1.5 h
**MoSCoW**: Must (backend export) · Should (dashboard download) · Could (JSONL) · Won't (CLI, Excel, auth)
**Flow**: Brownfield — small requirement on mature API (`/explore` + `results_analyzer.py`)
**Execution order**: **32 → 33 → 34 → 35 → 36 → 37 → 38 → 22 → 28***(external)* → 31 → 30 → 16 → 11 → 23 → 10 *(26, 27, 19 deferred — see TRAIL)*

## Slice workflow

**Outcome:** downloadable CSV/JSONL of analyzed sweep results (scores match Search Explorer)

**Files:**
- `server/core/results_export.py` — pure export formatting (composable with `analyze_results`)
- `server/api/experiments.py` — `GET /{id}/export` route
- `tests/test_results_export.py` — endpoint + row parity with `/explore`
- `frontend/src/components/ExperimentDetailScreen.tsx` — Export CSV button
- `frontend/src/services/apiClient.ts` — download helper

**Exit criteria:**
- [ ] pytest export tests pass
- [ ] `./scripts/quality-gates.sh --quick` pass
- [ ] Manual CSV download verified
- [ ] `docs/user-guide/dashboard-guide.md` updated

**Commit pattern:**
```
feat(export): add experiment results CSV download endpoint

Enables portable sharing of normalized sweep scores (issue #49).
Reuses analyze_results so export matches Search Explorer.
```

**Skills:** `/tdd` · `/slice-workflow` · `/clean-commit` · `/verify-slice` · close with comment on #49

---

## Problem

Teams running parameter sweeps can view ranked results in Search Explorer (`GET /experiments/{id}/explore`), but cannot download them for spreadsheets, notebooks, or stakeholder sharing. [Issue #49](https://github.com/neomatrix369/rag-params-finder/issues/49) requests a portable export path reusing `mongo_list_results_for_experiment` + `analyze_results` normalization.

## Issue #49 traceability

| Issue requirement | Slice 28 coverage |
|-------------------|-------------------|
| Export endpoint CSV or JSONL | Must — `format=csv\|jsonl` (default csv) |
| Reuse `mongo_list_results_for_experiment` + `analyze_results` | Must — same load path as `/explore` (`mongo_load_explore_source`) |
| Streaming CSV response | Must — `StreamingResponse` |
| Query params: `format`, `query_text`, `top_k` | Must — `top_k` = top K rows **per config** (issue wording) |
| CSV columns per issue example | Must — see below (`score` = raw, `nn_normalized_score` = 0–100) |
| Frontend **Export CSV** on `ExperimentDetailScreen` | Should |
| Path `/api/experiments/{id}/export` in issue | **Adapted** — repo mounts experiments at `/experiments/{id}/export` (no `/api` prefix; matches `/explore`, `/results`) |
| Issue sketch iterates `analyzed["configs"]` | **Corrected** — rows from `detailed_results` (per-chunk, matches issue CSV example) |
| `/explore` uses `query` param | Export accepts `query_text` per issue; optionally alias `query` for parity |


## Goal

Add `GET /experiments/{experiment_id}/export` returning **streaming CSV** (default) or **JSON Lines**, built from `analyze_results()` output — same scores and ranks as the dashboard explorer. Add an **Export CSV** button on the experiment detail screen.

## Why this slice (impact)

| Stakeholder | Value |
|-------------|-------|
| Sweep operators | Share findings without MongoDB or dashboard access |
| Analysis workflows | Import into pandas / Sheets / BI tools |
| Hackathon demo | Shows production-minded “results leave the system” UX |

## Design

### Endpoint

```
GET /experiments/{experiment_id}/export
  ?format=csv|jsonl     (default: csv)
  &query_text=<string>  (optional — same filter as /explore)
  &top_k=<int>          (optional — top K results per config; omit = all)
```

**404** when experiment missing. **422** when `format` invalid.

### Row source

Compose rows from `analyze_results()` → `detailed_results` (already has `rank`, normalized `score`, config fields, `query_text`, `run_id`). Add `experiment_id` column. Do **not** duplicate normalization logic in the route handler — extract a small formatter module.

### CSV columns (Must — matches issue #49)

```
experiment_id,run_id,query_text,chunking_method,chunk_size,overlap,embedding_model,
retrieval_method,score,nn_normalized_score,rank
```

- `score` — raw retrieval score (e.g. `0.89`; rerank or dense from `_effective_score`)
- `nn_normalized_score` — min-max normalized 0–100 (same as Search Explorer `detailed_results[].score`)

Example row (from issue):

```csv
abc123,run-1,"What is ML?",semantic,512,50,all-MiniLM-L6-v2,dense,0.89,78,1
```

Omit `chunk_text` from default CSV (size); include in JSONL only.

### Response headers

- CSV: `Content-Type: text/csv`, `Content-Disposition: attachment; filename="{experiment_id}-results.csv"`
- JSONL: `application/x-ndjson`, same disposition pattern with `.jsonl`

### Frontend (Should)

`ExperimentDetailScreen` — **Export CSV** button in page actions (alongside Explore). Triggers download via `fetch` + blob; disabled when experiment has zero stored results.

## Acceptance Criteria

### Backend (Must)

- [ ] `GET /experiments/{id}/export?format=csv` returns valid CSV with header row + one row per detailed result
- [ ] Normalized scores match `GET /experiments/{id}/explore` for the same `query_text` filter
- [ ] `query_text` filter works; omitted returns all queries
- [ ] `top_k` limits to top K results **per config** (issue #49 semantics)
- [ ] Unknown experiment → 404
- [ ] Invalid `format` → 422
- [ ] pytest covers: happy path CSV, query filter, 404, format validation

### Frontend (Should)

- [ ] Export CSV button on experiment detail downloads `{id}-results.csv`
- [ ] Button shows error toast on failure; disabled when `total_results === 0`

### Docs (Must)

- [ ] `docs/user-guide/dashboard-guide.md` — Export section (1 paragraph + screenshot optional)
- [ ] OpenAPI reflects new route (auto via FastAPI)

## Files

| File | Change |
|------|--------|
| `server/core/results_export.py` | **NEW** — `build_export_rows()`, `stream_csv()`, `stream_jsonl()` from analyzed payload |
| `server/api/experiments.py` | **EDIT** — `export_experiment_results` route |
| `tests/test_results_export.py` | **NEW** — GWT tests (mock mongo + analyzer) |
| `frontend/src/services/apiClient.ts` | **EDIT** — `downloadExperimentExport()` |
| `frontend/src/components/ExperimentDetailScreen.tsx` | **EDIT** — Export CSV button |
| `docs/slices/PROGRESS.md` | Slice 28 row + decision log |

## GWT Scenarios (tests)

```
Scenario: export CSV for completed experiment
  Given experiment e1 has stored query results
  When  GET /experiments/e1/export?format=csv
  Then  response is text/csv with attachment disposition
  And   first data row scores match GET /experiments/e1/explore detailed_results

Scenario: filter export by query
  Given experiment e1 has results for queries Q1 and Q2
  When  GET /experiments/e1/export?query_text=Q1
  Then  every CSV row has query_text=Q1

Scenario: export missing experiment
  When  GET /experiments/nope/export
  Then  404

Scenario: dashboard download
  Given user is on experiment detail for e1 with results
  When  user clicks Export CSV
  Then  browser saves e1-results.csv
```

## Before-checks

- [x] Merge PRs #47 (semantic chunker overlap) and #48 (padding sweep dimension) — merged to `main` 2026-07-05 (#60/#61 review follow-ups included)
- [ ] `./scripts/quality-gates.sh --quick` green on `main`
- [ ] Branch `slice/28-results-export` from latest `main` *(contributor-owned — @cschanhniem per issue #49)*

## After-checks

- [ ] `./scripts/quality-gates.sh` pass
- [ ] Specification coverage: every GWT clause has ≥1 test; essential error paths covered (90–100% of clauses)
- [ ] Branch coverage: 100% target; exclusions documented (test-writing-craft-quality.mdc §12)
- [ ] Mutation testing: survival budget met if slice is feature-complete (§23)
- [ ] Manual: run local experiment → Export CSV → open in spreadsheet
- [ ] Close or comment on GitHub #49 with PR link

## Out of scope (Won't / defer)

- CLI `rag-params-finder export` (Could — separate slice if needed)
- Excel `.xlsx` format
- Export auth / signed URLs
- Slice 11 remaining items (visualization, query filtering UX) — stay in Slice 11

## Relation to Slice 11

Slice 11 (*Search Explorer enhancements*) listed “export results” as one of several items. **Slice 28** implements export only (issue #49) as a shippable vertical slice; Slice 11 scope shrinks to visualization + filtering.
