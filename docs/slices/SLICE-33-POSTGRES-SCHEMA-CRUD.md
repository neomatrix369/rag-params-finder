# SLICE 33 — Postgres Schema + Pool + Metadata/Chunks CRUD

**MoSCoW:** MUST
**Target time:** ~4–6 h
**Status:** 📋 PLANNED
**Depends on:** 32
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../plan/PRD-supabase-pgvector-migration.md) §6.2–6.4

---

## Slice Workflow Bundle

- Slice name: `slice-33-postgres-schema-crud`
- Branch: `slice/33-postgres-schema-crud`
- Files (expected):
  - `server/db/postgres.py` — pool (`asyncpg` or `psycopg`)
  - `server/db/postgres_uri.py` — cloud vs local detection (TLS)
  - `server/db/postgres_store.py` — StorageBackend impl
  - `server/db/schema.sql` or migrations — experiments, run_status, chunks, results
  - `pyproject.toml` — add Postgres client; keep pymongo
  - `docker-compose.yml` — `postgres` / pgvector service (profile)
  - `tests/test_postgres_store_crud.py`
- Exit criteria: With `STORAGE_BACKEND=postgres`, experiment CRUD + cascade delete + chunk insert work against local Postgres
- Commit pattern: `feat(slice-33): postgres schema and crud behind storage protocol`

---

## Goal

Ship a working Postgres/pgvector schema and CRUD path for experiments, run_status, chunks, and results — including cascade delete — behind the Slice 32 Protocol. Retrieval can return empty/stub; dense search is Slice 34.

---

## Spec (GWT)

```
Scenario: Cascade delete removes all related rows
  Given an experiment with runs, chunks, and results in Postgres
  When DELETE /experiments/{id} is called with STORAGE_BACKEND=postgres
  Then experiments, run_status, chunks, and results rows for that id are gone

Scenario: Chunks store dense columns by dimension
  Given embedding_model maps to 384 or 1024 dims
  When chunks are inserted
  Then the correct nullable vector column is populated and the other dense column is null

Scenario: Local Docker Postgres accepts connections without TLS
  Given DATABASE_URL points at local pgvector container
  When the server boots
  Then the pool connects and schema bootstrap succeeds
```

---

## Design constraints (from PRD)

- Single `chunks` table with `embedding_384`, `embedding_1024`, optional `embedding_sparse` (nullable)
- Raw SQL client end-to-end (no `vecs`)
- Env-driven URI via pydantic-settings
- FK `ON DELETE CASCADE` from child tables to experiments

---

## Before-Checks [GATE]

- [ ] Slice 32 ✅ PASSED
- [ ] Branch from main
- [ ] Local Docker available for pgvector image

---

## After-Checks [GATE]

- [ ] All GWT scenarios passing
- [ ] Mongo backend still green (dual-backend regression)
- [ ] Specification / branch coverage gates on new Postgres modules
- [ ] `.env.example` documents `STORAGE_BACKEND` + `DATABASE_URL`
- [ ] `./scripts/quality-gates.sh` passes
- [ ] Doc audit: user-guide stub or link for Postgres path (full parity in 37)

## Gate Status

📋 PLANNED
