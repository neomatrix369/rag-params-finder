# SLICE 36 — Postgres Index Preflight + DB Stats + Storage Mode

**MoSCoW:** MUST
**Target time:** ~3–4 h
**Status:** 📋 PLANNED
**Depends on:** 35
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../PRD-supabase-pgvector-migration.md)

> Absorbs deferred Slice 27 (Mongo cloud vs local indicator) into a **four-value** `storage_mode` that mirrors the operator flag vocabulary from Slice 37.

---

## Slice Workflow Bundle

- Slice name: `slice-36-postgres-preflight-stats`
- Branch: `slice/36-postgres-preflight-stats`
- Files (expected):
  - `server/core/search_index_plan.py` — backend-agnostic required-index plan
  - `server/core/search_index_guard.py` or `postgres_index_guard.py` — Postgres introspection (replace Atlas-only short-circuit with real verify)
  - `server/db/postgres_stats.py` — **extend/verify** (partially shipped in Slice 33; not create from scratch; was incorrectly named `postgres_storage.py` in earlier drafts)
  - `server/db/postgres_uri.py` — rename `postgres_storage_mode()` return values to flag-aligned taxonomy
  - `server/db/mongodb_uri.py` — `get_mongodb_mode()` (or equivalent) for mongo local/cloud
  - `cli/indexes_cmd.py` — list/reset for Postgres backend
  - `server/core/health_check.py` / `/healthz` — surface `storage_mode`
  - Dashboard header badge / sweep_summary field
  - `tests/test_postgres_index_guard.py`, `tests/test_storage_mode.py`
- Exit criteria: Missing/wrong indexes → HTTP 422; db-stats panels work; indexes CLI useful; four-value storage mode visible and named after flags
- Commit pattern: `feat(slice-36): postgres index preflight db stats and storage mode`

---

## Goal

Postgres equivalents of search-index preflight and vector DB stats, plus a **storage-mode indicator** — absorbing deferred Slice 27 — using the same vocabulary as `start-services.sh` flags:

| `storage_mode` | Meaning |
|---|---|
| `mongodb-local` | Atlas Local Docker / no TLS |
| `mongodb-cloud` | Atlas cloud / TLS |
| `postgres-local` | Docker pgvector / no TLS |
| `postgres-cloud` | Hosted Supabase / TLS |

An operator who sees `postgres-cloud` on the badge knows the exact flag that produced it. Today `postgres_storage_mode()` returns `local-postgres` / `supabase` — this slice renames those values and adds the Mongo pair (four values total; do not collapse both Mongo flavours into `mongo`).

**Cross-cutting invariant:** `storage_mode` values === CLI flag compounds === compose profile local names (`mongodb-local`, `postgres-local`). No third spelling (`supabase`, `local-postgres`, `mongo` as a mode).

**Pull-forward note (2026-07-26):** Mode rename + `/healthz` `storage_mode` may land with the flag vocabulary pass before index introspection; if so, this slice After-Checks still own dashboard badge polish, indexes CLI, and Postgres preflight introspection.

---

## Preflight behaviour (Postgres-native, not Atlas Admin API)

Indexes come from [`schema.sql`](../../../server/db/schema.sql) at pool bootstrap. Preflight **introspects** required HNSW/GIN and returns 422 only when DDL/extension is missing or wrong — not an Atlas quota/create/reconcile dance.

Align with today’s `preflight_not_applicable()` short-circuit: promote introspection so the guard verifies presence; schema bootstrap remains the ensure path. Do not invent Atlas-style “create missing index via Admin API” for Postgres.

---

## Spec (GWT)

```
Scenario: Preflight rejects missing HNSW/GIN indexes
  Given STORAGE_BACKEND=postgres and required indexes absent (or vector extension missing)
  When experiment submit runs
  Then HTTP 422 with actionable mismatch detail
  And the server does not call Atlas Admin APIs

Scenario: Db-stats returns sizes without Atlas Admin API
  Given Postgres backend (local or hosted)
  When db-stats API is called
  Then response includes database/relation size fields the dashboard can render
  And postgres_stats helpers already shipped in Slice 33 are reused/extended
  And storage_mode is one of mongodb-local|mongodb-cloud|postgres-local|postgres-cloud

Scenario: Storage mode — mongodb-cloud
  Given STORAGE_BACKEND=mongodb (or legacy mongo) and an Atlas cloud MONGODB_URI
  When GET /healthz (or db-stats) is queried
  Then storage_mode is mongodb-cloud

Scenario: Storage mode — mongodb-local
  Given STORAGE_BACKEND=mongodb and an Atlas Local / localhost URI
  When GET /healthz is queried
  Then storage_mode is mongodb-local

Scenario: Storage mode — postgres-local
  Given STORAGE_BACKEND=postgres and a local Docker DATABASE_URL
  When GET /healthz is queried
  Then storage_mode is postgres-local

Scenario: Storage mode — postgres-cloud
  Given STORAGE_BACKEND=postgres and a *.supabase.* DATABASE_URL
  When GET /healthz is queried
  Then storage_mode is postgres-cloud

Scenario: Mode token matches flag vocabulary
  Given any healthy server
  When storage_mode is read from /healthz
  Then ./start-services.sh --{storage_mode} is the documented restart command for that mode

Scenario: indexes list shows known vs missing indexes on Postgres
  When rag-params-finder indexes list runs with STORAGE_BACKEND=postgres
  Then output distinguishes present vs required-missing indexes
```

---

## Before-Checks [GATE]

- [ ] Slice 35 ✅ PASSED
- [ ] Prefer `pg_*` size functions before Supabase Management API
- [ ] Confirm Slice 33 `postgres_stats.py` baseline before extending

---

## After-Checks [GATE]

- [ ] 422 parity with Mongo preflight UX (actionable detail; no Atlas calls on postgres)
- [ ] Dashboard stats smoke on Postgres
- [ ] Storage mode badge/field documented; values match flag names exactly
- [ ] **Slice 27 absorbed:** named tests for all four modes (`mongodb-local`, `mongodb-cloud`, `postgres-local`, `postgres-cloud`)
- [ ] No user-facing mode string is `supabase`, `local-postgres`, or bare `mongo`
- [ ] Mongo preflight/stats still pass when `STORAGE_BACKEND=mongodb` (legacy `mongo` alias OK)
- [ ] Specification coverage: every GWT clause has at least one test; essential error paths covered
- [ ] Branch coverage: target 100% where practical; document any exclusions
- [ ] Mutation testing run if slice is feature-complete: mutation budget ≤10% survivors
- [ ] Coverage + quality gates
- [ ] Doc audit: PRD §Documentation matrix rows for slice **36** (`cli-reference.md`, `configuration.md` storage-mode)
- [ ] `docs/plan/slices/PROGRESS.md` updated

## Gate Status

📋 PLANNED
