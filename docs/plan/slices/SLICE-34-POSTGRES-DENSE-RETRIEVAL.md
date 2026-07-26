# SLICE 34 — Supabase Dense Retrieval (pgvector)

**MoSCoW:** MUST
**Target time:** ~3–4 h
**Status:** ✅ COMPLETE
**Depends on:** 33 (implementation: schema + store + local profile — not tracker PASSED)
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../PRD-supabase-pgvector-migration.md) §5.1.1, §6.3, §6.5

---

## Slice Workflow Bundle

- Slice name: `slice-34-postgres-dense-retrieval`
- Branch: `slice/34-postgres-dense-retrieval`
- Files (shipped):
  - `server/core/retriever_postgres.py` — dense path + dispatcher
  - `server/db/postgres_store.py` — `PostgresRetrieverBackend` delegates to dense search
  - `server/db/schema.sql` — HNSW indexes on `embedding_384` / `embedding_1024`
  - `server/db/postgres.py` — `hnsw.iterative_scan = strict_order` on every pooled connection
  - `server/core/search_index_guard.py` / `search_index_plan.py` — Atlas preflight short-circuit for non-mongo
  - `server/core/health_check.py` / `server/main.py` — backend-aware `/healthz` (`storage_backend`, not mode)
  - `tests/test_postgres_dense_retrieval.py` — **mandatory `embedding_model` filter tests**
- Exit criteria: Dense retrieval returns top-K for a real sweep on Postgres; cross-model comparison impossible by query construction
- Commit pattern: `feat(slice-34): pgvector dense retrieval with embedding_model filter`

---

## Goal

Implement cosine dense search via pgvector HNSW (Atlas-comparable score scale), preserving the critical invariant: **every vector query filters by `embedding_model`**.

---

## Spec (GWT)

```
Scenario: Dense search filters by embedding_model
  Given chunks for model A and model B in the same table
  When dense_search is called with embedding_model=A
  Then only chunks with embedding_model=A are returned

Scenario: Wrong dimension column is never queried
  Given a 384-dim query embedding
  When dense_search runs
  Then SQL uses embedding_384 (not embedding_1024)

Scenario: Dense sweep end-to-end
  Given STORAGE_BACKEND=postgres and a local MiniLM config
  When a dense-only sweep completes
  Then results contain ranked chunks with scores
```

---

## Out of scope / handed to 36–37

This slice does **not** finish local/cloud DX:

| Concern | Owner |
|---|---|
| Four-value `storage_mode` on `/healthz` + db-stats badge (`mongodb-local` \| `mongodb-cloud` \| `postgres-local` \| `postgres-cloud`) | Slice 36 |
| Honest Postgres index introspection (beyond Atlas short-circuit) | Slice 36 |
| Hosted `ensure_env` without `MONGODB_URI`; `--postgres-cloud` | Slice 37 |
| Flag vocabulary + low-friction two-command switching | Slice 37 |
| Config `database_provider` ↔ server consistency (422 + remediation) | Slice 37 |
| `postgres start\|stop\|reset\|status` lifecycle | Slice 37 |

`/healthz` today reports `storage_backend` (`mongo` \| `postgres`) only — location mode is Slice 36.

---

## Recall finding — why `hnsw.iterative_scan` is set on every connection

An HNSW index cannot apply a `WHERE` clause inside itself. Our mandatory
`experiment_id` / `embedding_model` / `run_id` filters therefore run *after* the
index returns its `ef_search` candidate set, and anything filtered out is simply
lost from the top-k.

Measured on this schema (2 472 chunks, 4 runs, planner forced onto HNSW,
`hnsw.iterative_scan = off`, `ef_search = 40`):

| Path | Rows returned for `LIMIT 20` |
|---|---|
| Exact (btree filter + sort) — planner's default choice | 20 |
| HNSW post-filter, iterative scan **off** | **3** (39 removed by filter) |
| HNSW post-filter, iterative scan **strict_order** | 20 |

A silently short result set would change the very scores this tool exists to
compare, so `server/db/postgres.py` sets `hnsw.iterative_scan = strict_order` on
every pooled connection (pgvector ≥ 0.8; older servers log a warning and keep the
planner's exact path). Two tests pin this — one reads the live setting, one forces
the HNSW path and asserts full recall. With the setting reverted they return 1 of
20 rows and fail.

At current data volumes the planner prefers the exact path anyway, so today's
sweeps are exact rather than approximate. Partitioning `chunks` by
`experiment_id` — which would let each partition's HNSW serve filter-free
queries — is the scale-up option if sweeps grow past the point where exact KNN is
affordable. Not needed now (YAGNI); noted in the roadmap.

---

## Before-Checks [GATE]

- [x] Slice 33 **implementation** available (schema + store + local profile + CI job) — tracker may still be IN PROGRESS for coverage/mutation/32B
- [x] HNSW / pgvector extension enabled in local container (pgvector 0.8.5, PG 16.14)

---

## After-Checks [GATE]

- [x] Unit tests prove `embedding_model` filter on every dense path (PRD AC) — the
      isolation test uses a rival model at the *same* 384 width in the *same* run,
      so neither the dimension column nor `run_id` can mask a missing filter;
      verified by mutation (neutering the filter fails the test)
- [x] Real dense sweep smoke on local Postgres — 4/4 runs complete, 2 472 chunks
      all in `embedding_384`, 308 query results, scores 0.587–0.920 on the Atlas scale
- [x] Mongo dense path unchanged — `retriever.py` untouched; the Atlas index
      preflight now short-circuits for non-Mongo backends only
- [x] Specification coverage: every GWT clause has at least one test; error paths
      (missing model, missing embedding, unsupported width, sparse/hybrid) covered
- [x] Branch coverage: `server/core/retriever_postgres.py` at **100%** statements and
      branches (21 tests). Enforced in the `postgres-integration` CI job at ≥95%,
      not the `backend` job — these tests skip without a database, so the main job
      would measure them as 0%
- [x] Mutation testing: four targeted mutants on the behaviours that carry the
      slice's risk, all killed —
      `embedding_model` filter neutered → isolation + ranking tests fail;
      `run_id` filter neutered → run-isolation test fails;
      score formula `1 - d/2` → `1 - d` → Atlas-scale test fails;
      `iterative_scan` → `off` → recall tests fail (1 of 20 rows).
      Nightly `mutmut` runs without a Postgres service, so it cannot cover this
      module; the targeted run above is the evidence
- [x] Coverage + quality gates — `./scripts/quality-gates.sh` green (11/11); full
      backend suite green, no regressions
- [x] Doc audit: `architecture.md` module tree (Postgres db modules + Postgres
      dense retriever), `postgres-setup.md` (dense retrieval, score scale, HNSW
      recall note), `CLAUDE.md` Key Files
- [x] `docs/plan/slices/PROGRESS.md` updated — status + decision-log entries

## Gate Status

✅ COMPLETE
