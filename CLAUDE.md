# CLAUDE.md

Agent guidance for `rag-params-finder`. Start with `AGENTS.md` → this file → `docs/_internal/PROGRESS.md`.

## Project Overview

**rag-params-finder** is a RAG parameter sweep experimentation tool with three components:
1. **Python CLI** — submits experiment configs
2. **FastAPI Server** — orchestrates PDF → chunk → embed → search pipeline
3. **React Dashboard** — read-only visualization of experiments and results

Two-process architecture: config submission (CLI) is separate from execution (Server). Dashboard is observer-only.

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
rag-params-finder version
```

List/detail: dashboard or `GET /experiments` / `GET /experiments/{id}` (see `http://localhost:8001/docs`).

## Key Files

| File | Purpose |
|---|---|
| `server/main.py` | FastAPI app entry; lifespan ensures DB indexes |
| `server/settings.py` | Centralized pydantic-settings config |
| `server/core/orchestrator.py` | End-to-end pipeline executor |
| `server/core/model_registry.py` | Embedding + reranking model catalog |
| `server/core/embedder.py` | Voyage embedding client |
| `server/core/local_embedder.py` | sentence-transformers embedding (lazy-load) |
| `server/core/reranker.py` | Voyage reranking client |
| `server/core/local_reranker.py` | CrossEncoder reranking (lazy-load) |
| `server/core/retriever.py` | Atlas Vector Search (dense/sparse/hybrid) |
| `server/models/config.py` | Pydantic experiment config + provider validators |
| `server/models/enums.py` | ChunkingMethod, RetrievalMethod, Phase |
| `cli/main.py` | Typer app (`run`, `cancel`, `version`) |
| `cli/config_loader.py` | YAML parser + model registry validation |
| `frontend/src/App.tsx` | Root component (screen routing) |
| `frontend/src/components/DashboardShell.tsx` | Shared header and navigation wrapper |
| `frontend/src/components/AppPageChrome.tsx` | Shared page wrapper (title, back button, actions) |
| `frontend/src/components/LoadingFeedbackPanel.tsx` | Progress panel with byte-level progress |
| `frontend/src/components/PollingIndicator.tsx` | Subtle "Syncing..." badge during background polls |
| `frontend/src/types/index.ts` | Hand-mirrored TypeScript types from Python models |
| `frontend/src/services/apiClient.ts` | Fetch wrapper (all server API calls) |
| `frontend/src/services/fetchWithProgress.ts` | ReadableStream-based fetch with progress tracking |

## Provider System

**Two independent provider settings**:
- `embedding.provider`: "local" or "voyage"
  - Local → `server/core/local_embedder.py` → `all-MiniLM-L6-v2` (384-dim)
  - Voyage → `server/core/embedder.py` → `voyage-3.5-lite|voyage-3.5|voyage-context-3` (1024-dim)
- `retrieval.rerank_provider`: "local" or "voyage"
  - Local → `server/core/local_reranker.py` → `cross-encoder/ms-marco-MiniLM-L-6-v2`
  - Voyage → `server/core/reranker.py` → `rerank-2.5-lite|rerank-2.5`

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

**Backend** (2026-05-05):
- `ruff check .` → 0 errors
- `mypy server/ cli/` → 0 errors
- `pytest` → 0 tests collected (test suite not yet written)

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
