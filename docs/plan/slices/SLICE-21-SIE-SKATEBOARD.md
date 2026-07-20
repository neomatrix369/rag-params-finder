<!-- file: docs/plan/slices/SLICE-21-SIE-SKATEBOARD.md -->

## Slice Workflow Header

Slice: 21 — SIE Skateboard — `POST /api/v1/sweep` returns ranked Tier 1 results using SIE (BGE-M3), logged to Aim

Files:

- pyproject.toml                          # add sie-sdk, aim deps
- server/core/embedder_factory.py         # new: get_embedder(provider) — neutral dispatch table (factory fn)
- server/core/sie_embedder.py             # new: embed_documents_sie / embed_query_sie (plain fns)
- server/core/aim_logger.py              # new: AimLogger.log_run() — no-op on Aim init failure
- server/api/sweep.py                     # new: POST /api/v1/sweep, GET /api/v1/best-config
- server/core/model_registry.py           # add SIE models (bge-m3, stella-v5, splade-v3)
- server/models/config.py                 # add "sie" to Provider enum
- server/core/orchestrator.py             # use get_embedder factory; remove if/elif from embed path
- server/core/embedder.py                 # remove provider-level dispatch; keep Voyage impl only
- server/main.py                          # include sweep_router at /api/v1; extend /health
- tests/test_sie_embedder.py              # GWT tests (mock SIEClient)
- tests/test_sweep_endpoint.py            # GWT tests for POST /api/v1/sweep
- tests/test_embedder_factory.py          # factory returns correct fns for voyage/local/sie
- configs/example-mongodb-sie.yaml        # CLI full-pipeline sweep (provider sie; bge-m3, stella-v5, splade-v3)
- tests/test_config_examples.py             # validates example YAML loads and expands
- docs/user-guide/sie-setup.md              # link to config file; models: schema

Exit criteria:

- [ ] All GWT tests pass (see Spec section below)
- [ ] ./scripts/quality-gates.sh passes — 0 ruff/mypy errors, pytest ≥ 80% coverage, frontend build clean
- [ ] POST /api/v1/sweep returns ranked results for a caller-supplied corpus (manual smoke test)
- [ ] GET /health returns sie status, mongodb status, and version
- [ ] Aim UI shows a logged run after sweep completes
- [ ] No prior tests regressed
- [ ] `configs/example-mongodb-sie.yaml` loads via CLI config loader without validation errors
- [ ] `rag-params-finder run --config configs/example-mongodb-sie.yaml` documented as full-pipeline SIE path (manual smoke when SIE warm)

Commit pattern:
feat(sie): add SIE Skateboard — SIE embeddings, Aim logging, /api/v1/sweep

- Wire SIEClient encode for BGE-M3; caller supplies corpus via `corpus: list[str]` field
- Add Aim logging wrapper called at every run completion
- New POST /api/v1/sweep and GET /health endpoints

---

## Slice 21 — SIE Skateboard [Must]

### Branch

`slice/21-sie-skateboard`
Create from `main` before any work begins: `git checkout main && git pull && git checkout -b slice/21-sie-skateboard`

### Spec (GWT)

**As a** developer / hackathon evaluator, **I want** to POST a topic and corpus to `/api/v1/sweep` and get ranked RAG configs using SIE (BGE-M3) with every run logged to Aim, **so that** I can compare open-source embedding quality without manual setup.

