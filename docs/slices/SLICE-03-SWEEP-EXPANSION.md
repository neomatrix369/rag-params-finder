# SLICE 03 — Sweep Expansion

**MoSCoW:** MUST ⭐ (core feature)
**Target time:** ~25 min
**Actual time:** ~15 min
**Status:** ✅ COMPLETE (2026-05-02)

---

## Goal

Cartesian product expansion: one YAML config with N models × M chunking methods × P chunk sizes × Q overlaps × R retrieval methods → N×M×P×Q×R independent runs executing sequentially.

---

## Acceptance Criteria

- [x] `expand_sweep()` generates the full Cartesian product of run parameters from a single config
- [x] Each run executes independently with its own `run_id`
- [x] `run_count` and `failed_count` reported in experiment response
- [x] `on_error: continue` allows partial completion; `on_error: stop` halts on first failure
- [x] `partial` experiment status distinguishes mixed outcomes from `complete` or `failed`
- [x] Example config uses 3 chunk sizes × 2 overlaps = 6 runs

---

## Files Changed

| File | Change |
|---|---|
| `server/models/config.py` | **NEW** `RunParams` model + `expand_sweep()` pure function |
| `server/api/runs.py` | **NEW** `GET /runs/{run_id}/status` endpoint |
| `server/api/__init__.py` | **NEW** package init |
| `server/core/orchestrator.py` | **REWRITE** split into `run_sweep()` + `run_single(run_params)` |
| `server/api/experiments.py` | **REWRITE** shows `run_count` in POST response; adds `GET /experiments/{id}/results` |
| `server/main.py` | **EDIT** register `/runs` router |
| `configs/example.yaml` | **EDIT** multi-value sweep (3 chunk_sizes × 2 overlaps) |
| `frontend/src/types/index.ts` | **EDIT** `run_count`, `failed_count` fields on `Experiment` |
| `frontend/src/components/ExperimentsScreen.tsx` | **EDIT** Runs column + partial status badge |

---

## Key Decisions

| Decision | Why |
|---|---|
| `expand_sweep()` as pure function | Testable without side effects; called in both API (preview count) and orchestrator (execute) |
| Sequential runs (`parallelism` ignored at runtime until Slice 16) | `parallelism` is persisted for audit/UI; honoring `parallelism > 1` → [SLICE-16-PARALLEL-SWEEP-RUNS.md](./SLICE-16-PARALLEL-SWEEP-RUNS.md) |
| `run_sweep()` + `run_single()` split | Single Responsibility — sweep management vs pipeline execution |
| `partial` status | Distinguishes "some runs failed" from "all failed" or "all succeeded" |

---

## Exit Criteria

- POST experiment with 3 chunk_sizes × 2 overlaps → exactly 6 run_ids in response
- All 6 runs reach COMPLETE (or FAILED with `on_error: continue`)
- Dashboard ExperimentsScreen shows run count per experiment
