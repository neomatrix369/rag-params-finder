# Development Guide

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-package_manager-DE5FE9?logoColor=white)
![ruff](https://img.shields.io/badge/ruff-linter-D7FF64?logoColor=black)
![mypy](https://img.shields.io/badge/mypy-type_checker-2A6DB2?logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI-2088FF?logo=githubactions&logoColor=white)

Dev environment setup, quality gates, testing strategy, and the slice workflow for contributors.

---

## 🛠️ Setup

### Backend

```bash
# Install Python dev dependencies (includes ruff, mypy, pytest)
uv pip install -e ".[dev]"

# Start the server
uvicorn server.main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # → http://localhost:5173
```

### Three-terminal development loop

```bash
# Terminal 1: Backend server (auto-reloads on .py changes)
source .venv/bin/activate
uvicorn server.main:app --reload --port 8001

# Terminal 2: Frontend (HMR on .tsx changes)
cd frontend && npm run dev

# Terminal 3: CLI submissions
source .venv/bin/activate
rag-params-finder run --config configs/example-mongodb-local.yaml
```

---

## ✅ Quality Gates

Run all gates before committing. All must pass with zero regressions.

### Backend

```bash
# Lint — expect 0 errors, 0 warnings
uv run ruff check .

# Type check — expect 0 errors
uv run mypy server/ cli/

# Tests (same as CI — provider regression suite)
rag-params-finder test

# Coverage (optional)
uv run pytest -m "not integration" --cov=server --cov=cli --cov-report=html
```

**Baseline (as of 2026-05-20)**:
- `ruff check .` → 0 errors
- `mypy server/ cli/` → 0 errors
- `rag-params-finder test` → 39 tests in `tests/` (no MongoDB or live API keys; GitHub Actions on PRs to `main`)

### Frontend

```bash
cd frontend

# Type check — expect 0 errors
npm run typecheck

# Build — expect ~34 modules, ~238 kB JS
npm run build

# Security audit — expect 0 vulnerabilities at high+ severity
npm audit --audit-level=high
```

**Baseline (as of 2026-05-05)**:
- `npm run typecheck` → 0 errors
- `npm run build` → built in ~1.8s, 34 modules
- `npm audit --audit-level=high` → 0 vulnerabilities

---

## 🧪 Testing Strategy

**CI today:** `rag-params-finder test` (or `uv run pytest -m "not integration" --tb=short -q`) — runs on every PR and merge queue to `main`; 39 provider-regression tests (embedder dispatch, retriever indexes, config validation, Vector DB stats, Kimchi adapter parsing). No MongoDB or live API keys required.

**Planned expansion:** [`docs/slices/SLICE-17-TEST-SUITE-EXPANSION.md`](../slices/SLICE-17-TEST-SUITE-EXPANSION.md) — parked high/medium items from the Kimchi merge review:

| Priority | Parked in Slice 17 |
|----------|-------------------|
| High | Manual smoke checklist (local / Voyage / Kimchi); Kimchi Atlas `vector_index_<dim>` docs; Kimchi embedding batching; env-gated CAST integration test |
| Medium | `ensure_vector_index` cache; orchestrator + pause/resume tests; reranker dispatch; sparse/hybrid retriever; mock-Mongo pipeline fixtures |
| Lower | Frontend vitest; dead-code cleanup; parallel-sweep tests (with Slice 16) |

Until Slice 17 ships, treat **pytest green + manual smoke** as the merge gate for provider changes.

**Manual testing** remains required for full CLI + Dashboard flows (see `VERIFICATION_CHECKLIST.md` at repo root).

---

## 📁 Project Structure

```
rag-params-finder/
├── server/              # FastAPI engine
│   ├── main.py          # App entry; lifespan ensures DB indexes
│   ├── settings.py      # Centralized pydantic-settings config
│   ├── api/             # Thin route handlers
│   ├── core/            # Business logic: orchestration, chunking, embedding, retrieval
│   ├── models/          # Pydantic schemas and enums
│   └── db/              # Atlas connection singleton + index helpers
├── cli/                 # Python CLI client (thin — delegates to server)
├── frontend/            # React dashboard (observe + pause/resume/cancel/delete)
│   └── src/
│       ├── components/  # ExperimentsScreen, ExperimentDetailScreen, SearchExplorerScreen
│       ├── services/    # apiClient.ts — all fetch calls
│       └── types/       # Hand-mirrored TypeScript types from Python models
├── configs/             # Example YAML configs and queries files
├── input_data/          # User-supplied documents (gitignored)
├── docs/
│   ├── user-guide/      # End-user documentation
│   ├── contributor-guide/ # This directory
│   ├── adr/             # Architecture Decision Records
│   ├── slices/          # Slice specs (dev-internal)
│   └── _internal/       # Dev log, gap tracker, Graphiti exports
└── .github/workflows/   # CI (ruff, mypy, pytest, npm typecheck + build)
```

---

## 📋 Slice Execution Playbook

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

### Post-slice checklist

```
[ ] All acceptance criteria checked ✅
[ ] Quality gates pass (zero regressions)
[ ] Slice status updated in docs/_internal/PROGRESS.md (🔨 → ✅ COMPLETE)
[ ] Decisions logged in PROGRESS.md Decision Log
[ ] Committed with a short, specific message
```

---

## 🔄 CI

GitHub Actions runs on every push and PR to `main`:

- **Backend**: `ruff check` → `mypy` → `pytest`
- **Frontend**: `npm run typecheck` → `npm run build`

See `.github/workflows/ci.yml` for the full pipeline.

---

## 🤝 Contributing

Areas where help is most needed:

- **Test suite (Slice 17)**: see [`SLICE-17-TEST-SUITE-EXPANSION.md`](../slices/SLICE-17-TEST-SUITE-EXPANSION.md) — mock MongoDB + pre-computed embedding fixtures, orchestrator coverage
- **SSE live updates**: replace the 2-second polling loop with Server-Sent Events
- **Docker Compose**: one-command `docker compose up` setup
- **Experiment cleanup CLI**: `rag-params-finder cleanup --older-than 30d`

Please open an issue before starting work on large features to discuss the approach.

---

## 👉 See Also

- [Architecture](architecture.md) — system design and module map
- [Extending the System](extending.md) — step-by-step guides for adding models, chunkers, endpoints
- [Local Environment](local-environment.md) — Atlas setup, debugging, and maintenance details
- [docs/_internal/PROGRESS.md](../_internal/PROGRESS.md) — slice status, decision log, forward roadmap
