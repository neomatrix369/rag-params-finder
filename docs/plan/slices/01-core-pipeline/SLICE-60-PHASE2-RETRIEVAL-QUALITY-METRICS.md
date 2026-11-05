# SLICE 60 — Phase 2: zero-LLM retrieval-quality metrics (Recall@k, MRR, nDCG, hit rate)

**MoSCoW:** SHOULD
**Target time:** ~12–16 h (to be sized)
**Status:** 📋 PLANNED — **backlog stub** (from the Phase 0 master prompt's "later phases"; needs a short interview/sizing before execution)
**Depends on:** **55** · golden-master schema decision (Human) · soft: 57B
**Branch:** `slice/60-retrieval-quality-metrics`
**Feature:** Replace raw similarity scores with real relevance metrics, still without any LLM.

---

## Context

Today a run is ranked by similarity score only (`analyze_results`); there are no labels or expected sources, so scores are not comparable across retrieval methods (see SLICE-57D) and the Fed Loan golden master has only `text` + `focus` per question. This slice adds **Recall@k, MRR, nDCG (binary relevance) and hit rate**, with **k set in YAML (default 1, 3, 5, 10)**. Strictly zero-LLM: LLM-judged metrics (faithfulness, answer relevance) are out. **Expected sources** are an any-of list of document ID + evidence span in the golden master. Per-config latency (indexing and query) is a Should; a false-positive view (top-k chunks outside the golden set) is a Could. When it ships, the 'evals underway' banner in the About box is removed (one line).

- **Depends-on outputs:** `analyze_results()`, `QueryResult` / `SearchResult`, the questions file format `configs/questions.example.json`.

- **Invariants pointer:** `docs/plan/invariants.md`; `docs/plan/DECISION-OWNERSHIP.md` (ceiling raises and gate-topology changes are Human-owned).

## Non-goals

- LLM-judged metrics (faithfulness, answer relevance, context precision via LLM).
- Building golden masters automatically (Ragas stays an offline tool; see SLICE-56 Part J / SLICE-58).
- Cross-store parallel sweeps (→ SLICE-61).

## Output contract

- Questions files accept expected sources (doc ID + evidence span, any-of) and still load without them.
- Results docs carry per-query relevance hits and the four metrics at the configured k values.
- The dashboard ranks by a chosen metric and labels it; similarity score stays available.
- Latency per config (indexing, query) is recorded and shown, labelled as indicative.

## Spec (GWT) — outline, to be completed at sizing

- Given a golden master with expected sources when a sweep completes then Recall@k, MRR, nDCG and hit rate are stored for each k.
- Given a questions file without expected sources when loaded then the sweep behaves as today and metrics are absent, not zero.
- Given any-of expected sources when one matches the top-k then the query counts as a hit.

## Before-Checks [GATE]

- [ ] **Human decision:** expected-sources schema in the questions file and how existing golden masters are upgraded (e.g. mapping Ragas reference contexts to doc IDs).
- [ ] Decide the ranking metric precedence vs `max_score` (touches the canonical ranking; ADR candidate).
- [ ] Confirm it unblocks SLICE-57D (comparability gate).

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

📋 PLANNED — stub. Gate evidence (`docs/plan/gate-evidence/slice-60.json`) is written by the executor, never pre-created.
