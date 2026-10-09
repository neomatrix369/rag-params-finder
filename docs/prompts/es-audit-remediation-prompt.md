# Elasticsearch Audit Remediation — End-to-End Session Prompt

## Context

You are working on `rag-params-finder`, a RAG parameter sweep experimentation tool with a Python FastAPI backend, React frontend, and CLI. The project supports multiple vector database backends (MongoDB Atlas, PostgreSQL/pgvector, Elasticsearch, Redis) with an orthogonal run-state store (sqlite default per ADR-008, or mongodb/postgres).

## Goal

Perform a full audit remediation of the Elasticsearch vector store adapter and fix all issues found. Loop until every quality gate passes green and the ES pathway works end-to-end. Do not stop until exit criteria are met.

## What to audit and fix

### 1. Bulk insert reliability (`server/db/elasticsearch/elasticsearch_vector_store.py`)
- Check whether `insert_chunks()` inspects the bulk API response for per-document errors — if errors are silently swallowed, add batching (500 docs, 60s timeout), raise on failure, and add partial-write cleanup.
- Check `num_candidates` for kNN — if unbounded, cap at 10,000 (ES hard limit).

### 2. Error handling (`server/db/elasticsearch/client.py`)
- Verify `_api_error_status()` type-guards `meta.status` with `isinstance(int)`.
- Verify `raise_if_unreachable()` has a catch-all for unmapped HTTP codes (500, 502, 504).
- Verify `health_check()` logs the exception before returning `False`.
- Verify HTTP 401/403/429/503 are wrapped in typed exceptions.

### 3. Run-state store pairing (`scripts/lib/storage_mode.sh`)
- ES and Redis must default to `STORAGE_BACKEND=sqlite` per ADR-008.
- Check both `_pair_elasticsearch_run_state` and `_pair_redis_run_state`.
- Check bash 3.2 compatibility (macOS default) — array expansion under `set -u`.

### 4. Config files (`configs/elasticsearch/`)
- All ES config YAMLs must reference `--elasticsearch-local`, not `--mongodb-local`.
- Remove Atlas-specific labels.

### 5. Documentation sync
- `docs/user-guide/elasticsearch-setup.md` — correct defaults, prerequisites, quickstart commands.
- `README.md` and `QUICKSTART.md` — ES sections must match actual setup flow.
- Architecture C4 diagrams — sqlite run-state defaults must be reflected.

### 6. Dependency security
- Run `bash scripts/ci/pip-audit.sh` — fix CVEs with `uv lock --upgrade-package <pkg>` (NOT `uv pip install --upgrade`).
- If pymongo ≥4.18, remove `pymongo[srv]` from `pyproject.toml` (dnspython is now a hard dep).
- Run `npm --prefix frontend audit --omit=dev --audit-level=high`.
- Apply `--omit=dev` consistently: `quality-gates.sh`, `pre-push-gates.sh`, `ci.yml`, `nightly.yml`.

### 7. Docker images
- Refactor `server.Dockerfile` into base+derived multi-stage pattern if needed.
- Update `docker-compose.yml` and `start-services.sh` if build targets change.

### 8. CI/pre-push gates
- Check `pre-push-gates.sh` for stale `--cov-fail-under` values (floor is 70%).
- Ensure CI npm audit uses `--omit=dev`.

## Verification protocol — loop until green

```bash
./scripts/ci/quality-gates.sh
```

11 steps: repo lint → ruff → mypy → bandit → xenon → vulture → pytest+cov (≥70%) → pip-audit → frontend (vitest + eslint + tsc + vite build) → npm audit --omit=dev.

**Do not report success until this script exits 0.**

## ES pathway smoke test

```bash
./start-services.sh --elasticsearch-local
rag-params-finder run --config configs/elasticsearch/example-local.yaml
```

Verify all 4 retrieval methods complete: dense (kNN), sparse (BM25), hybrid (RRF), cross_encoder.

## Commit discipline

- One commit per logical fix.
- Conventional commits: `fix(elasticsearch):`, `docs(elasticsearch):`, `fix(ci):`, `fix(deps):`.
- Run quality gates before each commit.

## Exit criteria

1. All bulk insert / error handling bugs fixed and verified
2. sqlite run-state default works for ES and Redis backends
3. All ES config files and docs reference correct prerequisites
4. Quality gates: 11/11 pass locally (exit 0)
5. CI: all GitHub Actions checks green after push
6. ES smoke test: 4/4 retrieval methods complete
7. No regressions in backend or frontend test suites
8. Dependency audits clean (pip-audit + npm audit --omit=dev)
