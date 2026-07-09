# SLICE 35 — Postgres Sparse + Hybrid Retrieval

**MoSCoW:** MUST
**Target time:** ~4–5 h
**Status:** 📋 PLANNED
**Depends on:** 34
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../plan/PRD-supabase-pgvector-migration.md) §5.1.2–5.1.3, §7 SPLADE risk

---

## Slice Workflow Bundle

- Slice name: `slice-35-postgres-sparse-hybrid`
- Branch: `slice/35-postgres-sparse-hybrid`
- Files (expected):
  - `fts` / `tsvector` + GIN on chunks
  - SQL `hybrid_search()` (RRF CTEs) with `embedding_model` filter
  - Sparse path for keyword BM25-equivalent; SPLADE/`sparsevec` only if non-zero counts pass gate
  - `tests/test_postgres_sparse_hybrid.py`
- Exit criteria: Sparse and hybrid return results on a real sweep; RRF uses project weight/`rrf_k` tunables where exposed
- Commit pattern: `feat(slice-35): postgres sparse and hybrid rrf retrieval`

---

## Goal

Parity for `sparse` and `hybrid` retrieval on Postgres using `tsvector`/`ts_rank` and Supabase-documented RRF fusion, extended with mandatory `embedding_model` filtering on the dense CTE.

---

## Spec (GWT)

```
Scenario: Sparse search returns keyword matches
  Given chunks containing distinctive tokens
  When sparse retrieval runs for a matching query
  Then those chunks rank above unrelated chunks

Scenario: Hybrid uses RRF fusion
  Given dense and sparse candidate sets
  When hybrid_search runs with rrf_k and weights
  Then fused ranking differs from pure dense and pure sparse in the expected direction

Scenario: SPLADE sparsevec gate
  Given a real SPLADE-v3 encode on project corpus
  When non-zero element counts are logged
  Then design commits to sparsevec only if max non-zeros ≤ 1000; otherwise document fallback
```

---

## Before-Checks [GATE]

- [ ] Slice 34 ✅ PASSED
- [ ] Instrument SPLADE non-zero counts before locking `sparsevec` column

---

## After-Checks [GATE]

- [ ] Sparse + hybrid real-sweep smoke
- [ ] RRF weights/`rrf_k` wired or explicitly N/A with reason
- [ ] SPLADE decision logged in DECISIONS.md
- [ ] Coverage + quality gates
- [ ] Doc audit: configuration.md retrieval notes

## Gate Status

📋 PLANNED
