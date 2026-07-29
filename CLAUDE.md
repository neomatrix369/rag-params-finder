# CLAUDE.md

Agent guidance for `rag-params-finder`. Start with `AGENTS.md` → this file → `docs/README.md` → `docs/plan/slices/PROGRESS.md`.

## Project Overview

**rag-params-finder** is a RAG parameter sweep experimentation tool with three components:
1. **Python CLI** — submits experiment configs
2. **FastAPI Server** — orchestrates PDF → chunk → embed → search pipeline
3. **React Dashboard** — visualization and sweep controls (pause, resume, cancel, delete)

Two-process architecture: config submission (CLI) is separate from execution (Server). Dashboard observes and controls active sweeps (pause/resume/cancel/delete).

## Development Commands

### Backend (Python 3.12+)

```bash
# Setup
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
bash scripts/ci/install-git-hooks.sh   # commit + pre-push hooks

# Run server
uvicorn server.main:app --reload --port 8001

# Lint & type check
uv run ruff check .
uv run mypy server/ cli/

# Tests
uv run pytest --tb=short -q

# All quality gates (mirrors CI — repo lint + backend + frontend + audits)
./scripts/ci/quality-gates.sh
bash scripts/ci/repo-lint.sh   # shell + workflows + Markdown only
```

### Frontend (Node.js 22+)

```bash
cd frontend
npm install
npm run dev           # → http://localhost:5374
npm run test
npm run typecheck
npm run build
```

### Docker (optional)

```bash
./start-services.sh                    # server + dashboard (Atlas cloud in .env)
./start-services.sh --mongodb-local    # server + dashboard + MongoDB Atlas Local (no cloud account)
./start-services.sh --postgres-local   # server + dashboard + local pgvector (STORAGE_BACKEND=postgres)
./start-services.sh --postgres-cloud   # hosted Supabase (DATABASE_URL or SUPABASE_URI; no MONGODB_URI)
RAG_MONGODB_LOCAL=1 ./start-services.sh  # same as --mongodb-local via env var
./start-services.sh mongodb [start|stop|reset|status]  # manage local Atlas container standalone
./start-services.sh postgres [start|stop|reset|status]  # manage local pgvector container standalone
./scripts/docker/health-check.sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build  # dev HMR
```

Backend switching — only the start command changes:

| Backend | Connection string (CLI / host server) |
|---------|--------------------------------|
| Atlas cloud | `MONGODB_URI=mongodb+srv://...` (from .env) |
| Atlas Local | `MONGODB_URI=mongodb://localhost:27017/rag_params_finder?directConnection=true` |
| Local pgvector | `STORAGE_BACKEND=postgres` + `DATABASE_URL=postgresql://rag:rag@localhost:5433/rag_params_finder` |
| Hosted Supabase | `STORAGE_BACKEND=postgres` + `DATABASE_URL` (or optional `SUPABASE_URI` alias) — Session-mode pooler |

Host CLI unchanged: `SERVER_URL=http://localhost:8001`. See `docs/plan/slices/03-platform/SLICE-14-DOCKER-COMPOSE.md`, `docs/user-guide/mongodb-setup.md`, and `docs/user-guide/postgres-setup.md`.

### CLI

```bash
rag-params-finder run --config configs/mongodb/example-local.yaml
rag-params-finder run --config configs/mongodb/example-local.yaml --detach
rag-params-finder run --config configs/mongodb/example-sie.yaml   # SIE BGE-M3/Stella/SPLADE — see docs/user-guide/sie-setup.md
rag-params-finder run --config configs/supabase/example-local.yaml  # pgvector — see docs/user-guide/postgres-setup.md
rag-params-finder cancel <experiment-id>
rag-params-finder pause <experiment-id>
rag-params-finder resume <experiment-id>
rag-params-finder delete <experiment-id>           # Delete experiment and all data
rag-params-finder delete <experiment-id> --force   # Skip confirmation
rag-params-finder indexes list                     # Atlas known/unknown OR Postgres PRESENT/MISSING
rag-params-finder indexes reset                    # Atlas only — drop unknown + ensure required
rag-params-finder indexes reset --all              # Atlas only — rebuild all chunks search indexes
rag-params-finder version
```

List/detail: dashboard or `GET /experiments` / `GET /experiments/{id}` (see `http://localhost:8001/docs`).

## Key Files

