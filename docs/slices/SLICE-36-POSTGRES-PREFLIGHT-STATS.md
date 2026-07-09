# SLICE 36 — Postgres Index Preflight + DB Stats + Indexes CLI

**MoSCoW:** MUST
**Target time:** ~3–4 h
**Status:** 📋 PLANNED
**Depends on:** 35
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../plan/PRD-supabase-pgvector-migration.md) §5.1.7–5.1.8, §5.2 CLI purpose

---

## Slice Workflow Bundle

- Slice name: `slice-36-postgres-preflight-stats`
- Branch: `slice/36-postgres-preflight-stats`
- Files (expected):
  - `server/core/search_index_plan.py` — generalize required-index output (backend-agnostic plan)
  - `server/core/search_index_guard.py` or `postgres_index_guard.py` — Postgres introspection
  - `server/core/postgres_storage.py` — `pg_database_size` / relation sizes (replace Atlas Admin for Postgres path)
  - `cli/indexes_cmd.py` — list/reset purpose preserved for Postgres
  - Dashboard stats panels continue to consume API shape
  - `tests/test_postgres_index_guard.py`, `tests/test_postgres_db_stats.py`
- Exit criteria: Missing indexes → HTTP 422 on submit; db-stats panels non-error on Postgres; indexes CLI useful for quota troubleshooting
- Commit pattern: `feat(slice-36): postgres index preflight and db stats`

---

## Goal

Postgres-native equivalents of search-index preflight and vector DB stats reporting, preserving CLI `indexes list|reset` purpose and dashboard `VectorDbStatsPanel` data source.

---

## Spec (GWT)

```
Scenario: Preflight rejects missing HNSW/GIN indexes
  Given STORAGE_BACKEND=postgres and required indexes absent
  When POST /experiments (or sweep submit) runs
  Then HTTP 422 with actionable mismatch detail

Scenario: Db-stats returns sizes without Atlas Admin API
  Given Postgres backend
  When GET db-stats (or equivalent) is called
  Then response includes database/relation size fields dashboard can render

Scenario: indexes list shows known vs missing Postgres indexes
  When `rag-params-finder indexes list` runs against Postgres
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
- [ ] Mongo preflight/stats still pass
- [ ] Coverage + quality gates
- [ ] Doc audit: indexes CLI docs mention both backends

## Gate Status

📋 PLANNED
