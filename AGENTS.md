# AGENTS.md

Agent session entry point for `rag-params-finder`.

## Start here

1. Read [`CLAUDE.md`](CLAUDE.md) — project overview, architecture, commands, quality gates, and slice playbook.
2. Read [`docs/PROGRESS.md`](docs/PROGRESS.md) — current slice status, forward roadmap, and interrupt recovery checklist.
3. If continuing a slice: read the slice spec in [`docs/slices/`](docs/slices/).
4. If starting a new slice: check the forward roadmap in `docs/PROGRESS.md` and create a spec before writing code.

## Key rules

- Run quality gates before and after every change (see `CLAUDE.md` → Quality Gates Baseline).
- Follow the slice execution playbook in `CLAUDE.md` → Slice Execution Playbook.
- Secrets (`VOYAGE_API_KEY`, `MONGODB_URI`) stay server-side — never in CLI configs or committed files.
- Provider/model must match: `provider: local` + Voyage model → Pydantic validation error.

## Quick commands

```bash
# Backend
uvicorn server.main:app --reload --port 8001   # start server
rag-params-finder run --config configs/example-local.yaml  # submit experiment
uv pip install -e ".[dev]" && uv run ruff check . && uv run mypy server/ cli/ && uv run pytest

# Frontend
cd frontend && npm run dev                     # start dashboard → http://localhost:5173
npm run typecheck && npm run build             # quality gates
```
