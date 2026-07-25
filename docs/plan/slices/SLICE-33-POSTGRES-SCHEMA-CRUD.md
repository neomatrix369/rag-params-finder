# SLICE 33 — Supabase Schema + Pool + Metadata/Chunks CRUD

**MoSCoW:** MUST
**Target time:** ~4–6 h
**Status:** 🔨 IN PROGRESS
**Depends on:** 32B
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

- [x] Add Postgres/pgvector service to CI — `postgres-integration` job in `.github/workflows/ci.yml`
      (`pgvector/pgvector:pg16` service container on 5433, health-gated)
- [x] Smoke: `STORAGE_BACKEND=postgres` CRUD test passes in CI pipeline —
      `tests/test_postgres_store_integration.py`, with `RAG_REQUIRE_POSTGRES=1` so a
      missing container fails instead of skipping

## Before-Checks [GATE]

- [ ] Slice 32B ✅ PASSED (gate closure for Storage Protocol — coverage, mutation/waiver, full gates, nw-review)
      — **outstanding:** user chose to proceed with 32C M3 only and defer 32B
- [ ] Branch from main
- [x] Docker available for local pgvector smoke

---

## After-Checks [GATE]

- [x] All GWT scenarios passing — 19 tests, all four scenarios covered
      (cascade delete, dimension routing, local bootstrap without TLS, string `experiment_id`)
- [x] Specification coverage: every GWT clause has at least one test; error paths covered
      (unsupported dimension, empty chunk batch, empty interrupt list, unknown experiment id)
- [ ] Branch coverage: target 100% where practical; document any exclusions
- [ ] Mutation testing run if slice is feature-complete: mutation budget ≤10% survivors
- [x] Mongo backend still green (dual-backend regression) — full suite passes, 264 tests
- [x] `docker compose --profile local-postgres up` documented for manual smoke —
      [`docs/user-guide/postgres-setup.md`](../../user-guide/postgres-setup.md)
- [x] `.env.example` documents `STORAGE_BACKEND` + `DATABASE_URL`
- [x] `./scripts/quality-gates.sh` passes
- [x] Doc audit: `.env.example`, `configuration.md` env vars, new `postgres-setup.md`
- [x] `docs/plan/slices/PROGRESS.md` updated

## Deferred out of this slice

- **Retrieval** — `get_retriever_backend()` still raises for Postgres; dense lands in Slice 34,
  sparse/hybrid in Slice 35.
- **`embedding_sparse` column** — PRD lists it as optional here. `vector_column_for()` raises a
  `ValueError` naming Slice 35 rather than silently dropping SPLADE-width vectors.
- **Storage quota** — Postgres exposes no quota over SQL, so `database_storage_limit_mb` and
  `database_free_mb` report `None`; Slice 36 owns the capacity story.

## Gate Status

🔨 IN PROGRESS — implementation and CI complete; branch coverage and mutation
testing outstanding, and Slice 32B remains an open upstream gate.
