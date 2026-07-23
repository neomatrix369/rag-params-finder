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
bash scripts/install-git-hooks.sh   # commit + pre-push hooks

# Run server
uvicorn server.main:app --reload --port 8001

# Lint & type check
uv run ruff check .
uv run mypy server/ cli/

# Tests
uv run pytest --tb=short -q

# All quality gates (mirrors CI — repo lint + backend + frontend + audits)
./scripts/quality-gates.sh
bash scripts/repo-lint.sh   # shell + workflows + Markdown only
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
./start-services.sh --local            # server + dashboard + MongoDB Atlas Local (no cloud account)
RAG_LOCAL_ATLAS=1 ./start-services.sh  # same as --local via env var
./start-services.sh mongodb [start|stop|reset|status]  # manage local Atlas container standalone
./scripts/health-check.sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build  # dev HMR
```

Backend switching — only the start command changes:

| Backend | MONGODB_URI (CLI / host server) |
|---------|--------------------------------|
| Atlas cloud | `mongodb+srv://...` (from .env) |
| Atlas Local | `mongodb://localhost:27017/rag_params_finder?directConnection=true` |

Host CLI unchanged: `SERVER_URL=http://localhost:8001`. See `docs/plan/slices/SLICE-14-DOCKER-COMPOSE.md` and `docs/user-guide/mongodb-setup.md`.

### CLI

```bash
rag-params-finder run --config configs/example-mongodb-local.yaml
rag-params-finder run --config configs/example-mongodb-local.yaml --detach
rag-params-finder run --config configs/example-mongodb-sie.yaml   # SIE BGE-M3/Stella/SPLADE — see docs/user-guide/sie-setup.md
rag-params-finder cancel <experiment-id>
rag-params-finder pause <experiment-id>
rag-params-finder resume <experiment-id>
rag-params-finder delete <experiment-id>           # Delete experiment and all data
rag-params-finder delete <experiment-id> --force   # Skip confirmation
rag-params-finder indexes list                     # Atlas Search indexes (known vs unknown)
rag-params-finder indexes reset                    # Drop unknown indexes + ensure required
rag-params-finder indexes reset --all              # Drop all chunks indexes + recreate
rag-params-finder version
```

List/detail: dashboard or `GET /experiments` / `GET /experiments/{id}` (see `http://localhost:8001/docs`).

## Key Files

