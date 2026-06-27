<!-- file: docs/plan/slice-21-sie-skateboard.md -->

## Slice Workflow Header

Slice: 21 — SIE Skateboard — `POST /api/v1/sweep` returns ranked Tier 1 results using SIE (BGE-M3) vs voyage-3.5, logged to Aim

Files:
- pyproject.toml                          # add sie-sdk, aim, tavily-python deps
- server/core/embedder_factory.py         # new: get_embedder(provider) — neutral dispatch table (factory fn, not Protocol)
- server/core/sie_embedder.py             # new: embed_documents_sie / embed_query_sie (plain fns)
- server/core/tavily_corpus.py            # new: fetch_corpus() standalone primitive
- server/core/aim_logger.py              # new: AimLogger.log_run() — no-op on Aim init failure
- server/api/sweep.py                     # new: POST /api/v1/sweep, GET /api/v1/best-config
- server/core/model_registry.py           # add SIE models (bge-m3, stella-v5, splade-v3)
- server/models/config.py                 # add "sie" to Provider enum
- server/core/orchestrator.py             # use get_embedder factory; remove if/elif from embed path
- server/core/embedder.py                 # remove provider-level dispatch; keep Voyage impl only
- server/main.py                          # include sweep_router at /api/v1; extend /health
- tests/test_sie_embedder.py              # GWT tests (mock SIEClient)
- tests/test_tavily_corpus.py             # GWT tests (mock Tavily client)
- tests/test_sweep_endpoint.py            # GWT tests for POST /api/v1/sweep
- tests/test_embedder_factory.py          # factory returns correct fns for voyage/local/sie

Exit criteria:
  [ ] All GWT tests pass (see Spec section below)
  [ ] ./scripts/quality-gates.sh passes — 0 ruff/mypy errors, pytest ≥ 80% coverage, frontend build clean
  [ ] POST /api/v1/sweep returns ranked results for a real topic (manual smoke test)
  [ ] GET /health returns sie="reachable", tavily="reachable", mongodb="connected"
  [ ] Aim UI shows a logged run after sweep completes
  [ ] No prior tests regressed

Commit pattern:
feat(sie): add SIE Skateboard — SIE embeddings, Tavily corpus, Aim logging, /api/v1/sweep

- Wire SIEClient encode for BGE-M3; voyage-3.5 stays as numeric baseline
- Add Tavily corpus builder as standalone primitive
- Add Aim logging wrapper called at every run completion
- New POST /api/v1/sweep and GET /health endpoints

---

## Slice 21 — SIE Skateboard [Must]

### Branch
`slice/21-sie-skateboard`
Create from `main` before any work begins: `git checkout main && git pull && git checkout -b slice/21-sie-skateboard`

### Spec (GWT)

**As a** developer / hackathon evaluator, **I want** to POST a topic to `/api/v1/sweep` and get ranked RAG configs using SIE (BGE-M3) vs voyage-3.5 with every run logged to Aim, **so that** I can compare open-source vs closed-API embedding quality without manual setup.

```
Scenario: SIE BGE-M3 dense embedding
  Given SIEClient is initialised with base_url=http://localhost:8080
  When encode(model="bge-m3", inputs=["test query"]) is called
  Then a list containing one 1024-dim float vector is returned

Scenario: SIE encode falls back gracefully when SIE is unreachable
  Given SIEClient cannot connect to http://localhost:8080
  When encode is called
  Then a RuntimeError is raised with message containing "SIE unreachable"

Scenario: Tavily corpus builder returns text chunks
  Given TAVILY_API_KEY is set and Tavily API is reachable
  When fetch_corpus(topic="machine learning embeddings", max_results=5) is called
  Then a non-empty list of strings (text chunks) is returned, each non-empty

Scenario: Tavily corpus builder raises on missing API key
  Given TAVILY_API_KEY is not set in env
  When fetch_corpus is called
  Then a ValueError is raised with message containing "TAVILY_API_KEY"

Scenario: POST /api/v1/sweep — Tier 1 sweep with SIE BGE-M3
  Given SIE running, Tavily reachable, MongoDB connected
  When POST /api/v1/sweep {"topic":"AI agents","retrieval_methods":["dense","bm25","hybrid-rrf"],"embedding_model":"bge-m3"}
  Then HTTP 200 with body containing best_config.retrieval_method, best_config.score, results (list ≥ 1 item), experiment_id (uuid), corpus_source="tavily"

Scenario: POST /api/v1/sweep — defaults to BGE-M3 when embedding_model omitted
  Given a valid sweep request with no embedding_model field
  When POST /api/v1/sweep {"topic":"AI agents"}
  Then HTTP 200 and best_config.embedding_model is "bge-m3"

Scenario: GET /health — enhanced to include SIE and Tavily
  Given SIE running at :8080, Tavily reachable, MongoDB connected
  When GET /health
  Then HTTP 200 with {"status":"ok","mongodb":"connected","tavily":"reachable","sie":"reachable","version":"<semver>"}

Scenario: Aim logging on sweep run completion
  Given a sweep run completes (pass or fail)
  When the run finishes
  Then an Aim Run exists with params: model_name, model_source ("sie"|"voyage"), retrieval_method, score, latency_ms, topic, experiment_id
```

### Before-Checks [GATE — slice is BLOCKED until all pass]