```
Scenario: SIE BGE-M3 dense embedding
  Given SIEClient is initialised with base_url=http://localhost:8720
  When encode(model="bge-m3", inputs=["test query"]) is called
  Then a list containing one 1024-dim float vector is returned

Scenario: SIE encode falls back gracefully when SIE is unreachable
  Given SIEClient cannot connect to http://localhost:8720
  When encode is called
  Then a RuntimeError is raised with message containing "SIE unreachable"

Scenario: POST /api/v1/sweep — Tier 1 sweep with SIE BGE-M3
  Given SIE running, MongoDB connected, and a pre-fetched corpus provided
  When POST /api/v1/sweep {"topic":"AI agents","retrieval_methods":["dense","bm25","hybrid-rrf"],"embedding_model":"bge-m3","corpus":["chunk one","chunk two"]}
  Then HTTP 200 with body containing best_config.retrieval_method, best_config.score, results (list ≥ 1 item), experiment_id (uuid), corpus_source="provided"

Scenario: POST /api/v1/sweep — defaults to BGE-M3 when embedding_model omitted
  Given a valid sweep request with no embedding_model field
  When POST /api/v1/sweep {"topic":"AI agents"}
  Then HTTP 200 and best_config.embedding_model is "bge-m3"

Scenario: POST /api/v1/sweep — falls back to topic string when no corpus supplied
  Given a sweep request with no corpus field
  When POST /api/v1/sweep {"topic":"machine learning"}
  Then HTTP 200 and corpus_source="topic"

Scenario: GET /health — enhanced to include SIE status and version
  Given SIE running at :8720, MongoDB connected
  When GET /health
  Then HTTP 200 with {"status":"ok","mongodb":"connected","sie":"reachable","version":"<semver>"}

Scenario: Aim logging on sweep run completion
  Given a sweep run completes (pass or fail)
  When the run finishes
  Then an Aim Run exists with params: model_name, model_source ("sie"|"voyage"), retrieval_method, score, latency_ms, topic, experiment_id

Scenario: example-mongodb-sie.yaml loads and expands sweep for SIE provider
  Given configs/example-mongodb-sie.yaml exists
  When load_config() and ExperimentConfig.model_validate() are called
  Then embedding.provider is "sie", models includes bge-m3/stella-v5/splade-v3, and expand_sweep() yields 120 runs
  And required_search_indexes() includes vector_index_1024, vector_index_30522, and text_search_index
```

### Before-Checks [GATE — slice is BLOCKED until all pass]

- [ ] Branch `slice/21-sie-skateboard` created from latest `main` and checked out
- [ ] Conventional Commits format confirmed: `feat(sie): ...` — write WHY not WHAT; no Co-authored-by
- [ ] Previous slice gate status is PASSED (Slice 20 — Toolchain hardening ✅)
- [ ] SIE Docker running — see [SIE Provider Setup](../user-guide/sie-setup.md) for the canonical `docker run` command, warm-up polling, and known log messages (503 encode, disk-cache WARNING)
- [ ] SIE **model ready** (not just `/healthz`): encode probe returns HTTP 200 — `curl -sf -o /dev/null -X POST http://localhost:8720/v1/encode/BAAI/bge-m3 -H "Content-Type: application/json" -d '{"items":[{"text":"probe"}]}'`
- [ ] `HF_TOKEN` present in `.env`
- [ ] All existing quality gates pass: `./scripts/quality-gates.sh`
- [ ] Divergence gate: no conflicts detected (confirmed in GAP_ANALYSIS.md — all additions are additive)

### TDD Execution

1. Write failing tests in `tests/test_sie_embedder.py`, `tests/test_sweep_endpoint.py` derived from each GWT scenario above. Mock `SIEClient` at the boundary.
2. Run `uv run pytest tests/test_sie_embedder.py tests/test_sweep_endpoint.py` — confirm RED.
3. Implement minimum code to pass — GREEN.
4. Refactor: extract shared fixtures, remove duplication, confirm composability.
5. Run full suite `uv run pytest --tb=short -q` — confirm no regressions.

### Implementation Steps

1. **Add dependencies** to `pyproject.toml`: `sie-sdk>=0.1`, `aim>=3.0`
2. **Add SIE models to registry** (`server/core/model_registry.py`):
   - `bge-m3`: provider=`sie`, dims=1024, type=dense+sparse+multi-vector
   - `stella-v5`: provider=`sie`, dims=1024, type=dense
   - `splade-v3`: provider=`sie`, sparse=True