| File | Purpose |
|---|---|
| `server/main.py` | FastAPI app entry; lifespan ensures DB indexes + orphan reconciliation |
| `server/settings.py` | Centralized pydantic-settings config |
| `server/core/orchestrator.py` | End-to-end pipeline executor; preflight search indexes before sweep |
| `server/core/search_index_plan.py` | Pure logic: required indexes from config, capacity assessment |
| `server/core/search_index_guard.py` | Cluster snapshot + ensure_indexes retry; raises on mismatch |
| `server/core/startup_reconciliation.py` | Mark stale `running` experiments on server boot |
| `server/db/mongodb_uri.py` | Cloud vs local URI detection (`is_atlas_uri`, `parse_atlas_cluster_name`) |
| `server/core/atlas_storage.py` | Atlas Admin API cluster quota + tier specs (`resolve_tier_specs`); shared-tier storage fallbacks |
| `server/core/model_registry.py` | Embedding + reranking model catalog |
| `server/core/embedder_factory.py` | Provider dispatch factory; `get_embedder(provider)` returns `(embed_docs_fn, embed_query_fn)` — add new providers here, not in orchestrator |
| `server/core/embedder.py` | Voyage embedding client; `voyage-context-3` uses contextualized API with segment splitting; provider dispatch removed to `embedder_factory.py` |
| `server/core/local_embedder.py` | sentence-transformers embedding (lazy-load) |
| `server/core/sie_embedder.py` | SIE embeddings (BGE-M3, Stella-v5, SPLADE-v3) via remote gateway or optional self-hosted Docker |
| `server/core/sie_guard.py` | SIE preflight guard — verifies `SIE_ENABLED` and gateway reachability before SIE embedding sweeps |
| `server/core/aim_logger.py` | Aim experiment run logging wrapper; `AimLogger.log_run()` — no-op if Aim init fails |
| `scripts/aim-ui.sh` | Start Aim UI on :43800 via Docker (shared `./.aim` repo with server) |
| `scripts/lib/compose.sh` | Shared Docker Compose helpers + local/cloud MongoDB URI constants; `start-services.sh mongodb` subcommands |
| `server/api/sweep.py` | `POST /api/v1/sweep` (ranked results, SIE vs voyage baseline) + `GET /api/v1/best-config` |
| `server/core/reranker.py` | Voyage reranking client |
| `server/core/local_reranker.py` | CrossEncoder reranking (lazy-load) |
| `server/core/retriever.py` | Atlas Vector Search (dense/sparse/hybrid) |
| `server/models/config.py` | Pydantic experiment config + provider validators |
| `server/models/enums.py` | ChunkingMethod, RetrievalMethod, Phase |
| `server/api/experiments.py` | Experiments CRUD, results/explore, db-stats, pause, resume, cancel, delete |
| `server/api/experiments_shared.py` | Shared Mongo helpers (delete cascade, db-stats aggregation) |
| `server/db/indexes.py` | Collection + search index creation; cluster-wide index listing |
| `cli/main.py` | Typer app (`run`, `cancel`, `pause`, `resume`, `delete`, `indexes`, `version`) |
| `cli/indexes_cmd.py` | `indexes list` and `indexes reset` subcommands |
| `cli/config_loader.py` | YAML parser + model registry validation |
| `cli/api_client.py` | HTTP client to server (POST /experiments, DELETE, etc.) |
| `frontend/src/App.tsx` | Root component (screen routing) |
| `frontend/src/components/DashboardShell.tsx` | Shared header and navigation wrapper |
| `frontend/src/components/AppPageChrome.tsx` | Shared page wrapper (title, back button, actions) |
| `frontend/src/components/LoadingFeedbackPanel.tsx` | Network loading progress panel with byte-level tracking |
| `frontend/src/components/ExperimentProgressCard.tsx` | Reusable experiment progress card with circular indicator |
| `frontend/src/components/PollingIndicator.tsx` | Subtle "Syncing..." badge during background polls |
| `frontend/src/components/ConfirmDeleteModal.tsx` | Delete confirmation modal with experiment details and stats |
| `frontend/src/components/ExperimentControlButtons.tsx` | Pause, resume, cancel buttons on detail screen |
| `frontend/src/components/ExperimentsScreen.tsx` | Experiments list with collapsible rows, vector DB stats, delete |
| `frontend/src/components/ExperimentDetailScreen.tsx` | Detail view with overview metrics, outcome banners, runs table |
| `frontend/src/components/VectorDbStatsPanel.tsx` | Cluster-grouped storage stats panel |
| `frontend/src/components/CollapsibleCard.tsx` | Reusable collapsible section (localStorage persistence) |
| `frontend/src/utils/experimentStatus.ts` | Run outcome summarization + terminal status helpers |
| `frontend/src/types/index.ts` | Hand-mirrored TypeScript types from Python models |
| `frontend/src/services/apiClient.ts` | Fetch wrapper (all server API calls, including DELETE) |
| `frontend/src/services/fetchWithProgress.ts` | ReadableStream-based fetch with progress tracking |
| `frontend/src/utils/devLog.ts` | Dev-only scoped console helpers (stripped from production builds) |
| `server/utils/scope_log.py` | Option A scoped log format for server and CLI |
| `tests/test_search_index_plan.py` | Search index requirement + capacity scenario tests |
| `tests/test_search_index_guard.py` | Preflight guard tests (mocked I/O) |

## Provider System

