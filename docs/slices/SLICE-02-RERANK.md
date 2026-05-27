# SLICE 02 — Rerank

**MoSCoW:** MUST
**Target time:** ~20 min
**Actual time:** ~10 min
**Status:** ✅ COMPLETE (2026-05-02)

---

## Goal

Add Voyage reranking to refine dense search results: top-`top_k_initial` candidates → top-`top_k_final` final results. Enables A/B comparison of dense-only vs reranked results.

---

## Acceptance Criteria

- [x] `server/core/reranker.py` dispatches to Voyage `rerank-2.5-lite`
- [x] Orchestrator executes RERANKING phase after QUERYING
- [x] `rerank_score` stored alongside `dense_score` in results
- [x] `rerank_model: null` skips the phase (dense-only path preserved)
- [x] Config field `top_k_initial` controls candidates fetched; `top_k_final` controls survivors

---

## Files Changed

| File | Change |
|---|---|
| `server/core/reranker.py` | **NEW** — Voyage rerank client; reuses embedder's client singleton |
| `server/core/orchestrator.py` | **EDIT** — Conditional RERANKING phase after QUERYING |
| `configs/example.yaml` | **EDIT** — `rerank_model: rerank-2.5-lite` (was `null`) |

---

## Key Decisions

| Decision | Why |
|---|---|
| Reuse embedder's `get_client()` singleton | Voyage SDK uses one client for both embed + rerank; avoids duplicate initialisation |
| Gate on `rerank_model` field | `null` skips reranking for A/B baseline comparison |
| `model_copy(update=...)` for SearchResult | Immutable Pydantic update — preserves original `dense_score` alongside `rerank_score` |

---

## Exit Criteria

- RERANKING phase appears in run_status progression
- Results collection has both `dense_score` and `rerank_score`
- Config with `rerank_model: null` completes without RERANKING phase

## Quality gates (current project standard)

```bash
./scripts/quality-gates.sh
```

See [`docs/contributor-guide/development.md`](../contributor-guide/development.md) and [`SLICE-20-TOOLCHAIN-HARDENING.md`](./SLICE-20-TOOLCHAIN-HARDENING.md).