3. **Add `"sie"` to Provider enum** in `server/models/config.py`
4. **Write `server/core/sie_embedder.py`** — thin wrapper: `SIEEmbedder(base_url).encode(model, texts) -> list[list[float]]`; raises `RuntimeError` on connection failure
5. **Write `server/core/aim_logger.py`** — `AimLogger.log_run(run_params: dict)`; no-op if Aim init fails (graceful degradation)
6. **Update `server/core/orchestrator.py`**: dispatch `sie` provider via `embedder_factory`; call `aim_logger.log_run()` at each run completion
7. **Write `server/api/sweep.py`**: `POST /api/v1/sweep` accepts `corpus: list[str]` (falls back to topic string when empty); `GET /api/v1/best-config?task=...` (queries MongoDB sweep history)
8. **Update `server/main.py`**: include `sweep_router` at prefix `/api/v1`; extend `/health` to probe `http://localhost:8720/healthz` (SIE) and include version
9. **Write tests** for all GWT scenarios (mock SIEClient)
10. **Run `./scripts/quality-gates.sh`** — fix any ruff/mypy/coverage failures
11. **Add `configs/example-mongodb-sie.yaml`** and cascade doc references (see file list in slice spec)
12. **Add `tests/test_config_examples.py`** — config load + index plan assertions (no SIE Docker in CI)

### After-Checks [GATE — next slice is BLOCKED until all pass]

- [ ] All GWT scenarios covered by passing named tests
- [ ] Specification coverage: every GWT clause has at least one test (BDD/GWT-first); essential error and timeout paths covered
- [ ] Branch coverage: target 100% where practical; document any exclusions
- [ ] Mutation testing run if slice is feature-complete: mutation budget ≤10% survivors
- [ ] No skipped tests in scope
- [ ] Stub scan: no `TODO`, `FIXME`, `NotImplemented`, bare `pass` in new files
- [ ] Full test suite green, ≥ 80% coverage on scoped modules
- [ ] Build clean: 0 ruff errors, 0 mypy errors, frontend build passes
- [ ] Smoke test: `curl -X POST http://localhost:8001/api/v1/sweep -H "Content-Type: application/json" -d '{"topic":"machine learning","corpus":["RAG improves retrieval","vector search scales well"]}'` → HTTP 200 with ranked results
- [ ] `GET /health` returns SIE status and version
- [ ] Aim UI (`./scripts/aim-ui.sh`) shows at least one logged run
- [ ] Doc audit → YES: update `docs/plan/slices/PROGRESS.md` (Slice 21 → ✅ COMPLETE); update `CLAUDE.md` Key Files table with new files; cascade `example-mongodb-sie.yaml` across user guide + config reference
- [ ] Security audit → NO (no auth, no external user input reaching shell/DB directly)
- [ ] Self-review: read `git diff main` before requesting review
- [ ] Run `/clean-commit` then push branch; open PR via `/create-pr`
- [ ] `docs/plan/slices/PROGRESS.md` updated: Slice 21 → ✅ COMPLETE

### Gate Status

✅ COMPLETE

### Expected Outcomes

- `POST /api/v1/sweep` returns ranked Tier 1 results comparing retrieval methods using SIE BGE-M3 embeddings on a caller-supplied corpus
- Every run logged to Aim with full model provenance
- `GET /health` is a first-class observability endpoint including SIE reachability and version
- All primitives (`sie_embedder`, `aim_logger`, `embedder_factory`) independently testable and composable
- Third example config completes **DB × provider** trio: local / voyage / **sie**
- CLI full sweep path documented alongside API skateboard (`POST /api/v1/sweep`)

### Session Metrics

| Metric | Planning phase | Execution phase |
|--------|---------------|-----------------|
| Model | claude-sonnet-4-6 | claude-sonnet-4-6 |
| Tokens — input / output (est.) | — / — | — / — |
| Turns | — | — |
| Context sources loaded | TRAIL.md, PCTO doc, PROGRESS.md | + touched source files, tests |
| Context pressure | none | — |
| Notes | — | — |
