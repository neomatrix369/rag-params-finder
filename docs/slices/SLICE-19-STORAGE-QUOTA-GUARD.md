# SLICE 19 — Atlas Storage Quota Guard

**MoSCoW:** SHOULD *(M0 free tier is 512 MB; large sweeps exhaust quota and block all MongoDB writes)*
**Target time:** ~3–5 h *(preflight + runtime handling + emergency recovery + dashboard warning; tests)*
**Status:** 📋 PLANNED — incident documented 2026-05-23; no implementation yet

---

## Goal

Treat Atlas **storage quota exhaustion** as a first-class failure mode — mirroring the existing search-index preflight pattern — so operators are warned before oversized sweeps, runs fail with clear errors mid-pipeline, and the app can recover when Atlas blocks normal cancel/update operations.

---

## Problem Statement *(2026-05-23 incident)*

On M0 (`TheSandboxCluster`), cluster storage reached **515 MB / 512 MB**. Atlas error code **8000** blocked **all writes**, including:

| Operation | Expected behavior | Actual behavior |
|-----------|-------------------|-----------------|
| Cancel running experiment | Mark `cancelled` in MongoDB | `OperationFailure` → HTTP 500 |
| Boot orphan reconciliation | Update stale `running` runs | Logged error on every server start |
| Delete **running** experiment | Cascade delete | HTTP 409 — "Cancel it first" |
| Delete **complete** experiment | Free space | Worked — freed ~17k chunks |

**Catch-22:** cancel requires a write; delete running requires cancel; quota blocks writes.

**Root causes:**

1. **Large sweep** — `example-mongodb-local.yaml` = 60 runs × ~450 chunks/run × query results on one PDF.
2. **Two experiments** on one M0 cluster (local + voyage) accumulated ~44k chunks.
3. **No storage preflight** at submit — unlike `validate_experiment_search_indexes` (HTTP 422).
4. **Measurement gap** — dashboard quota bar uses `dbStats` on `rag_params_finder` (~400 MB used) while Atlas enforces **cluster-wide** disk (~515 MB). UI showed ~112 MB "free" while writes were already blocked.
5. **No `OperationFailure` handling** — quota errors surface as generic 500s on API control endpoints.

---

## Acceptance Criteria

### Preflight (submit time)

- [ ] **`storage_preflight_plan`** pure module (parallel to `search_index_plan.py`): estimate sweep footprint from `expand_sweep(config)` + embedding dimensions + query count.
- [ ] **`validate_experiment_storage_capacity(config)`** guard (parallel to `search_index_guard.py`): compare estimate + current usage against quota with safety margin (default **85%** of limit).
- [ ] **`POST /experiments`** calls storage guard after search-index guard; reject with **HTTP 422** and human-readable estimate (runs × MB, free MB, suggested actions).
- [ ] Current usage: prefer **Atlas cluster disk metrics** when Admin API configured; fall back to `dbStats` with documented caveat.

### Runtime detection

- [ ] **`StorageQuotaExceededError`** domain exception; helper `is_storage_quota_error(exc)` for `OperationFailure` code **8000** / `"space quota"` message.
- [ ] Orchestrator: on quota error during STORING / QUERYING / results insert → mark run **FAILED** with clear `error_message`; signal in-memory cancel; stop sweep (`on_error: continue` still applies per run, but experiment should not keep embedding).
- [ ] Optional: headroom check before each run's `insert_many` (cheap guard vs wasted embed compute).

### API error mapping

- [ ] Cancel / pause / resume / delete: catch quota errors → **HTTP 507** (or **503**) with actionable `detail` (not generic 500).
- [ ] Global handler or shared wrapper for MongoDB write paths.

### Emergency recovery *(quota deadlock)*

- [ ] **`DELETE /experiments/{id}?force=true`** — allow deleting a **running** experiment without prior cancel when storage is critical (deletes free space; confirmed working near quota in incident).
- [ ] Cross-link [Slice 13](../_internal/PROGRESS.md) cleanup CLI for scheduled eviction of old **complete** experiments.
- [ ] Optional **`POST /experiments/cleanup`** — delete oldest complete experiments until usage < threshold (shares logic with Slice 13).

