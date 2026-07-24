# Development Guide

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-package_manager-DE5FE9?logoColor=white)
![ruff](https://img.shields.io/badge/ruff-linter-D7FF64?logoColor=black)
![mypy](https://img.shields.io/badge/mypy-type_checker-2A6DB2?logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)
[![CI](https://img.shields.io/github/actions/workflow/status/neomatrix369/rag-params-finder/ci.yml?branch=main&label=CI&logo=githubactions&logoColor=white)](https://github.com/neomatrix369/rag-params-finder/actions/workflows/ci.yml)
[![Nightly](https://img.shields.io/github/actions/workflow/status/neomatrix369/rag-params-finder/nightly.yml?branch=main&label=Nightly&logo=githubactions&logoColor=white)](https://github.com/neomatrix369/rag-params-finder/actions/workflows/nightly.yml)

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
npm run dev    # → http://localhost:5374
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

### Docker Compose

One-command stack for server + dashboard (MongoDB Atlas stays external). The **CLI runs on the host** at `SERVER_URL=http://localhost:8001` ([ADR-001](../adr/ADR-001-two-process-architecture.md)).

**Prerequisites:** Docker Desktop (or engine + Compose v2), valid `.env` with `MONGODB_URI`, Atlas search indexes per [mongodb-setup](../user-guide/mongodb-setup.md).

```bash
cp .env.example .env
./start-services.sh              # prod: built frontend + uvicorn (ports 8001, 5374)
./start-services.sh --force-build # rebuild images even when source unchanged
./scripts/health-check.sh        # smoke: server, frontend, Atlas via /healthz

# Host CLI (install once: uv pip install -e .)
rag-params-finder run --config configs/example-mongodb-local.yaml

# Dev overlay: HMR + uvicorn --reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
# or: RAG_DEV_STACK=1 ./start-services.sh

./stop-services.sh               # interactive stop (standard / pause / deep cleanup)
```

| Port | Service |
|------|---------|
| 8001 | FastAPI server |
| 5374 | React dashboard |

**Profiles:** default = production-like (`vite preview`); `dev` = bind-mounted source + `/api` proxy to `http://server:8001`.

**Non-interactive:** `NONINTERACTIVE=1 ./start-services.sh` (fails fast on missing/placeholder `.env`).

Spec: [SLICE-14-DOCKER-COMPOSE.md](../plan/slices/SLICE-14-DOCKER-COMPOSE.md). Troubleshooting: [user-guide/troubleshooting.md](../user-guide/troubleshooting.md#-docker).

---

## ✅ Quality Gates

Run all gates before committing. All must pass with zero regressions.

**CI jobs** (`.github/workflows/ci.yml`): `repo-lint`, `backend`, `frontend`, `secrets`, `dependency-audit` (five jobs, path-filtered). Nightly T4 checks in `.github/workflows/nightly.yml` (mutmut, Stryker, TruffleHog full, SBOM/CycloneDX, Meterian, container scan, Chalk provenance — every night 02:00 UTC).

| Layer | Tools |
|-------|--------|
| Repo | shellcheck (`scripts/*.sh`), actionlint, markdownlint |
| Backend | ruff, ruff format, mypy, bandit, pytest + coverage, pip-audit |
| Frontend | Vitest + React Testing Library, eslint, tsc, build, npm audit |
| Secrets | gitleaks |

**One command (mirrors CI exactly):**

```bash
./scripts/quality-gates.sh              # full CI mirror (default)
./scripts/quality-gates.sh --quick      # fast local subset (pytest no coverage, no scoped SCA/audit)
./scripts/pre-push-gates.sh             # push-specific gates only (pytest+cov, vite build, vitest, audits)
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
  --cov=server.core.sie_embedder \
  --cov=server.core.aim_logger \
  --cov=server.core.embedder_factory \
  --cov-fail-under=80

# Python dependency audit (ML transitive vulns tracked — see scripts/pip-audit.sh)
bash scripts/pip-audit.sh
```

**Baseline (as of 2026-07-05)**:
- `ruff check .` → 0 errors
- `mypy server/ cli/` → 0 errors
- `pytest` → 97 tests, coverage on scoped modules

### Frontend

```bash
cd frontend

# Lint — expect 0 errors, 0 warnings (eslint + security plugin)
npm run lint

# Component tests — expect all lifecycle scenarios to pass
npm run test

# Type check — expect 0 errors
npm run typecheck

# Build — expect ~49 modules
npm run build

# Security audit — expect 0 vulnerabilities at high+ severity
npm audit --audit-level=high
```

**Baseline (as of 2026-07-19)**:
- `npm run lint` → 0 errors
- `npm run test` → 7 component scenarios pass
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
| **pre-commit** | `git commit` | Static checks on **staged** files — no duplication with push (see list below) |
| **pre-push** | `git push` | Push-specific only: `./scripts/pre-push-gates.sh` (checks that commit cannot provide) |

**Pre-commit** (staged files): hygiene hooks, gitleaks, shellcheck, actionlint (~620 ms via managed binary), markdownlint, bandit, ruff + format, **dmypy** daemon (~0.5 s warm, ~60 s first run), frontend eslint + **tsc --noEmit** when `frontend/` is touched, testmon fast-tests on changed Python modules.

**Pre-push** (push-specific — zero overlap with commit): full **pytest + coverage** (80% gate, runs only when `server/`, `cli/`, `tests/`, `pyproject.toml`, or `uv.lock` changed — mirrors `ci.yml` `backend` path filter), **vite build**, vitest component tests (frontend-changed only), pip-audit (lockfile-changed), npm audit (lockfile-changed).

**Not on push**: `./scripts/quality-gates.sh --full` adds a repo-wide pre-commit all-files sweep and deeper security scans; routine push uses only push-specific gates.

Emergency bypass (use sparingly): `git push --no-verify`

Test push hook without pushing:

```bash
pre-commit run pre-push-gates --hook-stage pre-push
# or: ./scripts/pre-push-gates.sh
```

**Push did not run checks?** Git only runs hooks that exist under `.git/hooks/`. A plain `pre-commit install` (no `--hook-type pre-push`) installs **commit** only. After pulling hook changes, re-run:

```bash
bash scripts/install-git-hooks.sh
test -x .git/hooks/pre-push && echo "pre-push hook OK"
```

### When checks run (local vs GitHub)

| Trigger | What runs |
|---------|-----------|
| `git commit` | **pre-commit** — hygiene, gitleaks, repo lint, ruff, dmypy, bandit, eslint, tsc --noEmit, testmon fast-tests (changed modules) |
| `git push` | **pre-push** — pytest+coverage (backend-changed only), vite build, vitest, pip-audit, npm audit (zero overlap with commit) |
| PR or push to `main` | **GitHub Actions** — CI (repo-lint, backend, frontend, secrets, dependency-audit jobs) + nightly 02:00 UTC (mutmut, Stryker, TruffleHog, SBOM/CycloneDX, Meterian, container scan, Chalk) |
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
| `test_embedder_factory.py` | 6 | Provider dispatch factory (voyage/local/sie) |
| `test_sie_embedder.py` | 5 | SIE BGE-M3 dense embedding (mocked SIEClient) |
| `test_sweep_endpoint.py` | 9 | `POST /api/v1/sweep` + health helpers |

**Total:** 97 pytest tests (includes semantic overlap, padding, SIE, search-index, sweep-endpoint suites). Coverage is enforced at **80%** on scoped server modules (see Quality Gates above).

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
│   ├── plan/slices/     # Slice specs + PROGRESS.md (status, roadmap)
│   ├── _internal/       # Gap tracker, audits, Graphiti exports
│   └── README.md        # Documentation index (doc map)
└── .github/workflows/   # CI (see § CI — repo-lint, backend, frontend, secrets)
```

---

## 📋 Slice Execution Playbook

### Pre-slice checklist

```
[ ] Read docs/plan/slices/PROGRESS.md — confirm current state and which slice is next
[ ] Read or create the slice spec in docs/plan/slices/SLICE-XX-*.md
[ ] bash scripts/install-git-hooks.sh (once per machine if not already installed)
[ ] Run all quality gates — confirm zero regressions before starting
[ ] Note the exact acceptance criteria — these are the exit conditions
```

### Decision log template

Record every non-obvious choice in `docs/plan/slices/PROGRESS.md` → Decision Log:

```
| <date> | <slice> | <decision> | <why> |
```

### Post-slice checklist

```
[ ] All acceptance criteria checked ✅
[ ] Quality gates pass — ./scripts/quality-gates.sh; git push exercised full local gates (`pre-push-gates.sh`)
[ ] Slice status updated in docs/plan/slices/PROGRESS.md (🔨 → ✅ COMPLETE)
[ ] Decisions logged in PROGRESS.md Decision Log
[ ] Committed with a short, specific message
[ ] Consider release: ./scripts/release.sh minor (slices/features) or patch (fixes/polish)
    See docs/plan/slices/PROGRESS.md § Release Cadence for guidance
```

---

## 🔄 CI

GitHub Actions has two workflows (see `.github/workflows/`):

**ci.yml** — runs on every push and PR to `main` (path-filtered, five jobs):

| Job | Steps |
|-----|--------|
| **Repo lint** | `pre-commit run shellcheck` → `actionlint` → `markdownlint` (all files) |
| **Backend (Python)** | `ruff check` → `ruff format --check` → `mypy` → `bandit -ll` → `pytest` + 80% scoped coverage |
| **Frontend (Node.js)** | `npm run lint` → `npm run typecheck` → `npm run build` → `npm run test` |
| **Secrets** | `gitleaks` diff-only scan |
| **Dependency audit** | `pip-audit` (backend) + `npm audit` (frontend); lockfile-gated |

**nightly.yml** — every night 02:00 UTC (T4 deep checks):
`mutmut` (Python mutation) · `Stryker` (Node mutation) · `TruffleHog` (full git history) · `anchore/sbom-action` (CycloneDX SBOM) · Trivy license compliance · Meterian SCA · container scan (Dockerfile-gated)

Dependabot opens weekly PRs for pip, npm, and GitHub Actions (`.github/dependabot.yml`).

**Local mirrors:** `./scripts/quality-gates.sh` (full, before PR). **`git push`** runs `./scripts/pre-push-gates.sh` when hooks are installed. `--full` adds pre-commit all-files sweep.

---

## 🪵 Debugging and logs

**Server and CLI** use Option A scoped logging via `server/utils/scope_log.py`:

```
[rag-params-finder] [Orchestrator] sweep scheduled — experiment abc123, 120 run(s)
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
- **Experiment cleanup CLI**: `rag-params-finder cleanup --older-than 30d`

Please open an issue before starting work on large features to discuss the approach.

---

## 👉 See Also

- [Architecture](architecture.md) — system design and module map
- [Extending the System](extending.md) — step-by-step guides for adding models, chunkers, endpoints
- [Local Environment](local-environment.md) — Atlas setup, debugging, and maintenance details
- [Release Process](release-process.md) — creating releases, versioning strategy, when to release
- [AGENTS.md](../../AGENTS.md) · [CLAUDE.md](../../CLAUDE.md) — agent entry points (incl. optional code-review-graph MCP)
- [docs/plan/slices/PROGRESS.md](../plan/slices/PROGRESS.md) — slice status, decision log, forward roadmap
- [docs/README.md](../README.md) — documentation index by persona and topic
