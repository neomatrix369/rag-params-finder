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

**One command (mirrors CI exactly):**

```bash
./scripts/quality-gates.sh              # full CI mirror (default)
./scripts/quality-gates.sh --quick      # lint + typecheck + unit tests only
./scripts/quality-gates.sh --full       # CI mirror + local gitleaks + pre-commit all-files
```

**Integrity check (unit tests + import smoke):**

```bash
python scripts/check_integrity.py
python scripts/check_integrity.py --full   # + quality-gates + pre-commit
```

### Backend

```bash
# Lint — expect 0 errors, 0 warnings
uv run ruff check .

# Type check — expect 0 errors
uv run mypy server/ cli/

# Tests + coverage (scoped to unit-tested modules, 80% threshold)
uv run pytest --tb=short -q \
  --cov=server.core.search_index_plan \
  --cov=server.core.search_index_guard \
  --cov=server.core.results_analyzer \
  --cov=server.models.config \
  --cov-fail-under=80

# Python dependency audit (ML transitive vulns tracked — see scripts/pip-audit.sh)
bash scripts/pip-audit.sh
```

**Baseline (as of 2026-05-27)**:
- `ruff check .` → 0 errors
- `mypy server/ cli/` → 0 errors
- `pytest` → 23 tests, 83.6% coverage on scoped modules

### Frontend

```bash
cd frontend

# Lint — expect 0 errors, 0 warnings (eslint + security plugin)
npm run lint

# Type check — expect 0 errors
npm run typecheck

# Build — expect ~49 modules
npm run build

# Security audit — expect 0 vulnerabilities at high+ severity
npm audit --audit-level=high
```

**Baseline (as of 2026-05-27)**:
- `npm run lint` → 0 errors
- `npm run typecheck` → 0 errors
- `npm run build` → built in ~4s, 49 modules
- `npm audit --audit-level=high` → 0 high vulnerabilities

### Pre-commit

```bash
uv pip install -e ".[dev]"
pre-commit install
```

---

## 🧪 Testing Strategy

**Fast unit tier** (`tests/`, run in CI and `./scripts/quality-gates.sh`):

| Module | Tests | Focus |
|--------|-------|--------|
| `test_search_index_plan.py` | 15 | Required Atlas indexes, capacity scenarios |
| `test_search_index_guard.py` | 2 | Preflight guard (mocked I/O) |
| `test_expand_sweep.py` | 3 | Unified `retrievers` sweep expansion |
| `test_tiebreaker_ranking.py` | 3 | Weighted ranking / tiebreaker logic |

**Total:** 23 pytest tests (2026-05-27 baseline). Coverage is enforced at **80%** on four scoped server modules (see Quality Gates above).

**Still manual / not automated:**
- End-to-end pipeline via CLI + dashboard (real Atlas + optional Voyage)
- **Integration tests**: full pipeline with mock MongoDB and pre-computed embedding fixtures (planned — `integration` marker exists in `pyproject.toml`)
- **Frontend**: ESLint + `tsc` + production build in CI; no Vitest/Jest suite yet

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
└── .github/workflows/   # CI (see § CI — backend, frontend, secrets jobs)
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
[ ] Consider release: ./scripts/release.sh minor (slices/features) or patch (fixes/polish)
    See docs/_internal/PROGRESS.md § Release Cadence for guidance
```

---

## 🔄 CI

GitHub Actions runs on every push and PR to `main` (three jobs — see `.github/workflows/ci.yml`):

| Job | Steps |
|-----|--------|
| **Backend (Python)** | `ruff check` → `ruff format --check` → `mypy` → `bandit -ll` → `pytest` + 80% scoped coverage → `scripts/pip-audit.sh` |
| **Frontend (Node.js)** | `npm run lint` → `npm run typecheck` → `npm run build` → `npm audit --audit-level=high` (Node from repo-root `.nvmrc`) |
| **Secrets** | `gitleaks-action` with `.gitleaks.toml` |

Dependabot opens weekly PRs for pip, npm, and GitHub Actions (`.github/dependabot.yml`).

Local mirror: `./scripts/quality-gates.sh` (default). Use `--quick` for lint/typecheck/tests only; `--full` adds local gitleaks + `pre-commit run --all-files`.

---

## 🪵 Debugging and logs

**Server and CLI** use Option A scoped logging via `server/utils/scope_log.py`:

```
[rag-params-finder] [Orchestrator] sweep scheduled — experiment abc123, 90 run(s)
[rag-params-finder] [indexes] vector indexes OK — already exist
```

Set `LOG_LEVEL=DEBUG` in `.env` and restart uvicorn for verbose output. Uvicorn access logs are suppressed at WARNING by default.

**Dashboard** (dev mode only) uses `frontend/src/utils/devLog.ts` with the same prefix pattern. Calls are stripped from production builds.

**Search index issues:** run `rag-params-finder indexes list` before submitting sweeps on M0. Preflight errors on submit return HTTP 422 with actionable messages.

---

## 🤖 AI-assisted development (optional)

**Not required** to run, test, or ship `rag-params-finder`. End users can ignore this section.

Some contributors use **Cursor** or **Claude Code** with the [`code-review-graph`](https://pypi.org/project/code-review-graph/) MCP server — a local knowledge graph of callers, callees, tests, and change impact. It speeds up exploration and review; it does not affect the FastAPI server, CLI, or dashboard.

| Audience | Needs code-review-graph? |
|---|---|
| Running sweeps / using the dashboard | No |
| Contributing code or reviewing PRs | Optional |

**Setup (when you want it):**

1. Install the server: `uvx code-review-graph serve` (or configure MCP in your editor — see project `.mcp.json` if present).
2. Let hooks build/update the graph; cache lives in `.code-review-graph/` (gitignored).
3. In Cursor, project guidance may live in `.cursor/rules/code-review-graph.mdc` (local; `.cursor/` is gitignored except shared symlinks on your machine).

**Workflow:** Prefer graph tools (`detect_changes`, `query_graph`, `get_impact_radius`, …) before broad Grep/file reads. Full tool list and workflow: [AGENTS.md](../../AGENTS.md) and [CLAUDE.md](../../CLAUDE.md).

---

## 🤝 Contributing

Areas where help is most needed:

- **Test suite expansion**: integration tier with mock MongoDB + pre-computed embedding fixtures *(23 unit tests shipped — search index, sweep expansion, tiebreaker)*
- **SSE live updates**: replace the 2-second polling loop with Server-Sent Events
- **Docker Compose**: one-command `docker compose up` setup
- **Experiment cleanup CLI**: `rag-params-finder cleanup --older-than 30d`

Please open an issue before starting work on large features to discuss the approach.

---

## 👉 See Also

- [Architecture](architecture.md) — system design and module map
- [Extending the System](extending.md) — step-by-step guides for adding models, chunkers, endpoints
- [Local Environment](local-environment.md) — Atlas setup, debugging, and maintenance details
- [Release Process](release-process.md) — creating releases, versioning strategy, when to release
- [AGENTS.md](../../AGENTS.md) · [CLAUDE.md](../../CLAUDE.md) — agent entry points (incl. optional code-review-graph MCP)
- [docs/_internal/PROGRESS.md](../_internal/PROGRESS.md) — slice status, decision log, forward roadmap
