# SLICE 33 — Supabase Schema + Pool + Metadata/Chunks CRUD

**MoSCoW:** MUST
**Target time:** ~4–6 h
**Status:** 🔨 IN PROGRESS
**Depends on:** 32B
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../PRD-supabase-pgvector-migration.md)

> **Naming:** Supabase is hosted Postgres. This slice implements the Postgres/pgvector layer that Supabase runs in production and Docker pgvector runs locally (Path A). Hosted Path B operator DX lands in Slice 37.

---

## Slice Workflow Bundle

- Slice name: `slice-33-supabase-schema-crud`
- Branch: `slice/33-supabase-schema-crud`
- Files (shipped):
  - `server/db/postgres.py` — connection pool (`psycopg` pool; sync FastAPI alignment)
  - `server/db/postgres_uri.py` — Supabase vs local detection (TLS, pooler host)
  - `server/db/postgres_docs.py` — document ↔ row mapping + `vector_column_for`
  - `server/db/postgres_store.py` — `StorageBackend` impl
  - `server/db/postgres_stats.py` — stats / explore helpers (partial; Slice 36 extends)
  - `server/db/stats_common.py` — backend-agnostic db-stats assembly
  - `server/db/schema.sql` — experiments, run_status, chunks, results + HNSW indexes
  - `server/db/store_factory.py` — returns Postgres adapters when `STORAGE_BACKEND=postgres`
  - `pyproject.toml` — `psycopg[binary]`; keep pymongo
  - `docker-compose.yml` — `postgres-local` service under `local-postgres` profile
  - `start-services.sh` / `scripts/lib/compose.sh` — `--postgres` / `RAG_LOCAL_POSTGRES=1` (canonical rename to `--postgres-local` in Slice 37)
  - `configs/supabase/example-local.yaml`
  - `docs/user-guide/postgres-setup.md` — Path A (local) documented
  - `tests/test_postgres_store_integration.py` — 19 live CRUD/cascade/stats tests
- Exit criteria: With `STORAGE_BACKEND=postgres`, experiment CRUD + cascade delete + chunk insert work against local pgvector container
- Commit pattern: `feat(slice-33): supabase postgres schema and crud behind storage protocol`

---

## Goal

Ship Postgres/pgvector schema and CRUD for experiments, run_status, chunks, and results — including cascade delete — behind the Slice 32 `StorageBackend` port. Retrieval stubs until Slice 34.

**Decision (2026-07-26):** Local compose (`--postgres` → future `--postgres-local`) landed in this slice so 34–36 could proceed without waiting. Hosted cloud operator path (`--postgres-cloud`, `ensure_env` without `MONGODB_URI`, lifecycle subcommands) remains Slice 37. Do not claim hosted Supabase smoke here.

---

## Operator contract (local half only)

| Concern | This slice |
|---|---|
| Local one-command | `./start-services.sh --postgres` (alias; Slice 37 renames to `--postgres-local`) |
| Cloud / hosted | Out of scope — Slice 37 |
| Docs | [`postgres-setup.md`](../../user-guide/postgres-setup.md) Path A; Path B expanded in 37 |
| Example config | `configs/supabase/example-local.yaml` (not `example-supabase-local.yaml`) |

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

- Single `chunks` table with `embedding_384`, `embedding_1024`, optional `embedding_sparse` (nullable — deferred to 35)
- Raw SQL via `psycopg` — no `vecs`
- Env: `STORAGE_BACKEND=postgres`, `DATABASE_URL=...` (Supabase connection string in cloud)
- FK `ON DELETE CASCADE` from child tables to experiments
- Local compose is part of this slice’s delivered surface; hosted `ensure_env` / flag vocabulary / lifecycle parity are Slice 37

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
- [x] Mongo backend still green (dual-backend regression) — full suite passes
- [x] Local pgvector profile documented for manual smoke —
      [`docs/user-guide/postgres-setup.md`](../../user-guide/postgres-setup.md) Path A
- [x] `.env.example` documents `STORAGE_BACKEND` + `DATABASE_URL`
- [x] `./scripts/quality-gates.sh` passes
- [x] Doc audit: `.env.example`, `configuration.md` env vars, new `postgres-setup.md`
- [x] `docs/plan/slices/PROGRESS.md` updated

## Deferred out of this slice

- **Retrieval** — dense lands in Slice 34; sparse/hybrid in Slice 35.
- **`embedding_sparse` column** — PRD lists it as optional here. `vector_column_for()` raises a
  `ValueError` naming Slice 35 rather than silently dropping SPLADE-width vectors.
- **Storage quota / mode badge** — Slice 36 owns capacity story and four-value `storage_mode`.
- **Hosted Supabase operator path** — Slice 37 (`--postgres-cloud`, `ensure_env`, lifecycle, Path B docs, low-friction switching).
- **Flag rename + config consistency gate** — `--postgres` → `--postgres-local`; YAML `database_provider` must match active backend (Slice 37).
- **Four-value `storage_mode`** — Slice 36 (may pull forward with 37 vocabulary pass).

## Gate Status

🔨 IN PROGRESS — implementation and CI complete; branch coverage and mutation
testing outstanding, and Slice 32B remains an open upstream gate.
