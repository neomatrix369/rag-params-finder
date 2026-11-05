# SLICE 61 — Phase 3: vector store as a sweep dimension (cross-store comparison as a real feature)

**MoSCoW:** COULD
**Target time:** ~16–24 h (to be sized)
**Status:** 📋 PLANNED — **backlog stub** (from the Phase 0 master prompt's "later phases"; needs a short interview/sizing before execution)
**Depends on:** **56** (Phase 0 leaderboard) · **60** (latency + metrics) · **54** (embedding cache) · **53**
**Branch:** `slice/61-vector-store-sweep-dimension`
**Feature:** Grow the Phase 0 cross-store leaderboard into a first-class sweep feature.

---

## Context

Phase 0 compares existing runs across stores using the store as one more column. Phase 3 makes the **vector store a sweep dimension**: the same dataset + YAML run against several stores, with **matched index settings by default**, **stores in parallel plus a sequential latency pass** (so timings are comparable), and **embeddings shared via the Redis embedding cache** with a per-store fallback and a visible warning. Today `config_backend_guard` returns 422 when a YAML `database_provider` differs from `VECTOR_STORE_BACKEND`, and each server process has one vector store — both change here.

- **Depends-on outputs:** the cross-store config key from SLICE-56 Part A, `CacheBackend` (Slice 54), vector-store registry and `get_vector_store()` (Slice 49).

- **Invariants pointer:** `docs/plan/invariants.md`; `docs/plan/DECISION-OWNERSHIP.md` (ceiling raises and gate-topology changes are Human-owned).

## Non-goals

- Ranking stores by speed without the sequential latency pass.
- Managed/paid tiers beyond what each store's guide already covers.
- LLM-based evaluation.

## Output contract

- One YAML lists several stores; the sweep expands them as a dimension and groups results by config key.
- A latency pass runs sequentially after the parallel pass and is stored separately.
- Embeddings are computed once and reused across stores; if the cache is unavailable each store embeds itself and a warning is recorded.

## Spec (GWT) — outline, to be completed at sizing

- Given a YAML with stores [redis, mongodb] when submitted then runs exist for both with identical non-store parameters.
- Given the shared cache is down when the sweep runs then it completes with a warning, not a failure.
- Given the latency pass when it runs then no other store workload runs concurrently.

## Before-Checks [GATE]

- [ ] **Human decision:** relax `config_backend_guard` / single-store server (ADR needed).
- [ ] Check the vector-store registry and pairing rules still hold with several active stores.
- [ ] Memory/capacity preflight for several stores at once (Redis `maxmemory` is 256 MB locally).

## After-Checks [GATE]

- [ ] Every GWT scenario has ≥1 test; backend floors and frontend floors 95/90/95/95 unchanged.
- [ ] `./scripts/ci/quality-gates.sh` green.
- [ ] Docs updated: CHANGELOG, affected user/contributor docs, PROGRESS, DECISIONS.

### Closing Gates

- [ ] `nw-at-completeness-check` — AT completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline review (slice close gate #9)
- [ ] `nw-documentarist-reviewer` — docs currency where docs change
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)

## Gate Status

📋 PLANNED — stub. Gate evidence (`docs/plan/gate-evidence/slice-61.json`) is written by the executor, never pre-created.
