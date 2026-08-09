# Slice 46 — Backend Coverage: 70.1% → 80–85%

**Theme**: 07-quality-craft | **Status**: 📋 PLANNED | **Priority**: Should

## Goal

Raise unit-tier backend coverage from 70.1% to 80–85% by adding ATDD-format tests
for the unit-testable gaps in `server/api`, `cli/`, `server/core/pipeline`,
`server/core/embedding`, and `server/core` modules.

The integration-only floor (Postgres/Mongo adapters, live retrieval) is ~300 statements;
these remain covered by the dedicated `postgres-integration` and `mongo-integration` CI jobs.
The realistic unit-tier ceiling before mocking adapters is ~85–88%.

## Acceptance Criteria

### Must

- [ ] `--cov-fail-under` raised from 70 → 80 in all four enforcement points
  (ci.yml, nightly.yml, quality-gates.sh, pyproject.toml)
- [ ] `backend_coverage_thresholds` floors raised proportionally (stmts/br/lines ≥ 78/65/78)
- [ ] All new tests follow ATDD format: module docstring (`Author`, `Created`, `Scope`),
  test docstring (`Scenario:`, `Slice:`, GWT prose), `### Given / ### When / ### Then` markers
- [ ] 468 existing tests continue to pass (zero regressions)

### Should

- [ ] `server/api` coverage ≥ 85% (currently 66.3%, ~148 missing stmts) —
  use FastAPI `TestClient`; mock `StorageBackend` via `app.dependency_overrides`
- [ ] `cli/` coverage ≥ 85% (currently 69.4%, ~186 missing stmts) —
  mock HTTP calls with `unittest.mock.patch`; use Typer `CliRunner`
- [ ] `server/core/pipeline` coverage ≥ 80% (currently 73.5%, ~180 missing stmts) —
  mock storage + embedding; test orchestrator branching paths
- [ ] `server/core/embedding` coverage ≥ 85% (currently 73.4%, ~117 missing stmts) —
  extend existing mocked embedder/rate-limiter tests

### Could

- [ ] `server (other)` coverage ≥ 70% (currently 62.7%, ~85 missing stmts)
  — `server/main.py` lifespan is integration-only; focus on `settings.py`, `scope_log.py`

## Gap by Category (2026-08-09 baseline)

| Category | Cover | Missing stmts | Reachable by unit tests |
|---|---|---|---|
| `server/db/postgres` | 43.5% | 218 | No — live DB required (CI integration jobs) |
| `server/core/retrieval` | 65.3% | 51 | Partly — search dispatch paths |
| `server/api` | 66.3% | 148 | Yes — FastAPI TestClient |
| `cli/` | 69.4% | 186 | Yes — Typer CliRunner + HTTP mocks |
| `server/core/pipeline` | 73.5% | 180 | Partly — orchestrator branching |
| `server/core/embedding` | 73.4% | 117 | Yes — already partially covered |
| `server/db/mongo` | 84.8% | 83 | No — live Atlas required (CI integration jobs) |
| `server/db/ports` | 89.5% | 12 | Yes |
| `server/core/guards` | 97.0% | 9 | Yes (near-complete) |
| `server/models` | 99.2% | 2 | Yes (near-complete) |

## Approach

1. `server/api` — FastAPI `TestClient` + `app.dependency_overrides` to inject a
   `MagicMock` `StorageBackend`; cover experiments CRUD, pause/resume/cancel/delete,
   sweep endpoint, best-config, explore, db-stats.
2. `cli/` — `typer.testing.CliRunner` for command integration; `patch` HTTP calls
   in `api_client.py`; cover error paths, format output, pagination.
3. `server/core/pipeline` — mock `StorageBackend`, embedder, and retriever;
   test `_run_sweep_inner` branching (cancel, error, partial, complete), `_run_bayesian_inner`.
4. `server/core/embedding` — extend `test_embedder_unit.py` and `test_rate_limiter_unit.py`
   for segment-splitting, contextualized paths, SIE dispatch.

## Pre-slice Checklist

- [ ] Read PROGRESS.md — confirm Slice 46 is next quality-craft slice
- [ ] Run `./scripts/ci/quality-gates.sh` — confirm zero regressions before starting
- [ ] Review `docs/plan/gate-evidence/test-gap-analysis-2026-08-07.md` for the 5 critical gaps

## Exit Criteria

- `uv run pytest … --cov=server --cov=cli --cov-fail-under=80` passes
- `check_backend_coverage_floors.py` passes with updated floors (78/65/78)
- All new tests follow ATDD format
- No existing tests broken
