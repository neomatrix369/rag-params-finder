# Slice 22 — SIE Scooter — SIE reranking + SPLADE v3 sparse + `/api/v1/best-config`

**Status**: ✅ COMPLETE
**MoSCoW**: Must (PCTO)
**Depends on**: 21 ✅, **32** Protocol on main (IMPLEMENTED — formal 32B gate debt parallel), **38** ✅ soft (cutover COMPLETE)

> **Executed 2026-07-29** on `slice/22-sie-scooter` (`9805de8` feat + `383541b` hermetic/docs follow-up). Plan refresh Path A + `/nw-execute` — DECISIONS #166–#170. `/verify-slice` **COMPLETE** (unit/API-mock **VERIFIED**).

## Slice Workflow Header

Slice: 22 — SIE Scooter — SIE reranking + SPLADE sparse path + `/api/v1/best-config`

Files:
- `server/core/rerank/reranker.py` — add `sie` dispatch calling `SIEClient.score()` for BGE-reranker
- `server/core/model_registry.py` — add `bge-reranker` (`provider: sie`); `splade-v3` already present (do not re-add)
- `server/api/sweep.py` — persist Tier-1 sweep summaries via StorageBackend; complete `GET /api/v1/best-config`; optional `GET /api/v1/experiments/{id}` alias
- `server/core/embedding/sie_embedder.py` — or thin `sie_scorer` helper if score stays out of embedder (reuse `_get_client()`)
- `tests/server/core/rerank/test_sie_reranker.py` — GWT: score OK + unreachable RuntimeError (mock `SIEClient.score`)
- `tests/server/api/test_best_config.py` — GWT: 200 with history / 404 empty (mock StorageBackend)
- `docs/user-guide/sie-setup.md` — note `vector_index_30522` / SPLADE sparse path when documenting operator steps

Exit criteria:
  [x] SIE reranking (BGE-reranker) produces relevance scores for query+doc pairs
  [x] `POST /api/v1/sweep` persists a lightweight sweep summary via StorageBackend (topic + ranked configs)
  [x] `GET /api/v1/best-config?task=…` returns a recommendation from persisted sweep history (200) or 404
  [x] SPLADE sparse sweep path asserts registry+index foundation is used (no re-create of registry row)
  [x] `./scripts/ci/quality-gates.sh` passes
  [x] No prior tests regressed

Commit pattern:
```
feat(sie): add SIE Scooter — reranking, SPLADE sparse path, best-config API

- Wire BGE-reranker via SIE score primitive
- Persist Tier-1 sweep summaries via StorageBackend; complete GET /api/v1/best-config
- Assert SPLADE sparse path against existing registry + vector_index_30522
```

> **MCP note**: MCP server exposure (`get_rag_config` tool) is explicitly deferred — Won't have this cycle (DECISIONS #8).
> The `GET /api/v1/best-config` endpoint is the clean integration point for any future MCP wrapper.

---

## Slice 22 — SIE Scooter [Must]