**Two independent provider settings**:
- `embedding.provider`: "local", "voyage", or "sie"
  - Local → `server/core/local_embedder.py` → `all-MiniLM-L6-v2` (384-dim)
  - Voyage → `server/core/embedder.py` → all models in `EMBEDDING_MODELS` with `provider: voyage` (1024-dim; `voyage-context-3` uses `contextualized_embed()` with automatic segment splitting for long documents)
  - SIE → `server/core/sie_embedder.py` → BGE-M3, Stella-v5 (1024-dim dense), SPLADE-v3 (30522-dim sparse); **opt-in** — remote gateway via `SIE_ENDPOINT` + `SIE_API_KEY` (no Docker), or self-hosted Docker fallback (`docs/user-guide/sie-setup.md`)
  - Dispatch: `server/core/embedder_factory.py` — `get_embedder(provider)` returns the right functions; orchestrator never does if/elif on provider
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
[ ] Read or create the slice spec in docs/plan/slices/SLICE-XX-*.md
[ ] bash scripts/install-git-hooks.sh (once per machine — commit + pre-push checks)
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
# One command — mirrors CI (repo lint is step 1)
./scripts/quality-gates.sh

# Repo lint only (shell + workflows + Markdown)
bash scripts/repo-lint.sh

# Or individually:
uv run ruff check .
uv run mypy server/ cli/
uv run pytest --tb=short -q --cov=server.core.search_index_plan \
  --cov=server.core.search_index_guard --cov=server.core.results_analyzer \
  --cov=server.models.config --cov-fail-under=80
cd frontend && npm run lint && npm run test && npm run typecheck && npm run build
```

### Post-slice checklist
```
[ ] All acceptance criteria checked ✅
[ ] Quality gates pass (zero regressions) — ./scripts/quality-gates.sh; git push runs pre-push-gates (full local gates) when hooks installed
[ ] Slice status updated in docs/plan/slices/PROGRESS.md (🔨 → ✅ COMPLETE)
[ ] Decisions logged in PROGRESS.md Decision Log
[ ] Committed with a short, specific message
[ ] Consider release: ./scripts/release.sh minor (slices/features) or patch (fixes/polish)
    See PROGRESS.md § Release Cadence for guidance
```

## Quality Gates Baseline

**Unified script:** `./scripts/quality-gates.sh` (mirrors CI — 11 steps including repo lint)

**Git hooks** (after `bash scripts/install-git-hooks.sh`):
- **commit** → pre-commit (staged-file lint)
- **push** → full local gates (`./scripts/pre-push-gates.sh` — lint + type checks, coverage, frontend tests/typecheck/build, scoped SCA, gitleaks)

**Repo lint** (2026-05-27):
- `bash scripts/repo-lint.sh` → shellcheck + actionlint + markdownlint pass

**Backend** (2026-05-27):
- `ruff check .` → 0 errors
- `mypy server/ cli/` → 0 errors
- `pytest` → 183 tests, coverage on scoped modules (80% threshold)

**Frontend** (2026-07-19):
- `npm run lint` → 0 errors (eslint + security plugin)
- `npm run test` → 7 component scenarios pass (Vitest + React Testing Library)
- `npm run typecheck` → 0 errors
- `npm run build` → ✓ built in ~4s, 49 modules
- `npm audit --audit-level=high` → 0 high vulnerabilities

## Release Process

See [docs/contributor-guide/release-process.md](docs/contributor-guide/release-process.md) for the complete release workflow.

**Quick reference**:
```bash
# Create a new release (minor version bump for new slices/features)
./scripts/release.sh minor

# Create a patch release (bug fixes, polish)
./scripts/release.sh patch

# Check current version
rag-params-finder version
```

The project follows [Semantic Versioning](https://semver.org/). Release automation via `scripts/release.sh` handles version updates, CHANGELOG.md updates, git tagging, and optional GitHub release creation.

## Further Reading

| Doc | Audience | Purpose |
|---|---|---|
| `docs/user-guide/getting-started.md` | End users | Setup, first experiment |
| `docs/user-guide/configuration.md` | End users | Full config reference |
| `docs/contributor-guide/architecture.md` | Contributors | System design, modules, data flow |
| `docs/contributor-guide/extending.md` | Contributors | Adding models, chunkers, endpoints |
| `docs/contributor-guide/development.md` | Contributors | Dev loop, quality gates |
| `docs/contributor-guide/release-process.md` | Contributors | Creating releases, versioning strategy |
| `docs/plan/slices/PROGRESS.md` | Agents | Slice status, decision log, roadmap |
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
