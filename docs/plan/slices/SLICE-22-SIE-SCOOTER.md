# Slice 22 — SIE Scooter — SIE reranking + SPLADE v3 sparse + `/api/v1/best-config`

**Status**: 📋 PLANNED
**MoSCoW**: Must (PCTO)
**Depends on**: 21 ✅, **32** (hard — StorageBackend Protocol), **38** (soft — cutover; escape hatch in TRAIL)

## Slice Workflow Header

Slice: 22 — SIE Scooter — SIE reranking + SPLADE v3 sparse + `/api/v1/best-config`

Files:
- server/core/reranker.py                 # add SIE score path for BGE-reranker
- server/core/model_registry.py           # add bge-reranker (sie, score) + splade-v3 sparse index support
- server/api/sweep.py                     # complete GET /api/v1/best-config + GET /api/v1/experiments/{id} alias
- tests/test_sie_reranker.py             # GWT tests for SIE score path (mock SIEClient)
- tests/test_best_config.py              # GWT tests for best-config lookup

Exit criteria:
  [ ] SIE reranking (BGE-reranker) produces relevance scores for query+doc pairs
  [ ] GET /api/v1/best-config returns a recommendation from sweep history
  [ ] ./scripts/quality-gates.sh passes
  [ ] No prior tests regressed

Commit pattern:
feat(sie): add SIE Scooter — reranking, SPLADE sparse, best-config API

- Wire BGE-reranker via SIE score primitive (replaces rerank-2.5-lite)
- Add SPLADE v3 sparse index support for full open-source BM25
- Complete GET /api/v1/best-config querying sweep history via StorageBackend

> **MCP note**: MCP server exposure (`get_rag_config` tool) is explicitly deferred — Won't have this cycle.
> If ever built, it MUST be a standalone reusable skill or global tool (not embedded in this service).
> The `GET /api/v1/best-config` endpoint is the clean integration point for any future MCP wrapper.

---

## Slice 22 — SIE Scooter [Must]

### Branch
`slice/22-sie-scooter`
Create from `main` after **Slice 38** (storage cutover) is merged — Depends on: 21, 38 (TRAIL 2026-07-09). If PCTO deadline forces earlier start, implement against StorageBackend Protocol (Mongo) and retest on Postgres after 38.

### Spec (GWT)

```
Scenario: SIE BGE-reranker scores query+document pairs
  Given SIEClient is initialised at http://localhost:8720
  When score(model="bge-reranker", query="AI agents", documents=["doc1","doc2"]) is called
  Then a list of two float scores is returned

Scenario: Reranker falls back gracefully when SIE is unreachable
  Given SIEClient cannot connect
  When score is called
  Then a RuntimeError is raised with message containing "SIE unreachable"

Scenario: SPLADE v3 sparse sweep variant runs alongside dense
  Given SIE running with SPLADE v3 model available
  When POST /api/v1/sweep includes retrieval_methods=["bm25"] with embedding_model="splade-v3"
  Then the sweep runs and returns sparse BM25 results with correct index used

Scenario: GET /api/v1/best-config returns recommendation from sweep history
  Given the active storage backend contains completed sweep results for topic="machine learning"
  When GET /api/v1/best-config?task=machine+learning
  Then HTTP 200 with recommended_config (retrieval_method, embedding_model, score), confidence, based_on_experiments ≥ 1

Scenario: GET /api/v1/best-config returns 404 when no history exists
  Given the active storage backend has no sweep results for the requested task
  When GET /api/v1/best-config?task=unknown-topic
  Then HTTP 404
```

### Before-Checks [GATE]
- [x] Merge PRs #47 (semantic chunker overlap) and #48 (padding sweep dimension) — merged to `main` 2026-07-05
- [ ] Slice 32 StorageBackend + RetrieverBackend Protocol merged to current branch
- [ ] All history and best-config queries use StorageBackend — no direct `server.db.atlas` or `mongo_store` imports in sweep/history code
- [ ] Branch `slice/22-sie-scooter` created from latest `main` (Slice 21 ✅; prefer after Slice 38 — see escape hatch in TRAIL)
- [ ] SIE Docker running; BGE-M3 encode probe returns HTTP 200 — see [SIE Provider Setup](../user-guide/sie-setup.md)
- [ ] `./scripts/quality-gates.sh` passes

> **Soft dep on Slice 38:** If cutover delays, implement via Protocol so Postgres porting is isolated to adapters, not Slice 22 code.

### TDD Execution

1. Write failing tests in `tests/test_sie_reranker.py` and `tests/test_best_config.py` from GWT scenarios. Mock `SIEClient.score()`.
2. RED — confirm all new tests fail.
3. GREEN — implement SIE score path and complete `GET /api/v1/best-config`.
4. Refactor — align with existing `reranker.py` dispatch pattern (provider-based dispatch).
5. Full suite — no regressions.

### Implementation Steps

1. **Add `bge-reranker` to model registry** with provider=`sie`, primitive=`score`
2. **Extend `server/core/reranker.py`** — add `sie` dispatch branch calling `SIEClient.score()`; raise `RuntimeError` on connection failure
3. **Add SPLADE v3 sparse index support**: ensure Atlas vector index for sparse output format is created; document in `CLAUDE.local.md`
4. **Complete `GET /api/v1/best-config`** in `server/api/sweep.py`:
   - Query completed sweeps via `StorageBackend` (not direct Mongo collections)
   - Aggregate best score per config; return top result with confidence heuristic
5. **Add `GET /api/v1/experiments/{id}` alias** at `/api/v1` prefix (one-liner forwarding to existing route)
6. **Write tests** for all GWT scenarios
7. **Run `./scripts/quality-gates.sh`**

### After-Checks [GATE]
- [ ] All GWT scenarios have passing named tests
- [ ] Full suite green, quality gates pass
- [ ] Specification coverage: every GWT clause has ≥1 test; essential error paths covered (90–100% of clauses)
- [ ] Branch coverage: 100% target; exclusions documented (test-writing-craft-quality.mdc §12)
- [ ] Mutation testing: survival budget met if slice is feature-complete (§23)
- [ ] Manual: run a sweep → then `GET /api/v1/best-config?task=<topic>` returns a real config
- [ ] Doc audit → YES: update PROGRESS.md (Slice 22 → ✅ COMPLETE); note SPLADE v3 index requirement in `CLAUDE.local.md`
- [ ] Security audit → NO (no new auth surface; MongoDB query uses parameterised task filter)
- [ ] Self-review + `/code-review` + `/clean-commit` + PR

### Gate Status
PLANNED

### Expected Outcomes
- SIE reranking (BGE-reranker) available as Tier 2 reranker option in sweep configs
- Full open-source BM25 via SPLADE v3 without MongoDB full-text search workaround
- `GET /api/v1/best-config` queryable by task description — the single integration point for any future agent or MCP wrapper

### Session Metrics

| Metric | Planning phase | Execution phase |
|--------|---------------|-----------------|
| Model | claude-sonnet-4-6 | claude-sonnet-4-6 |
| Tokens — input / output (est.) | — / — | — / — |
| Turns | — | — |
| Context sources loaded | TRAIL.md, slice-21 | + touched source files |
| Context pressure | none | — |
| Notes | MCP deferred — Won't have this cycle | — |