| File | Purpose |
|---|---|
| `docs/contributor-guide/module-theme-map.md` | Behavior \| Feature \| Function theme map + Slice 45 layout status (hotspots 1–5 IMPLEMENTED) |
| `scripts/ci/` | Quality gates, repo lint, hooks install, pip-audit, coverage floor + threshold-drift checkers |
| `scripts/docker/` | health-check, aim-ui, docker-cleanup/build-context |
| `scripts/release/` | `release.sh` + bump/GitHub helpers |
| `scripts/security/` | `security-scan.sh` |
| `server/main.py` | FastAPI app entry; lifespan ensures DB indexes + orphan reconciliation |
| `server/settings.py` | Centralized pydantic-settings config (`storage_backend`: `mongodb` default permanently — DECISIONS #130 — or `postgres`) |
| `server/db/ports/storage.py` | `StorageBackend` Protocol — experiment/run/chunk/result CRUD + cascade + reconciliation |
| `server/db/ports/retriever_backend.py` | `RetrieverBackend` Protocol — dense/sparse/hybrid search port |
| `server/db/mongo/mongo_store.py` | Mongo adapters for both ports (Atlas / Atlas Local) |
| `server/db/mongo/mongo_stats.py` | Stats / explore / vector-db helpers (delegated by `MongoStorageBackend`) |
| `server/db/ports/stats_common.py` | Backend-agnostic db-stats assembly shared by Mongo and Postgres |
| `server/db/postgres/postgres.py` | Postgres pool, idempotent `schema.sql` bootstrap, query helpers |
| `server/db/postgres/postgres_uri.py` | Supabase vs local-pgvector detection; TLS only for hosted; `postgres_storage_mode()` → `postgres-local` \| `postgres-cloud` |
| `server/db/postgres/postgres_docs.py` | Document ↔ row mapping (promoted columns + `doc` JSONB) |
| `server/db/postgres/postgres_store.py` | Postgres `StorageBackend` impl (Supabase / local pgvector) |
| `server/db/postgres/postgres_stats.py` | Postgres stats / explore helpers (delegated by `PostgresStorageBackend`) |
| `server/db/postgres/schema.sql` | Postgres DDL — 4 tables, FK cascade, `embedding_384` / `embedding_1024` |
| `server/db/ports/store_factory.py` | `get_storage_backend()` / `get_retriever_backend()` from settings |
| `server/core/pipeline/orchestrator.py` | End-to-end pipeline executor; preflight search indexes before sweep |
| `server/core/guards/search_index_plan.py` | Pure logic: required Atlas indexes from config + capacity assessment; required Postgres catalog objects (`vector` extension, HNSW/GIN names) |
| `server/core/guards/search_index_guard.py` | Backend-aware preflight — Atlas snapshot + ensure_indexes retry, or Postgres catalog introspection; raises on mismatch (HTTP 422) |
| `server/core/guards/health_check.py` | `/healthz` storage ping + `resolve_storage_mode()` four-value compound; Postgres error remediation substring |
| `server/core/guards/config_backend_guard.py` | Config↔server engine mismatch 422 (before index/SIE preflight) |
| `scripts/lib/storage_mode.sh` | Four-flag `(db_type, location)` resolver for `start-services.sh` |
| `server/core/pipeline/startup_reconciliation.py` | Mark stale `running` experiments on server boot |
| `server/db/mongo/mongodb_uri.py` | Cloud vs local URI detection (`is_atlas_uri`, `parse_atlas_cluster_name`); `mongodb_storage_mode()` → `mongodb-local` \| `mongodb-cloud` |
| `server/core/atlas_storage.py` | Atlas Admin API cluster quota + tier specs (`resolve_tier_specs`); shared-tier storage fallbacks |
| `server/core/model_registry.py` | Embedding + reranking model catalog |
| `server/core/embedding/embedder_factory.py` | Provider dispatch factory; `get_embedder(provider)` returns `(embed_docs_fn, embed_query_fn)` — add new providers here, not in orchestrator |
| `server/core/embedding/embedder.py` | Voyage embedding client; `voyage-context-3` uses contextualized API with segment splitting; provider dispatch removed to `embedder_factory.py` |
| `server/core/embedding/local_embedder.py` | sentence-transformers embedding (lazy-load) |
| `server/core/embedding/sie_embedder.py` | SIE embeddings (BGE-M3, Stella-v5, SPLADE-v3) via remote gateway or optional self-hosted Docker |
| `server/core/guards/sie_guard.py` | SIE preflight guard — verifies `SIE_ENABLED` and gateway reachability before SIE embedding sweeps |
| `server/core/aim_logger.py` | Aim experiment run logging wrapper; `AimLogger.log_run()` — no-op if Aim init fails |
| `scripts/docker/aim-ui.sh` | Start Aim UI on :43800 via Docker (shared `./.aim` repo with server) |
| `scripts/lib/compose.sh` | Shared Docker Compose helpers + local/cloud MongoDB URI constants; `start-services.sh mongodb` subcommands |
| `server/api/sweep.py` | `POST /api/v1/sweep` (SIE vs voyage baseline; persists Tier-1 history via StorageBackend) + `GET /api/v1/best-config?task=` (Slice 22 **IMPLEMENTED**) |
| `server/core/rerank/reranker.py` | Voyage + local CrossEncoder + SIE `score` dispatch (`bge-reranker`) |
| `server/core/rerank/local_reranker.py` | CrossEncoder reranking (lazy-load) |
| `server/core/retrieval/retriever_mongo.py` | Atlas Vector Search (dense/sparse/hybrid) — Mongo-only |
| `server/core/retrieval/retriever_postgres.py` | pgvector dense + tsvector sparse + RRF hybrid; Atlas-scale dense scores; mandatory `embedding_model` filter |
| `server/models/config.py` | Pydantic experiment config + provider validators |
| `server/models/enums.py` | ChunkingMethod, RetrievalMethod, Phase |
| `server/api/experiments.py` | Experiments CRUD, results/explore, db-stats, pause, resume, cancel, delete |
| `server/api/experiments_lifecycle.py` | Bayesian summary + stale RUNNING reconciliation helpers (Slice 45) |
| `server/api/experiments_shared.py` | Thin API helpers — delegates all I/O to `StorageBackend` via store_factory |
| `server/db/mongo/indexes.py` | Collection + search index creation; cluster-wide index listing |
| `cli/main.py` | Typer app (`run`, `cancel`, `pause`, `resume`, `delete`, `indexes`, `version`) |
| `cli/display.py` | CLI live watch table + experiment summary panel (Slice 45) |
| `cli/indexes_cmd.py` | `indexes list` (Atlas or Postgres catalog) and `indexes reset` (Atlas-only) subcommands |
| `cli/config_loader.py` | YAML parser + model registry validation |
| `cli/api_client.py` | HTTP client to server (POST /experiments, DELETE, etc.) |
| `frontend/src/App.tsx` | Root component (screen routing) |
| `frontend/src/components/screens/` | Feature screens (`Experiments`, `Detail`, `SearchExplorer`) + co-located tests |
| `frontend/src/components/chrome/` | Shell chrome (`DashboardShell`, `AppPageChrome`, `Pagination`, `CollapsibleCard`, …) |
| `frontend/src/components/experiment/` | Experiment controls/progress/modals + detail chrome |
| `frontend/src/components/stats/` | Vector DB stats panels + `StatTile`/`StatRow` |
| `frontend/src/hooks/useExperimentDetail.ts` | Detail hydrate/poll/db-stats controller (Slice 45) |
| `frontend/src/test/helpers/` | Shared Vitest builders (`experiments`, `vectorDbStats`, `explore`, `experimentDetail`) |
| `frontend/src/components/explore/ExplorePanels.tsx` | Search Explorer tabs + sidebar panels |
| `frontend/src/utils/experimentStatus.ts` | Run outcome summarization + terminal status helpers |
| `frontend/src/utils/completionReason.ts` | Shared `completion_reason` → label mapping |
| `frontend/src/utils/feedEntries.ts` | Shared loading-feed append helper |
| `frontend/src/types/index.ts` | Hand-mirrored TypeScript types from Python models |
| `frontend/src/services/apiClient.ts` | Fetch wrapper (all server API calls, including DELETE) |
| `frontend/src/services/fetchWithProgress.ts` | ReadableStream-based fetch with progress tracking |
| `frontend/src/utils/devLog.ts` | Dev-only scoped console helpers (stripped from production builds) |
| `server/utils/scope_log.py` | Option A scoped log format for server and CLI |
| `tests/server/core/guards/test_search_index_plan.py` | Search index requirement + capacity scenario tests |
| `tests/server/core/guards/test_search_index_guard.py` | Preflight guard tests (mocked I/O) |
| `tests/server/db/test_postgres_store_integration.py` | Postgres CRUD/cascade/stats against live pgvector (skips without a DB) |

## Provider System

**Two independent provider settings**:
- `embedding.provider`: "local", "voyage", or "sie"
  - Local → `server/core/embedding/local_embedder.py` → `all-MiniLM-L6-v2` (384-dim)
  - Voyage → `server/core/embedding/embedder.py` → all models in `EMBEDDING_MODELS` with `provider: voyage` (1024-dim; `voyage-context-3` uses `contextualized_embed()` with automatic segment splitting for long documents)
  - SIE → `server/core/embedding/sie_embedder.py` → BGE-M3, Stella-v5 (1024-dim dense), SPLADE-v3 (30522-dim sparse); **opt-in** — remote gateway via `SIE_ENDPOINT` + `SIE_API_KEY` (no Docker), or self-hosted Docker fallback (`docs/user-guide/sie-setup.md`)
  - Dispatch: `server/core/embedding/embedder_factory.py` — `get_embedder(provider)` returns the right functions; orchestrator never does if/elif on provider
- **`retrieval.retrievers`** (unified format):
  - Each list entry is one sweep dimension — one retriever per run
  - Traditional: `{type: dense|sparse|hybrid}` — no provider/model needed
  - Rerankers: `{type: reranker|cross_encoder, provider: local|voyage, model: ...}`
  - Example:
    ```yaml
    retrieval:
      retrievers:
        - type: dense
        - type: cross_encoder
          provider: local
          model: cross-encoder/ms-marco-MiniLM-L-6-v2
    ```
    → creates separate runs for dense and cross_encoder (not a pipeline)

**Old format** (deprecated, auto-migrated):
- `retrieval.methods` + `retrieval_provider`/`retrieval_model` — still works but converts to `retrievers` internally

Provider/model must match — registry in `model_registry.py` validates at config load time.

## MongoDB Atlas Collections

| Collection | Purpose | Key Index |
|---|---|---|
| `chunks` | Text chunks + embeddings | Vector index on `embedding` (384 or 1024-dim cosine) + filters |
| `experiments` | Experiment metadata | `created_at`, `status` |
| `run_status` | Per-run phase tracking | `experiment_id`, `phase` |
| `results` | Query results (top-K chunks) | `experiment_id`, `query_id` |

**Critical**: always filter vector search by `embedding_model` — incompatible vectors must not be mixed.

## Slice Execution Playbook

### Pre-slice checklist
```
[ ] Read docs/plan/slices/PROGRESS.md — confirm current state and which slice is next
[ ] Read or create the slice spec in docs/plan/slices/0N-<theme>/SLICE-XX-*.md
[ ] bash scripts/ci/install-git-hooks.sh (once per machine — commit + pre-push checks)
[ ] Run all quality gates — confirm zero regressions before starting
[ ] Note the exact acceptance criteria — these are the exit conditions
```

### Decision log template
Record every non-obvious choice in `docs/plan/slices/PROGRESS.md` → Decision Log:
```
| <date> | <slice> | <decision> | <why> |
```

### Verify-all commands (run before each commit)
```bash
# One command — mirrors CI (repo lint is step 1; unit-tier pytest only)
./scripts/ci/quality-gates.sh

# Repo lint only (shell + workflows + Markdown)
bash scripts/ci/repo-lint.sh

# Or individually (same unit ignores as quality-gates / CI backend):
uv run ruff check .
uv run mypy server/ cli/
uv run pytest --tb=short -q \
  --ignore=tests/contract \
  --ignore=tests/server/db/test_postgres_store_integration.py \
  --ignore=tests/server/db/test_postgres_dense_retrieval.py \
  --ignore=tests/server/db/test_postgres_sparse_hybrid.py \
  -m "not integration" \
  --cov=server.core.guards.search_index_plan \
  --cov=server.core.guards.search_index_guard --cov=server.core.results_analyzer \
  --cov=server.models.config --cov-fail-under=95
cd frontend && npm run lint && npm run test && npm run typecheck && npm run build
```

### Post-slice checklist
```
[ ] All acceptance criteria checked ✅
[ ] Quality gates pass (zero regressions) — ./scripts/ci/quality-gates.sh; git push runs pre-push-gates (full local gates) when hooks installed
[ ] Slice status updated in docs/plan/slices/PROGRESS.md (🔨 → ✅ COMPLETE)
[ ] Decisions logged in PROGRESS.md Decision Log
[ ] Committed with a short, specific message
[ ] Consider release: ./scripts/release/release.sh minor (slices/features) or patch (fixes/polish)
    Creates release/vX.Y.Z + PR — never push the bump to main; tag after merge
    See PROGRESS.md § Release Cadence for guidance
```

## Quality Gates Baseline

**Unified script:** `./scripts/ci/quality-gates.sh` (mirrors CI — 11 steps including repo lint)

**Git hooks** (after `bash scripts/ci/install-git-hooks.sh`):
- **commit** → pre-commit (hygiene, gitleaks, repo lint, ruff, dmypy, bandit, eslint, tsc --noEmit, testmon fast-tests on changed modules)
- **push** → push-specific only (`./scripts/ci/pre-push-gates.sh` — full pytest+coverage, vite build, vitest, pip-audit, npm audit; no duplicate of commit checks)

**Repo lint** (2026-05-27):
- `bash scripts/ci/repo-lint.sh` → shellcheck + actionlint + markdownlint pass

**Repo lint** shellcheck scope: `start-services.sh` + `scripts/**/*.sh` (pre-commit `files: ^(start-services\.sh|scripts/.*\.sh)$`).

**Backend** (2026-07-28 — unit tier):
- `ruff check .` → 0 errors
- `mypy server/ cli/` → 0 errors
- `pytest` (ignores live contract/postgres suites, `-m "not integration"`) → **338** tests; BE floors **95/90/n/a/95** (stmts/br/fn/lines) via `fail_under=95` + `scripts/ci/check_backend_coverage_floors.py` — DECISIONS #142; no `MONGODB_URI` required
- FE/BE threshold lock: `scripts/ci/check_coverage_threshold_drift.py` asserts Vitest `coverage.thresholds` match `[tool.rag_params_finder.coverage_thresholds]` (incl. `functions=95`) — DECISIONS #161

**Frontend** (2026-07-28 — Slice 45 COMPLETE + floors #142):
- `npm run lint` → 0 errors (eslint + security plugin)
- `npm run test` → **261** tests across **24** files (Vitest + React Testing Library)
- `npm run test:coverage` / `test:ci` → v8 thresholds **95/90/95/95** stmts/br/fn/lines (`all: true`; DECISIONS #142); measured ≈98.4% / 93.11% / 100% / 99.69% — wired into `quality-gates.sh`, `pre-push-gates.sh`, and CI frontend job (**VERIFIED**)
- `npm run typecheck` → 0 errors
- `npm run build` → ✓ built in ~4s
- `npm audit --audit-level=high` → 0 high vulnerabilities
- Theme map + Slice 45 layout — hotspots 1–5 **IMPLEMENTED** (incl. `scripts/{ci,docker,release,security}/`); Gate Status ✅ — [`docs/plan/gate-evidence/slice-45.json`](docs/plan/gate-evidence/slice-45.json)

## Release Process

See [docs/contributor-guide/release-process.md](docs/contributor-guide/release-process.md) for the complete release workflow.

**Quick reference**:
```bash
# From clean main — creates release/vX.Y.Z, opens PR (does not push main)
./scripts/release/release.sh minor

# Patch release (bug fixes, polish)
./scripts/release/release.sh patch

# After the PR merges: tag + GitHub release on main (see release-process.md §4)
rag-params-finder version
```

The project follows [Semantic Versioning](https://semver.org/). `scripts/release/release.sh` bumps versions on a `release/vX.Y.Z` branch and opens a PR to `main`; tag and GitHub release happen **after** merge. Never push a version bump directly to `main`.

## Further Reading

| Doc | Audience | Purpose |
|---|---|---|
| `docs/user-guide/getting-started.md` | End users | Setup, first experiment |
| `docs/user-guide/configuration.md` | End users | Full config reference |
| `docs/contributor-guide/architecture.md` | Contributors | System design, modules, data flow |
| `docs/contributor-guide/module-theme-map.md` | Contributors / agents | Behavior \| Feature \| Function taxonomy; Slice 45 layout status (hotspots 1–5 IMPLEMENTED) |
| `docs/contributor-guide/extending.md` | Contributors | Adding models, chunkers, endpoints |
| `docs/contributor-guide/development.md` | Contributors | Dev loop, quality gates |
| `docs/contributor-guide/release-process.md` | Contributors | Creating releases, versioning strategy |
| `docs/plan/slices/PROGRESS.md` | Agents | Slice status, decision log, roadmap |
| `docs/plan/slices/README.md` | Agents / contributors | Theme folder index (`01`–`07`); specs under `0N-<theme>/` (#162) |
| `docs/README.md` | All | Documentation index (personas, topics, tasks) |
| `docs/adr/` | All | Architecture Decision Records |

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
| ------ | ---------- |
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
