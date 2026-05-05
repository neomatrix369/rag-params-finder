# SLICE 04 — Live Status + Polling

**MoSCoW:** MUST  
**Target time:** ~30 min  
**Actual time:** ~15 min  
**Status:** ✅ COMPLETE (2026-05-02)

---

## Goal

Real-time phase tracking: CLI shows a live table while runs progress, and the React dashboard has a drill-down detail screen with phase indicator dots that update every 2 seconds.

---

## Acceptance Criteria

- [x] CLI `--watch` flag (default on) shows a Rich Live table polling every 2 s
- [x] Phase transitions tracked in `run_status` collection (QUEUED → PARSING → CHUNKING → EMBEDDING → STORING → QUERYING → RERANKING → COMPLETE)
- [x] `elapsed_ms` tracked per run
- [x] Dashboard `ExperimentDetailScreen` shows phase indicator dots (past=green, current=blue pulsing, future=gray, failed=red)
- [x] Clicking an experiment row in ExperimentsScreen opens the detail screen
- [x] Detail screen stops polling when experiment reaches a terminal status (complete/failed/partial/cancelled)

---

## Files Changed

| File | Change |
|---|---|
| `cli/main.py` | **EDIT** Added `--watch` flag; Rich Live table polls every 2 s |
| `cli/api_client.py` | **EDIT** Added `get_experiment()`, `get_run_status()` |
| `server/core/orchestrator.py` | **EDIT** `elapsed_ms` tracking; `experiment_id` passed from API layer |
| `server/api/experiments.py` | **EDIT** `experiment_id` created in handler, returned in POST response |
| `server/api/runs.py` | **NEW** `GET /runs/{run_id}/status` |
| `frontend/src/components/ExperimentDetailScreen.tsx` | **NEW** Phase indicator dots, run table, 2 s polling |
| `frontend/src/App.tsx` | **EDIT** State-based routing (list ↔ detail) |
| `frontend/src/components/ExperimentsScreen.tsx` | **EDIT** Clickable rows via `onSelect` prop |

---

## Key Decisions

| Decision | Why |
|---|---|
| Rich Live table in CLI | Real-time phase display without clearing terminal; scroll-safe |
| `experiment_id` created in API handler | Returned immediately so CLI can poll before background task starts |
| Phase indicator dots not a progress bar | Visual clarity across 8 phases without crowding the UI |
| State-based routing (no react-router) | Two screens only — router dependency not worth it |

---

## Exit Criteria

- CLI `rag-params-finder run --config configs/example-local.yaml` shows live phase updates
- Dashboard detail screen shows phase dots advancing in real time
- All 8 phases (QUEUED through COMPLETE) appear correctly coloured
