# SLICE 33 — Supabase Schema + Pool + Metadata/Chunks CRUD

**MoSCoW:** MUST
**Target time:** ~4–6 h
**Status:** 📋 PLANNED
**Depends on:** 32
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../plan/PRD-supabase-pgvector-migration.md)

> **Naming:** Supabase is hosted Postgres. This slice implements the Postgres/pgvector layer that Supabase runs in production and Docker pgvector runs locally.

---

## Slice Workflow Bundle

- Slice name: `slice-33-supabase-schema-crud`
- Branch: `slice/33-supabase-schema-crud`
- Files (expected):
  - `server/db/postgres.py` — connection pool (`psycopg` pool; sync FastAPI alignment)
  - `server/db/postgres_uri.py` — Supabase vs local detection (TLS, pooler host)
  - `server/db/postgres_store.py` — `StorageBackend` impl
  - `server/db/schema.sql` or migrations — experiments, run_status, chunks, results
  - `pyproject.toml` — add `psycopg[binary]`; keep pymongo
  - `docker-compose.yml` — `pgvector` service under `local-postgres` profile (**minimal smoke** — full `start-services.sh` in 37)
  - `configs/example-supabase-local.yaml` (or `example-postgres-local.yaml`)
  - `tests/test_postgres_store_crud.py`
- Exit criteria: With `STORAGE_BACKEND=postgres`, experiment CRUD + cascade delete + chunk insert work against local pgvector container
- Commit pattern: `feat(slice-33): supabase postgres schema and crud behind storage protocol`

---

## Goal

Ship Postgres/pgvector schema and CRUD for experiments, run_status, chunks, and results — including cascade delete — behind the Slice 32 `StorageBackend` port. Retrieval stubs until Slice 34. **Minimal local Docker** in this slice so 34–36 can dev-test without waiting for Slice 37.

---

## experiment_id contract (locked)

- **External ID unchanged:** API, CLI, and dashboard continue to use string `experiment_id` (same shape as Mongo documents today).
- **Internal PK:** optional UUID column; if used, `experiment_id` remains a unique indexed text column — not the sole PK exposed to clients.
- **No breaking migration** of existing dashboard URLs or CLI commands in this slice.

---

## Spec (GWT)

```
Scenario: Cascade delete removes all related rows
  Given an experiment with runs, chunks, and results in Postgres
  When DELETE /experiments/{id} is called with STORAGE_BACKEND=postgres
  Then experiments, run_status, chunks, and results rows for that experiment_id are gone

Scenario: Chunks store dense columns by dimension
  Given embedding_model maps to 384 or 1024 dims
  When chunks are inserted
  Then the correct nullable vector column is populated and the other dense column is null

Scenario: Local pgvector container accepts connections without TLS
  Given DATABASE_URL points at local pgvector container (docker-compose profile)
  When the server boots
  Then the pool connects and schema bootstrap succeeds

Scenario: External experiment_id preserved
  Given an experiment is created via POST /experiments
  When the response is returned
  Then experiment_id is a string matching the existing API contract (not a raw UUID-only identifier)
```

---

## Design constraints (from PRD)

- Single `chunks` table with `embedding_384`, `embedding_1024`, optional `embedding_sparse` (nullable)
- Raw SQL via `psycopg` — no `vecs`
- Env: `STORAGE_BACKEND=postgres`, `DATABASE_URL=...` (Supabase connection string in cloud)
- FK `ON DELETE CASCADE` from child tables to experiments
- **Minimal smoke trade-off:** `docker compose --profile local-postgres` starts pgvector only in Slice 33; full `start-services.sh` integration deferred to Slice 37. Mitigation: Slice 37 Before-Checks gate on 33 profile completeness.

---

## CI (mandatory before merge)

- [ ] Add Postgres/pgvector service to CI (or `quality-gates.sh --postgres`) — **required before merging Slices 33–37**
- [ ] Smoke: `STORAGE_BACKEND=postgres` CRUD test passes in CI pipeline

## Before-Checks [GATE]

- [ ] Slice 32 ✅ PASSED
- [ ] Branch from main
- [ ] Docker available for local pgvector smoke

---

## After-Checks [GATE]

- [ ] All GWT scenarios passing
- [ ] Mongo backend still green (dual-backend regression)
- [ ] `docker compose --profile local-postgres up` documented for manual smoke (one-liner in slice notes)
- [ ] `.env.example` documents `STORAGE_BACKEND` + `DATABASE_URL`
- [ ] `./scripts/quality-gates.sh` passes
- [ ] Doc audit: PRD glossary + env table stub

## Gate Status

📋 PLANNED
