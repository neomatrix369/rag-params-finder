# SLICE 36 — Supabase Index Preflight + DB Stats + Indexes CLI

**MoSCoW:** MUST
**Target time:** ~3–4 h
**Status:** 📋 PLANNED
**Depends on:** 35
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../plan/PRD-supabase-pgvector-migration.md)

---

## Slice Workflow Bundle

- Slice name: `slice-36-supabase-preflight-stats`
- Branch: `slice/36-supabase-preflight-stats`
- Files (expected):
  - `server/core/search_index_plan.py` — backend-agnostic required-index plan
  - `server/core/search_index_guard.py` or `postgres_index_guard.py` — Postgres introspection
  - `server/core/postgres_storage.py` — `pg_database_size` / relation sizes
  - `cli/indexes_cmd.py` — list/reset for Postgres backend
  - `server/core/health_check.py` or `/healthz` — **storage mode** indicator (`mongo` | `local-postgres` | `supabase`)
  - Dashboard header badge / sweep_summary field (replaces deferred Slice 27 scope)
  - `tests/test_postgres_index_guard.py`, `tests/test_postgres_db_stats.py`
- Exit criteria: Missing indexes → HTTP 422; db-stats panels work; indexes CLI useful; storage mode visible
- Commit pattern: `feat(slice-36): supabase index preflight db stats and storage mode`

---

## Goal

Supabase/Postgres equivalents of search-index preflight and vector DB stats, plus a **storage-backend mode indicator** (mongo vs local pgvector vs hosted Supabase) — absorbing the intent of deferred Slice 27.

---

## Spec (GWT)

```
Scenario: Preflight rejects missing HNSW/GIN indexes
  Given STORAGE_BACKEND=postgres and required indexes absent
  When experiment submit runs
  Then HTTP 422 with actionable mismatch detail

Scenario: Db-stats returns sizes without Atlas Admin API
  Given Postgres/Supabase backend
  When db-stats API is called
  Then response includes database/relation size fields the dashboard can render

Scenario: Storage mode visible to operators
  Given STORAGE_BACKEND=postgres and a Supabase cloud DATABASE_URL
  When GET /healthz (or dashboard header) is queried
  Then mode indicates supabase (or local-postgres for Docker URI) — not generic "postgres" only

Scenario: Storage mode covers all backends (absorbed Slice 27)
  Given STORAGE_BACKEND is mongo, local-postgres Docker, or hosted Supabase
  When db-stats or health is queried
  Then storage_mode field is one of mongo | local-postgres | supabase with the correct value per backend

Scenario: indexes list shows known vs missing indexes on Postgres
  When rag-params-finder indexes list runs with STORAGE_BACKEND=postgres
  Then output distinguishes present vs required-missing indexes
```

---

## Before-Checks [GATE]

- [ ] Slice 35 ✅ PASSED
- [ ] Prefer `pg_*` size functions before Supabase Management API

---

## After-Checks [GATE]

- [ ] 422 parity with Mongo preflight UX
- [ ] Dashboard stats smoke on Postgres
- [ ] Storage mode badge/field documented
- [ ] **Slice 27 absorbed:** db-stats / health returns `mongo` | `local-postgres` | `supabase` with correct value per backend (named tests for each mode)
- [ ] Mongo preflight/stats still pass
- [ ] Coverage + quality gates
- [ ] Doc audit: PRD §Documentation matrix rows for slice **36** (`cli-reference.md`, `configuration.md` storage-mode)
- [ ] `docs/plan/slices/PROGRESS.md` updated

## Gate Status

📋 PLANNED
