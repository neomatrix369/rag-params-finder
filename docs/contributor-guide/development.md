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
# Install Python dev dependencies (includes ruff, mypy, pytest, pre-commit)
uv pip install -e ".[dev]"

# Git hooks: essential checks on commit (staged) and push (whole repo)
bash scripts/install-git-hooks.sh

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

**CI jobs** (`.github/workflows/ci.yml`): `repo-lint` → `backend` → `frontend` → `secrets` (four parallel jobs).

| Layer | Tools |
|-------|--------|
| Repo | shellcheck (`scripts/*.sh`), actionlint, markdownlint |
| Backend | ruff, ruff format, mypy, bandit, pytest + coverage, pip-audit |
| Frontend | eslint, tsc, build, npm audit |
| Secrets | gitleaks |

**One command (mirrors CI exactly):**

```bash
./scripts/quality-gates.sh              # full CI mirror (default)
./scripts/quality-gates.sh --quick      # repo lint + lint + typecheck + unit tests (skips coverage/build/audits)
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

### Repo lint (shell, workflows, Markdown)

```bash
bash scripts/repo-lint.sh
# or individually via pre-commit:
pre-commit run shellcheck --all-files
pre-commit run actionlint --all-files
pre-commit run markdownlint --all-files
```

| Tool | Scope | Config |
|------|--------|--------|
| **Shellcheck** | `scripts/*.sh` | via `shellcheck-py` pre-commit hook |
| **Actionlint** | `.github/workflows/*.yml` | — |
| **Markdownlint** | `*.md` (excludes `.claude/`) | `.markdownlint.json` |

Runs in CI (`repo-lint` job), `./scripts/quality-gates.sh`, and pre-commit.

### Git hooks (commit + push)

```bash
uv pip install -e ".[dev]"
bash scripts/install-git-hooks.sh
# equivalent:
# pre-commit install --hook-type pre-commit --hook-type pre-push
```

| Hook | When | What runs |
|------|------|-----------|
| **pre-commit** | `git commit` | Essential checks on **staged** files (see list below) |
| **pre-push** | `git push` | Same essential checks on the **entire repo** (`pre-commit run --all-files`) |

**Essential checks** (commit + push): trailing whitespace / EOF / YAML·JSON·TOML syntax, merge conflicts, large files, private keys, gitleaks, shellcheck (`scripts/*.sh`), actionlint, markdownlint, bandit, ruff + format, mypy, frontend eslint + verify (when `frontend/` applies).

**Not on push** (run manually or in CI): pytest + coverage, pip-audit, npm audit. Run `./scripts/quality-gates.sh` before opening a PR for full CI parity.

Emergency bypass (use sparingly): `git push --no-verify`

Test push hook without pushing:

```bash
pre-commit run --hook-stage pre-push --all-files
```

**Push did not run checks?** Git only runs hooks that exist under `.git/hooks/`. A plain `pre-commit install` (no `--hook-type pre-push`) installs **commit** only. After pulling hook changes, re-run:

```bash
bash scripts/install-git-hooks.sh
test -x .git/hooks/pre-push && echo "pre-push hook OK"
```

### When checks run (local vs GitHub)

| Trigger | What runs |
|---------|-----------|
| `git commit` | **pre-commit** — staged files (hygiene, secrets, repo lint, ruff, mypy, bandit, frontend when touched) |
| `git push` | **pre-push** — same essential hooks as commit, all files |
| PR or push to `main` | **GitHub Actions** — full CI (four jobs; includes pytest, coverage, pip-audit, npm audit, build) |
| Manual | `./scripts/quality-gates.sh` — full local mirror of CI before opening a PR |

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
└── .github/workflows/   # CI (see § CI — repo-lint, backend, frontend, secrets)
```

---

## 📋 Slice Execution Playbook

### Pre-slice checklist

```
[ ] Read docs/_internal/PROGRESS.md — confirm current state and which slice is next
[ ] Read or create the slice spec in docs/slices/SLICE-XX-*.md
[ ] bash scripts/install-git-hooks.sh (once per machine if not already installed)
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
[ ] Quality gates pass — ./scripts/quality-gates.sh; git push exercised essential pre-push hook
[ ] Slice status updated in docs/_internal/PROGRESS.md (🔨 → ✅ COMPLETE)
[ ] Decisions logged in PROGRESS.md Decision Log
[ ] Committed with a short, specific message
[ ] Consider release: ./scripts/release.sh minor (slices/features) or patch (fixes/polish)
    See docs/_internal/PROGRESS.md § Release Cadence for guidance
```

---

## 🔄 CI

GitHub Actions runs on every push and PR to `main` (four jobs — see `.github/workflows/ci.yml`):

| Job | Steps |
|-----|--------|
| **Repo lint** | `pre-commit run shellcheck` → `actionlint` → `markdownlint` (all files) |
| **Backend (Python)** | `ruff check` → `ruff format --check` → `mypy` → `bandit -ll` → `pytest` + 80% scoped coverage → `scripts/pip-audit.sh` |
| **Frontend (Node.js)** | `npm run lint` → `npm run typecheck` → `npm run build` → `npm audit --audit-level=high` (Node from repo-root `.nvmrc`) |
| **Secrets** | `gitleaks-action` with `.gitleaks.toml` |

Dependabot opens weekly PRs for pip, npm, and GitHub Actions (`.github/dependabot.yml`).

**Local mirrors:** `./scripts/quality-gates.sh` (full, before PR). **`git push`** runs essential pre-commit hooks on all files if `install-git-hooks.sh` was used. `--quick` / `--full` are manual only.

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