### Branch
`slice/22-sie-scooter`
Create from latest `main` (Slice 21 ✅, Slice 38 ✅, Protocol on main). Formal tracker rows **32 / 32C / 32B / 33** remain parallel gate debt — do not block execution (DECISIONS #51 escape hatch + #166).

Ship after gate PASS via **release branch + PR** — see [`docs/contributor-guide/release-process.md`](../../../contributor-guide/release-process.md). Never push a version bump directly to `main`.

### Spec (GWT)

```
Scenario: SIE BGE-reranker scores query+document pairs
  Given SIEClient is initialised (SIE_ENDPOINT reachable; SIE_ENABLED=true)
  When score(model="bge-reranker", query="AI agents", documents=["doc1","doc2"]) is called via the sie rerank path
  Then a list of two float scores is returned

Scenario: Reranker fails securely when SIE is unreachable
  Given SIEClient cannot connect
  When score is called via the sie rerank path
  Then a RuntimeError is raised with message containing "SIE unreachable"

Scenario: SPLADE v3 sparse sweep variant uses existing registry and index
  Given embedding model "splade-v3" is already in EMBEDDING_MODELS (30522-dim) and Atlas index name vector_index_30522 exists
  When POST /api/v1/sweep includes retrieval_methods=["bm25"] with embedding_model="splade-v3"
  Then the sweep runs and returns sparse BM25-oriented results without inventing a new registry entry

Scenario: POST /api/v1/sweep persists history for best-config lookup
  Given a successful Tier-1 sweep for topic="machine learning"
  When the sweep handler completes
  Then the active StorageBackend holds a lightweight sweep summary (topic + ranked configs) queryable by task

Scenario: GET /api/v1/best-config returns recommendation from sweep history
  Given the active storage backend contains completed sweep results for topic="machine learning"
  When GET /api/v1/best-config?task=machine+learning
  Then HTTP 200 with best_config (retrieval_method, embedding_model, score), experiment_id, and history_count ≥ 1

Scenario: GET /api/v1/best-config returns 404 when no history exists
  Given the active storage backend has no sweep results for the requested task
  When GET /api/v1/best-config?task=unknown-topic
  Then HTTP 404
```


### Before-Checks [GATE]
- [x] Merge PRs #47 (semantic chunker overlap) and #48 (padding sweep dimension) — merged to `main` 2026-07-05
- [x] StorageBackend + RetrieverBackend Protocol **IMPLEMENTED on main** (`server/db/ports/storage.py`, `store_factory.py`) — formal 32B COMPLETE is parallel debt
- [x] Soft dep Slice 38 COMPLETE (ADR-004; default stays `mongodb` — #130 Won't flip)
- [x] All history and best-config queries use StorageBackend — no direct `mongo_store` / Atlas collection imports in sweep/history code
- [x] Branch `slice/22-sie-scooter` created from latest `main`
- [ ] SIE reachable (remote gateway or Docker); BGE-M3 encode probe returns HTTP 200 — see [SIE Provider Setup](../../../user-guide/sie-setup.md) (optional live After-Check)
- [x] `./scripts/ci/quality-gates.sh` passes on clean main before first RED / after GREEN

### TDD Execution

1. Write failing tests in `tests/server/core/rerank/test_sie_reranker.py` and `tests/server/api/test_best_config.py` from GWT scenarios. Mock `SIEClient.score()` and StorageBackend.
2. RED — confirm all new tests fail for the right reason.
3. GREEN — implement SIE score path, persist sweep summaries, complete `GET /api/v1/best-config`, assert SPLADE path.
4. Refactor — align with existing `rerank_results` provider dispatch; keep score helper composable.
5. Full suite — `./scripts/ci/quality-gates.sh` — no regressions.

### Implementation Steps

1. **Add `bge-reranker` to `RERANKER_MODELS`** with `provider: sie` (score primitive — not encode).
2. **Extend `server/core/rerank/reranker.py`** — add `sie` dispatch branch calling `SIEClient.score()`; raise `RuntimeError` containing `"SIE unreachable"` on connection failure.
3. **SPLADE sparse path (narrow)** — do **not** re-add `splade-v3` to the registry (already present). Assert sparse/bm25 sweep uses existing model + `vector_index_30522` (Mongo) / Postgres tsvector fallback (#49). Document operator note in `sie-setup.md` (and CLAUDE.local if still used for private Atlas steps).
4. **Persist Tier-1 sweep summaries** on successful `POST /api/v1/sweep` via `get_storage_backend()` (lightweight: topic, experiment_id, ranked configs/scores). Aim logging stays; StorageBackend is the history source for best-config.
5. **Complete `GET /api/v1/best-config`** in `server/api/sweep.py`:
   - Query completed sweeps via StorageBackend (mock Protocol in unit tests; both Mongo and Postgres adapters must satisfy the port)
   - Select highest stored `best_config.score` for the task; return `best_config`, `experiment_id`, `history_count`; 404 when no match
6. **Optional:** `GET /api/v1/experiments/{id}` alias at `/api/v1` prefix (one-liner forwarding to existing route) if still missing.
7. **Write tests** for all GWT scenarios; run `./scripts/ci/quality-gates.sh`.

### After-Checks [GATE]
- [x] All GWT scenarios have passing named tests
- [x] Full suite green, quality gates pass
- [x] Specification coverage: every GWT clause has ≥1 test; essential error paths covered (90–100% of clauses)
- [ ] Branch coverage: 100% target; exclusions documented (test-writing-craft-quality.mdc §12) — follow project floor policy if not measured per-slice
- [ ] Mutation testing: survival budget met if slice is feature-complete (§23) — or nightly waiver logged if pure I/O wrappers
- [ ] Manual: run a sweep → then `GET /api/v1/best-config?task=<topic>` returns a real config (optional live SIE)
- [x] Doc audit → YES: PROGRESS + sie-setup + `/sync-docs` plan/agent surfaces
- [x] Security audit → NO new auth surface; task filter parameterised; no secrets in responses
- [ ] Self-review + `/code-review` + `/clean-commit` + PR on `slice/22-sie-scooter`

### Gate Status
✅ COMPLETE — `/verify-slice` **COMPLETE** 2026-07-29 (**VERIFIED** at unit/API-mock boundary: 17/17 targeted tests; quality-gates + pre-push green). Commits `9805de8` + `383541b`. Optional live SIE smoke remains After-Check only; PR open is process next step (branch pushed).

### Expected Outcomes
- SIE reranking (BGE-reranker) available as Tier 2 reranker option in sweep configs
- SPLADE sparse path verified against existing registry + index foundation (no duplicate registry work)
- `GET /api/v1/best-config` queryable by task — single integration point for any future agent or MCP wrapper
- Tier-1 sweep history durable via StorageBackend (not Aim-only)

### Planning Quality Lens (Slice 22)

| # | Check | Result |
|---|-------|--------|
| 1 | Fewest elements | PASS — three PCTO deliverables only; MCP Won't |
| 2 | YAGNI | PASS — needed this increment (PCTO Must) |
| 3 | SLAP | PASS — feature wiring on existing ports; no infra setup |
| 4 | Walking skeleton | N/A for mid-trail Must (Slice 21 already proved SIE encode) |
| 5 | Composability | PASS — Protocol-on-main; 32B parallel |
| 6 | Rule of 3 | PASS — no new framework; provider dispatch already has 3+ cases |
| 7 | Specification-first | PASS — GWT before implementation steps |
| 8 | API first | PASS — best-config contract specified before storage write details |
| 9 | Overengineering | PASS — thin score path + persist + query; no plugin system |
| 10 | Artifact paths | PASS — theme-folder paths + `scripts/ci/quality-gates.sh` |

### Session Metrics

| Metric | Planning phase | Execution phase |
|--------|---------------|-----------------|
| Model | claude-opus-4-8 / composer (plan refresh) | claude-sonnet-4-6 |
| Tokens — input / output (est.) | — / — | — / — |
| Turns | — | — |
| Context sources loaded | TRAIL, HANDOFF, main HEAD seams | + touched source files |
| Context pressure | none | — |
| Notes | Plan refresh 2026-07-29; MCP deferred — Won't | Invoke via `/nw-execute` |