- [ ] Branch `slice/21-sie-skateboard` created from latest `main` and checked out
- [ ] Conventional Commits format confirmed: `feat(sie): ...` — write WHY not WHAT; no Co-authored-by
- [ ] Previous slice gate status is PASSED (Slice 20 — Toolchain hardening ✅)
- [ ] SIE Docker running: `docker run -p 8080:8080 -v sie-hf-cache:/app/.cache/huggingface -e HF_TOKEN=$HF_TOKEN ghcr.io/superlinked/sie-server:latest-cpu-default`
- [ ] `curl http://localhost:8080/health` returns ok (wait for model warm-up)
- [ ] `TAVILY_API_KEY` present in `.env`
- [ ] `HF_TOKEN` present in `.env`
- [ ] All existing quality gates pass: `./scripts/quality-gates.sh`
- [ ] Divergence gate: no conflicts detected (confirmed in GAP_ANALYSIS.md — all PCTO additions are additive)

### TDD Execution

1. Write failing tests in `tests/test_sie_embedder.py`, `tests/test_tavily_corpus.py`, `tests/test_sweep_endpoint.py` derived from each GWT scenario above. Mock `SIEClient` and `TavilyClient` at the boundary.
2. Run `uv run pytest tests/test_sie_embedder.py tests/test_tavily_corpus.py tests/test_sweep_endpoint.py` — confirm RED.
3. Implement minimum code to pass — GREEN.
4. Refactor: extract shared fixtures, remove duplication, confirm composability.
5. Run full suite `uv run pytest --tb=short -q` — confirm no regressions.

### Implementation Steps

1. **Add dependencies** to `pyproject.toml`: `sie-sdk>=0.1`, `aim>=3.0`, `tavily-python>=0.3`
2. **Add SIE models to registry** (`server/core/model_registry.py`):
   - `bge-m3`: provider=`sie`, dims=1024, type=dense+sparse+multi-vector
   - `stella-v5`: provider=`sie`, dims=1024, type=dense
   - `splade-v3`: provider=`sie`, sparse=True
3. **Add `"sie"` to Provider enum** in `server/models/config.py`
4. **Write `server/core/sie_embedder.py`** — thin wrapper: `SIEEmbedder(base_url).encode(model, texts) -> list[list[float]]`; raises `RuntimeError` on connection failure
5. **Write `server/core/tavily_corpus.py`** — `fetch_corpus(topic, max_results) -> list[str]`; raises `ValueError` if `TAVILY_API_KEY` missing
6. **Write `server/core/aim_logger.py`** — `AimLogger.log_run(run_params: dict)`; no-op if Aim init fails (graceful degradation)
7. **Update `server/core/orchestrator.py`**: dispatch `sie` provider to `SIEEmbedder`; call `aim_logger.log_run()` at each run completion
8. **Write `server/api/sweep.py`**: `POST /api/v1/sweep` (calls orchestrator with Tavily corpus or provided document); `GET /api/v1/best-config?task=...` (queries MongoDB sweep history)
9. **Update `server/main.py`**: include `sweep_router` at prefix `/api/v1`; extend `/health` to probe `http://localhost:8080/health` (SIE) and Tavily reachability
10. **Write tests** for all GWT scenarios (mock SIEClient, TavilyClient)
11. **Run `./scripts/quality-gates.sh`** — fix any ruff/mypy/coverage failures

### After-Checks [GATE — next slice is BLOCKED until all pass]

- [ ] All GWT scenarios covered by passing named tests
- [ ] No skipped tests in scope
- [ ] Stub scan: no `TODO`, `FIXME`, `NotImplemented`, bare `pass` in new files
- [ ] Full test suite green, ≥ 80% coverage on scoped modules
- [ ] Build clean: 0 ruff errors, 0 mypy errors, frontend build passes
- [ ] Smoke test: `curl -X POST http://localhost:8001/api/v1/sweep -H "Content-Type: application/json" -d '{"topic":"machine learning"}'` → HTTP 200 with ranked results
- [ ] `GET /health` returns SIE + Tavily status
- [ ] Aim UI (`aim up`) shows at least one logged run
- [ ] Doc audit → YES: update `docs/slices/PROGRESS.md` (Slice 21 → ✅ COMPLETE); update `CLAUDE.md` Key Files table with new files
- [ ] Security audit → NO (no auth, no external user input reaching shell/DB directly; Tavily topic is URL-encoded by SDK)
- [ ] Self-review: read `git diff main` before requesting review
- [ ] Run `/clean-commit` then push branch; open PR via `/create-pr`
- [ ] `docs/slices/PROGRESS.md` updated: Slice 21 → ✅ COMPLETE

### Gate Status
PENDING

### Expected Outcomes

- `POST /api/v1/sweep` returns ranked Tier 1 results comparing SIE BGE-M3 vs voyage-3.5 using live Tavily content
- Every run logged to Aim with full model provenance
- `GET /health` is a first-class observability endpoint including SIE + Tavily
- All primitives (`sie_embedder`, `tavily_corpus`, `aim_logger`) independently testable and composable

### Session Metrics

| Metric | Planning phase | Execution phase |
|--------|---------------|-----------------|
| Model | claude-sonnet-4-6 | claude-sonnet-4-6 |
| Tokens — input / output (est.) | — / — | — / — |
| Turns | — | — |
| Context sources loaded | TRAIL.md, PCTO doc, PROGRESS.md | + touched source files, tests |
| Context pressure | none | — |
| Notes | — | — |
