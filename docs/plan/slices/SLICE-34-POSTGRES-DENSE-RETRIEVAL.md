# SLICE 34 — Supabase Dense Retrieval (pgvector)

**MoSCoW:** MUST
**Target time:** ~3–4 h
**Status:** 📋 PLANNED
**Depends on:** 33
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../plan/PRD-supabase-pgvector-migration.md) §5.1.1, §6.3, §6.5

---

## Slice Workflow Bundle

- Slice name: `slice-34-postgres-dense-retrieval`
- Branch: `slice/34-postgres-dense-retrieval`
- Files (expected):
  - `server/core/retriever.py` or `server/core/retriever_postgres.py` — dense path
  - HNSW indexes on `embedding_384` / `embedding_1024` (partial where not null)
  - `tests/test_postgres_dense_retrieval.py` — **mandatory `embedding_model` filter tests**
- Exit criteria: Dense retrieval returns top-K for a real sweep on Postgres; cross-model comparison impossible by query construction
- Commit pattern: `feat(slice-34): pgvector dense retrieval with embedding_model filter`

---

## Goal

Implement cosine (or IP-matching Atlas) dense search via pgvector HNSW, preserving the critical invariant: **every vector query filters by `embedding_model`**.

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

## Before-Checks [GATE]

- [ ] Slice 33 ✅ PASSED
- [ ] HNSW / pgvector extension enabled in local container

---

## After-Checks [GATE]

- [ ] Unit tests prove `embedding_model` filter on every dense path (PRD AC)
- [ ] Real dense sweep smoke on local Postgres
- [ ] Mongo dense path unchanged
- [ ] Specification coverage: every GWT clause has at least one test (BDD/GWT-first); essential error and timeout paths covered
- [ ] Branch coverage: target 100% where practical; document any exclusions
- [ ] Mutation testing run if slice is feature-complete: mutation budget ≤10% survivors
- [ ] Coverage + quality gates
- [ ] Doc audit: PRD §Documentation matrix rows for slice **34** (`architecture.md` Postgres dense)
- [ ] `docs/plan/slices/PROGRESS.md` updated

## Gate Status

📋 PLANNED
