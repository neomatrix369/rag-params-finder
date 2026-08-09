# Slice 47 — Complexity Gate: E/C/C → B/A/A (Xenon)

**Theme**: 07-quality-craft | **Status**: 📋 PLANNED | **Priority**: Should

## Goal

Tighten the Xenon hard complexity gate from the current baseline `E/C/C`
(`--max-absolute E --max-modules C --max-average C`) to the target `B/A/A`
(`--max-absolute B --max-modules A --max-average A`) by refactoring the known
high-complexity functions.

The gate was wired at E/C/C in `chore/project-hygiene-full` (2026-08-09) to block
new regressions. This slice removes the existing violations.

## Current Violations (2026-08-09)

### E-rank blocks (CC ≥ 21) — must reach B (CC ≤ 10)

| File | Function | CC | Strategy |
|---|---|---|---|
| `server/core/pipeline/orchestrator.py:570` | `_run_sweep_inner` | 40 | Extract phase handlers into separate private methods |
| `server/api/experiments_lifecycle.py:122` | `_normalize_stale_running_status` | 32 | Extract status-derivation into a lookup/dispatch table |

### D-rank blocks (CC 16–20)

| File | Function | CC |
|---|---|---|
| `server/core/results_analyzer.py:44` | `analyze_results` | D |
| `server/core/pipeline/orchestrator.py:306` | `_finalise_bayesian_experiment` | D |
| `server/core/pipeline/startup_reconciliation.py:45` | `_reconcile_one` | D |
| `cli/display.py:188` | `_print_summary` | D |

### C-rank blocks (CC 11–15) and B-rank modules

| File | Issue |
|---|---|
| `server/settings.py:118` | `parse_cors_origins` — C block |
| `server/core/atlas_storage.py:243,260` | `_disk_size_gb`, `_instance_size_name` — C blocks; module rank B |
| `server/core/pipeline/orchestrator.py:119,812` | `_run_bayesian_inner`, `_run_single` — C blocks; module rank B |
| `server/core/pipeline/startup_reconciliation.py:115` | `_derive_experiment_status` — C block; module rank C |
| `server/core/chunkers/semantic.py` | module rank B |
| `server/core/chunkers/__init__.py` | module rank B |
| `server/core/embedding/sie_embedder.py` | module rank B |
| `server/core/guards/search_index_guard.py:131` | `validate_experiment_search_indexes` — C block; module rank B |
| `server/api/experiments_lifecycle.py:71` | `_ensure_bayesian_summary` — C block; module rank B |
| `server/db/postgres/postgres_stats.py:272` | `get_vector_db_stats_grouped` — C block |
| `server/db/mongo/mongo_stats.py:56,254` | `_mongodb_cluster_storage_mb`, `_summary_db_stats_for_experiment` — C blocks |
| `server/db/mongo/indexes.py:276` | `_wait_for_indexes_ready` — C block |
| `cli/display.py` | `_print_summary` — D block; module rank C |
| `cli/api_client.py:25` | `_response_detail` — C block |
| `cli/indexes_cmd.py:118` | `indexes_reset` — C block; module rank B |

## Tightening Path

| Phase | Threshold | Blocking violations to fix |
|---|---|---|
| Baseline (current) | E/C/C | none — already wired |
| Phase 1 | D/C/C | Fix 2 E-rank blocks |
| Phase 2 | C/B/B | Fix 4 D-rank blocks; module ranks C → B |
| Phase 3 (target) | B/A/A | Fix all C-rank blocks; all modules → A |

## Acceptance Criteria

### Must

- [ ] `xenon --max-absolute B --max-modules A --max-average A server/ cli/` exits 0
- [ ] All four enforcement points updated (ci.yml, nightly.yml, quality-gates.sh, pre-push-gates.sh)
- [ ] No public interface changes (internal refactor only)
- [ ] All 468+ existing tests pass after refactoring

### Should

- [ ] Each extracted function/class has its own unit test (refactor → test)
- [ ] E-rank functions refactored first (highest risk, largest delta)

## Refactoring Strategy for E-rank Functions

### `_run_sweep_inner` (CC=40)

Core sweep execution loop. High CC from nested phase dispatching + error handling + cancel checks.
- Extract each pipeline phase into `_run_phase_X(run_id, config, cancel_check)` callables
- Main function becomes a loop over phase callables — reduces to CC ~8

### `_normalize_stale_running_status` (CC=32)

Status normalisation from multi-field run states.
- Replace nested if/elif with a `STATUS_RULES: list[tuple[Callable, str]]` dispatch table
- Each rule is a predicate + resulting status — reduces to CC ~5

## Pre-slice Checklist

- [ ] Read PROGRESS.md — confirm Slice 47 is the complexity-tighten slice
- [ ] Run `xenon --max-absolute E --max-modules C --max-average C server/ cli/` passes (baseline)
- [ ] Run `./scripts/ci/quality-gates.sh` — confirm zero regressions before starting

## Exit Criteria

- `xenon --max-absolute B --max-modules A --max-average A server/ cli/` exits 0
- All four enforcement points use `B/A/A`
- `./scripts/ci/quality-gates.sh` passes
