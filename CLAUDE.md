# CLAUDE.md

Agent guidance for `rag-params-finder`. Start with `AGENTS.md` → this file → `docs/_internal/PROGRESS.md`.

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

# Run server
uvicorn server.main:app --reload --port 8001

# Lint & type check
uv run ruff check .
uv run mypy server/ cli/

# Tests
uv run pytest --tb=short -q
```

### Frontend (Node.js 22+)

```bash
cd frontend
npm install
npm run dev           # → http://localhost:5173
npm run typecheck
npm run build
```

### CLI

```bash
rag-params-finder run --config configs/example-mongodb-local.yaml
rag-params-finder run --config configs/example-mongodb-local.yaml --detach
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
| `server/core/atlas_storage.py` | Atlas Admin API cluster quota + tier specs (`resolve_tier_specs`); shared-tier storage fallbacks |
| `server/core/model_registry.py` | Embedding + reranking model catalog |
| `server/core/embedder.py` | Voyage embedding client; `voyage-context-3` uses contextualized API with segment splitting |
| `server/core/local_embedder.py` | sentence-transformers embedding (lazy-load) |
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
- `embedding.provider`: "local" or "voyage"
  - Local → `server/core/local_embedder.py` → `all-MiniLM-L6-v2` (384-dim)
  - Voyage → `server/core/embedder.py` → all models in `EMBEDDING_MODELS` with `provider: voyage` (1024-dim; `voyage-context-3` uses `contextualized_embed()` with automatic segment splitting for long documents)
- **`retrieval.retrievers`** (NEW unified format):
  - Traditional retrievers: `{type: dense|sparse|hybrid}` — no provider/model needed
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

**Old format** (deprecated, auto-migrated):
- `retrieval.methods` + `rerank_provider`/`rerank_model` — still works but converts to `retrievers` internally

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
[ ] Read docs/_internal/PROGRESS.md — confirm current state and which slice is next
[ ] Read or create the slice spec in docs/slices/SLICE-XX-*.md
[ ] Run all quality gates — confirm zero regressions before starting
[ ] Note the exact acceptance criteria — these are the exit conditions
```

### Decision log template
Record every non-obvious choice in `docs/_internal/PROGRESS.md` → Decision Log:
```
| <date> | <slice> | <decision> | <why> |
```

### Verify-all commands (run before each commit)
```bash
# Backend
uv run ruff check .
uv run mypy server/ cli/
uv run pytest --tb=short -q

# Frontend
cd frontend && npm run typecheck && npm run build
```

### Post-slice checklist
```
[ ] All acceptance criteria checked ✅
[ ] Quality gates pass (zero regressions)
[ ] Slice status updated in docs/_internal/PROGRESS.md (🔨 → ✅ COMPLETE)
[ ] Decisions logged in PROGRESS.md Decision Log
[ ] Committed with a short, specific message
```

## Quality Gates Baseline

**Backend** (2026-05-23):
- `ruff check .` → 0 errors
- `mypy server/ cli/` → 0 errors
- `pytest` → 17 tests (search index preflight)

**Frontend** (2026-05-05):
- `npm run typecheck` → 0 errors
- `npm run build` → ✓ built in ~1.8s, 34 modules
- `npm audit --audit-level=high` → 0 vulnerabilities

## Further Reading

| Doc | Audience | Purpose |
|---|---|---|
| `docs/user-guide/getting-started.md` | End users | Setup, first experiment |
| `docs/user-guide/configuration.md` | End users | Full config reference |
| `docs/contributor-guide/architecture.md` | Contributors | System design, modules, data flow |
| `docs/contributor-guide/extending.md` | Contributors | Adding models, chunkers, endpoints |
| `docs/contributor-guide/development.md` | Contributors | Dev loop, quality gates |
| `docs/_internal/PROGRESS.md` | Agents | Slice status, decision log, roadmap |
| `docs/adr/` | All | Architecture Decision Records |