### Dashboard & config guardrails

- [ ] Warning banner in **VectorDbStatsPanel** when usage ≥ **80%** of quota (cluster metric when available).
- [ ] **`configs/example-mongodb-local-smoke.yaml`** — minimal M0 dev sweep (1 chunk method, 1 size, 1 retriever); keep full local example for intentional large sweeps with comment warning.

### Docs & tests

- [ ] Troubleshooting: Atlas storage quota exceeded — symptoms, catch-22, recovery steps (delete complete → force delete → Atlas UI).
- [ ] Pytest: preflight rejects oversized estimate; `is_storage_quota_error` fingerprint; force-delete bypasses running check.

---

## Design Notes

Follow the **search index preflight** layering:

```
POST /experiments
  → validate_experiment_search_indexes (existing)
  → validate_experiment_storage_capacity (new)
  → insert + schedule sweep

run_sweep / _run_single
  → optional headroom check before STORING
  → catch OperationFailure 8000 → StorageQuotaExceededError

DELETE /experiments/{id}?force=true
  → skip running-status check; cascade delete (recovery path)
```

**Storage estimate formula** (reuse `_storage_breakdown_mb` in `experiments_shared.py`):

- Per run: `avg_chunks × (dim × 4 + 500 metadata bytes)` + results × avg result size.
- Conservative default `avg_chunks` from config or historical median; document uncertainty for semantic chunking.

**Quota source priority:**

1. Atlas Metrics / cluster disk API *(if available)*.
2. `dbStats.totalSize` on app database + headroom warning that cluster may differ.
3. Manual `MONGODB_STORAGE_LIMIT_MB` override (existing).

---

## Files Likely Touched

| File | Change |
|------|--------|
| `server/core/storage_preflight_plan.py` | **NEW** — estimate + assess capacity |
| `server/core/storage_quota_guard.py` | **NEW** — validate before submit / per-run |
| `server/core/atlas_storage.py` | Cluster disk usage lookup (extend beyond limit-only) |
| `server/core/orchestrator.py` | Catch quota errors; headroom check |
| `server/api/experiments.py` | Preflight call; force delete; HTTP 507 mapping |
| `server/api/experiments_shared.py` | Shared quota error helper; export estimate fn |
| `server/main.py` | Graceful orphan reconciliation when writes blocked |
| `frontend/src/components/VectorDbStatsPanel.tsx` | ≥80% warning banner |
| `configs/example-mongodb-local-smoke.yaml` | **NEW** — M0-friendly dev config |
| `docs/user-guide/troubleshooting.md` | Storage quota section |
| `tests/test_storage_preflight.py` | **NEW** |

**Related slices:** [Slice 13](.) cleanup CLI (scheduled eviction); vector DB stats panel (existing monitoring).

---

## Key Decisions *(log in PROGRESS when slicing starts)*

| Decision | Notes |
|----------|-------|
| Safety margin 85% | Same spirit as search-index slot reservation; tunable via settings |
| Force delete vs auto-cancel | Prefer force delete — cancel needs write that may fail |
| dbStats vs Atlas metrics | Show both when possible; preflight uses conservative (max) of signals |
| HTTP 507 vs 503 | 507 Insufficient Storage for quota; document in API |

---

## Automated quality gates

```bash
bash scripts/install-git-hooks.sh
./scripts/quality-gates.sh
```

See [`development.md`](../contributor-guide/development.md) § Git hooks.

---

## Verification

```bash
# Unit tests
uv run pytest tests/test_storage_preflight.py -q

# Manual (M0 or MONGODB_STORAGE_LIMIT_MB=512 override)
# 1. Fill cluster near limit
# 2. Submit oversized config → expect 422 with estimate
# 3. Trigger quota during sweep → runs fail with clear error_message
# 4. Cancel fails with 507 → force delete frees space → cancel/delete work again

./scripts/quality-gates.sh
# or during development: ./scripts/quality-gates.sh --quick
```
