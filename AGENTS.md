# AGENTS.md

Agent session entry point for `rag-params-finder`.

## Start here

1. Read [`CLAUDE.md`](CLAUDE.md) — project overview, architecture, commands, quality gates, and slice playbook.
2. Read [`docs/_internal/PROGRESS.md`](docs/_internal/PROGRESS.md) — current slice status, forward roadmap, and interrupt recovery checklist.
3. If continuing a slice: read the slice spec in [`docs/slices/`](docs/slices/).
4. If starting a new slice: check the forward roadmap in `docs/_internal/PROGRESS.md` and create a spec before writing code.

## Key rules

- Run quality gates before and after every change; install hooks with `bash scripts/install-git-hooks.sh` (commit + pre-push checks — see `CLAUDE.md` → Quality Gates Baseline).
- Follow the slice execution playbook in `CLAUDE.md` → Slice Execution Playbook.
- Secrets (`VOYAGE_API_KEY`, `MONGODB_URI`) stay server-side — never in CLI configs or committed files.
- Provider/model must match: `provider: local` + Voyage model → Pydantic validation error.

## Quick commands

```bash
# Quality gates (mirrors CI — run before every commit)
./scripts/quality-gates.sh              # full CI mirror (repo lint + backend + frontend + audits)
bash scripts/repo-lint.sh               # shellcheck + actionlint + markdownlint only
./scripts/quality-gates.sh --quick      # repo lint + lint + typecheck + unit tests (no coverage/build/audits)
./scripts/quality-gates.sh --full       # + local gitleaks + pre-commit all-files
python scripts/check_integrity.py       # unit tests + import smoke

# Docker (server + dashboard; CLI on host)
./start-services.sh                            # prod profile → :8001, :5173
./scripts/health-check.sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Backend
uvicorn server.main:app --reload --port 8001   # start server (manual)
rag-params-finder run --config configs/example-mongodb-local.yaml  # submit experiment
rag-params-finder pause <experiment-id>   # pause after current phase
rag-params-finder resume <experiment-id>  # continue paused sweep
rag-params-finder indexes list            # Atlas Search indexes (known vs unknown)
rag-params-finder indexes reset           # drop unknown indexes + ensure required
rag-params-finder indexes reset --all     # drop all chunks search indexes + recreate
uv pip install -e ".[dev]"
bash scripts/install-git-hooks.sh          # essential checks on commit (staged) and push (all files)

# Frontend
cd frontend && npm run dev                     # start dashboard → http://localhost:5173
npm run lint && npm run typecheck && npm run build
```

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
