# Project Invariants
> Self-contained reference — key constraints extracted here. Links provided for traceability only.
> Created by plan-health-check on 2026-09-10 — refresh when interview_summary / DECISIONS / TRAIL change.

## Key constraints
- All PCTO / dual-backend changes are **additive** — no orchestrator rewrites.
- Voyage AI stays as the numeric baseline for sweep comparisons.
- MCP server is **Won't** this cycle; `GET /api/v1/best-config` is the integration point if ever needed.
- Major toolchain bumps (Vite 8, ESLint 9, sentence-transformers v4+) need dedicated slices — not blind merges.
- Factory-function dispatch for new providers (`embedder_factory.py`) preferred over Protocol ceremony unless a cross-adapter contract is required (Storage/Retriever ports are the Protocol exception — DECISIONS #10 upgraded for dual-backend).
→ Source: `docs/plan/interview_summary.md` § Constraints; DECISIONS #7–#10, #130

## Architecture decisions (non-negotiable)
- **Dual-backend**: Postgres/pgvector + Mongo via `StorageBackend` / `RetrieverBackend` Protocols; code default stays `STORAGE_BACKEND=mongodb` permanently (#130 Won't flip).
- Backends are independent — neither is a fail-safe for the other (#129).
- ADR-004 Accepted; ADR-003 Superseded (#127).
- SIE is opt-in (`SIE_ENABLED` + endpoint/key); Voyage/local remain first-class.
- New embedding providers (e.g. DoubleWord, Slice 48) are opt-in behind a fail-closed readiness guard (HTTP 422 at submit); configs that don't use them must behave byte-identically without their keys (#192).
- `SWEEP_EXECUTOR` has **one worker**: nothing may block it waiting on an external async job (e.g. DoubleWord batches) — submit, release, and resume via a detached watcher (#200).
- Secrets (`VOYAGE_API_KEY`, `DOUBLEWORD_API_KEY`, `MONGODB_URI`, `DATABASE_URL` / `SUPABASE_URI`) stay server-side — never in CLI configs or commits.
→ Source: `docs/plan/DECISIONS.md` (#114–#130, #166–#170); `docs/adr/ADR-004-*.md`

## Vector store / split-store (Slices 49A–51, 53)
- `VECTOR_STORE_BACKEND` defaults to `STORAGE_BACKEND`; single-store Mongo/Postgres behaviour stays byte-identical (#240, #242).
- Chunk write, delete, stats and search go **only** through `get_vector_store()`; run state (experiments, runs, results) goes only through `get_storage_backend()`. `get_retriever_backend()` keeps its name and signature and resolves via the vector store (#240).
- Pairing rule (ii): a store that can hold run state must hold it (`VECTOR_STORE_BACKEND == STORAGE_BACKEND`); vector-only stores (ES, Redis) pair with either. `elasticsearch` / `redis` are never valid for `STORAGE_BACKEND` (#241).
- Delete order: vector store first, then run state; both idempotent (#246).
- `/healthz` returns 503 if either store is down; `storage_mode` = vector store, plus `run_state_mode` and `stores{}`; a missing or placeholder URI for either store stops startup, an unreachable store is reported by `/healthz` 503 and preflight 422 (#247, #250).
- One `DatabaseProvider` Literal (`server/models/config.py`); no store-name comparisons outside adapters, registry, settings and config normalisers (AST guard over `server/` + `cli/`) (#240, #242).
- Mandatory `embedding_model` + `experiment_id` + `run_id` filter on every vector query; dense scores on the shared `(1+cos)/2` scale; hybrid via RRF `k=60`.
- Local ES (D5) pairs with `postgres-local` by default; Basic licence, security off, `127.0.0.1`, 1 GB heap, unquantized HNSW (#215, ADR-006).
- Scripts read `scripts/lib/stores.tsv` (bash 3.2-safe); server image extras via `ARG EXTRAS`; one nightly matrix job, skipped ≠ green (#243, #244, #248).
→ Source: `docs/plan/DECISIONS.md` (#213–#219, #240–#250); `docs/plan/slices/05-storage/SLICE-49*.md`–`SLICE-53*.md`

## Tech stack & runtime
- Python 3.12+ via `uv`; Node 22+ (frontend); FastAPI server `:8001`; React dashboard `:5374`.
- Quality gates: `./scripts/ci/quality-gates.sh` (repo lint + backend + frontend + audits).
- Complexity gate baseline: xenon E/C/C on `server/` `cli/` (reporting toward B/A/A — Slice 47).
- Coverage floors: FE **95/90/95/95**; BE combined fail_under + floor checkers (DECISIONS #142).
- Model split — Planning: claude-opus-4-8 · Execution: claude-sonnet-4-6 (TRAIL Original Material).
→ Source: `docs/plan/TRAIL.md` § Original Material; `CLAUDE.md` § Quality Gates Baseline

## Baseline commands
A fresh executor should be able to act from this file alone. Each command below is runnable as-is.

| Stack | Baseline command | What it proves |
|-------|------------------|----------------|
| All gates | `./scripts/ci/quality-gates.sh` | Mirrors PR `ci.yml` — repo lint + backend + frontend + audits pass |
| Repo lint | `bash scripts/ci/repo-lint.sh` | shellcheck + actionlint + markdownlint pass |
| Backend tests | `uv run pytest --tb=short -q` | Unit-tier suite green (live Postgres/Mongo suites excluded) |
| Backend lint/type | `uv run ruff check . && uv run mypy server/ cli/` | 0 lint + 0 type errors |
| Server | `uvicorn server.main:app --reload --port 8001` | App boots; `/healthz` on `:8001` responds |
| Frontend | `cd frontend && npm run test && npm run typecheck && npm run build` | Vitest green, 0 type errors, build ✓ |
| CLI smoke | `rag-params-finder version` | CLI installed and importable |
| CLI run | `rag-params-finder run --config configs/mongodb/example-local.yaml` | End-to-end sweep submits and runs |

→ Source: project `CLAUDE.md` § Development Commands / Quality Gates Baseline; runnable map in [`docs/smoke-tests/SMOKE-REGISTRY.md`](../smoke-tests/SMOKE-REGISTRY.md)

## Depends-on file mapping
Resolves a slice stub's `Depends-on:` ids to the concrete outputs a fresh executor must build on (live tracks).

| Prior slice | Key output files | Quick test command |
|-------------|------------------|--------------------|
| 32 — Storage/Retriever ports | `server/db/ports/storage.py`, `server/db/ports/retriever_backend.py`, `server/db/ports/store_factory.py` | `uv run pytest tests/server/db -q -m "not integration"` |
| 34–38 — Postgres cutover | `server/db/postgres/*.py`, `server/db/postgres/schema.sql` | `uv run pytest tests/server/db/test_postgres_store_integration.py` (needs live pgvector) |
| 49A/49B — Split vector store | `get_vector_store()` in `server/db/ports/store_factory.py`; `VECTOR_STORE_BACKEND` in `server/settings.py`; `DatabaseProvider` in `server/models/config.py` | `uv run pytest tests/server/db -q` + AST guard over `server/`+`cli/` |
| 50/51 — Elasticsearch adapter | ES adapter under `server/db/` (per ADR-006, pending); `scripts/lib/stores.tsv` | nightly matrix job (skipped ≠ green) |
| 48A — DoubleWord provider | `server/core/embedding/embedder_factory.py` dispatch; DoubleWord embedder module | `uv run pytest tests/server/core/embedding -q` |
| 52 — Redis (docs-only) | `docs/plan/BRIEF-redis-evaluation.md` | n/a (brief) |

→ Source: `CLAUDE.md` § Key Files; `docs/plan/slices/05-storage/`, `08-embedding-providers/`

## Project rules
- Branch-per-slice: `slice/<N>-<name>`; never commit directly to `main`.
- State machine: `📋 PLANNED → 🔨 IN PROGRESS → 🔀 ON BRANCH → ✅ PASSED | 🔴 BLOCKED | 📦 DEFERRED`.
- Gate evidence: `docs/plan/gate-evidence/slice-N.json` required before ON BRANCH → PASSED; health-check must not invent `gate_status: PASSED`.
- Must/Should stubs require Context / Non-goals / Output contract + Closing Gates before execution.
- Decision ownership: portable `decision-ownership` rule + filled project matrix at `docs/plan/DECISION-OWNERSHIP.md` (ceiling raises remain Human HITL).
→ Source: project `CLAUDE.md` / `AGENTS.md`; `~/.claude/CLAUDE.md` craft themes; enhanced-flow-planner Output Quality Standards
