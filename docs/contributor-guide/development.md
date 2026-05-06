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
rag-params-finder run --config configs/example-local.yaml
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

# Tests (suite not yet written — 0 collected is the current baseline)
uv run pytest --tb=short -q

# Coverage (when tests exist)
uv run pytest --cov=server --cov=cli --cov-report=html
```

**Baseline (as of 2026-05-05)**:
- `ruff check .` → 0 errors
- `mypy server/ cli/` → 0 errors
- `pytest` → 0 tests collected

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

Current approach: manual testing via CLI + Dashboard.

**Planned test layers** (no suite yet — see Contributing):
- **Unit tests**: individual chunkers, embedders, rerankers with mock inputs
- **Integration tests**: full pipeline with mock MongoDB collections and pre-computed embedding fixtures (avoids real API calls)
- **Frontend**: TypeScript compilation serves as the basic type-correctness check (no vitest/jest setup yet)

The primary blockers for a proper test suite are:
- Integration tests need mock MongoDB (or a test Atlas cluster)
- Embedding tests need either a local model or pre-computed fixtures to avoid slow API calls

---

## 📁 Project Structure

```
rag-params-finder/
├── server/              # FastAPI engine
│   ├── main.py          # App entry + startup boot recovery
│   ├── settings.py      # Centralized pydantic-settings config
│   ├── api/             # Thin route handlers
│   ├── core/            # Business logic: orchestration, chunking, embedding, retrieval
│   ├── models/          # Pydantic schemas and enums
│   └── db/              # Atlas connection singleton + index helpers
├── cli/                 # Python CLI client (thin — delegates to server)
├── frontend/            # React dashboard (read-only observer)
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

- **Additional chunkers**: `sentence`, `token`, and `semantic` methods are stubbed with `NotImplementedError`
- **Sparse/hybrid retrieval**: BM25 + Atlas FTS wiring for the `sparse` and `hybrid` paths
- **Test suite**: pytest fixtures with mock MongoDB + pre-computed embedding fixtures
- **SSE live updates**: replace the 2-second polling loop with Server-Sent Events
- **Docker Compose**: one-command `docker compose up` setup

Please open an issue before starting work on large features to discuss the approach.

---

## 👉 See Also

- [Architecture](architecture.md) — system design and module map
- [Extending the System](extending.md) — step-by-step guides for adding models, chunkers, endpoints
- [Local Environment](local-environment.md) — Atlas setup, debugging, and maintenance details
- [docs/_internal/PROGRESS.md](../_internal/PROGRESS.md) — slice status, decision log, forward roadmap
