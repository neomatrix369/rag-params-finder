# Slice 31 — Experiment List Filter

**Status**: 📋 PLANNED
**Branch**: `slice/31-experiment-list-filter`
**Estimated time**: ~2 h
**MoSCoW**: Should (navigability at scale — becomes pain point at 20+ experiments)

## Problem

`ExperimentsScreen` lists all experiments newest-first with no way to narrow the view. With a growing set of runs (different configs, dates, providers), finding a specific experiment requires scrolling through the full paginated list. There is no:
- Status filter (show only `running`, `complete`, `failed`, etc.)
- Name/ID search

## Goal

Add a lightweight filter bar above the experiments table — status dropdown + free-text search — so operators can locate specific experiments without pagination scrolling.

## Acceptance Criteria

### Status filter (Must)
- [ ] A "Status" dropdown appears above the experiments table with options: All, Running, Complete, Failed, Partial, Cancelled, Paused
- [ ] Selecting a status filters the displayed rows to that status only
- [ ] "All" (default) shows the full list
- [ ] Pagination resets to page 1 when filter changes
- [ ] Filter state is NOT persisted in localStorage (always resets to "All" on page load)

### Name/ID search (Should)
- [ ] A text input labelled "Search" appears next to the status dropdown
- [ ] Typing filters rows whose `experiment_id` or `config.name` contains the search string (case-insensitive)
- [ ] Search is client-side (no new API calls)
- [ ] Clearing the input restores the full list
- [ ] Search and status filter compose: both can be active simultaneously

### Layout (Should)
- [ ] Filter bar is visible on both desktop and mobile (responsive, wraps gracefully)
- [ ] When zero results match, show "No experiments match your filter" (not a blank table)

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/components/ExperimentsScreen.tsx` | Status dropdown + search input + client-side filter logic |
| `frontend/src/types/index.ts` | No new types needed — filters operate on existing `ExperimentSummary` |

## GWT Scenarios (tests — component)

```
Scenario: filter by status "failed" shows only failed experiments
  Given the list contains one complete and one failed experiment
  When user selects "Failed" from the status dropdown
  Then only the failed experiment row is shown

Scenario: search by ID narrows the list
  Given experiments with IDs "abc-2026" and "xyz-2026"
  When user types "abc" in the search box
  Then only "abc-2026" is shown

Scenario: combined filter and search
  Given a "complete" experiment "run-abc" and a "failed" experiment "run-xyz"
  When user selects "Complete" and types "abc"
  Then only "run-abc" is shown

Scenario: no-match state
  Given no experiment has status "running"
  When user selects "Running"
  Then the table body shows "No experiments match your filter"
  And pagination controls are hidden or disabled

Scenario: filter resets on page load
  Given user previously selected "Failed"
  When user navigates away and returns to the experiments page
  Then the status filter shows "All"

Scenario: pagination resets when filter changes
  Given user is on page 2 of the experiments list
  When user selects a status filter
  Then pagination resets to page 1
```

> *Tests execute through `ExperimentsScreen` (RTL user interactions as the driving port); no direct store/domain imports.*

## Session bootstrap
> Re-read CLAUDE.md before starting — use values there, not hardcoded commands here.
- **Runtime source**: → CLAUDE.md § Environment / Development Commands
- **Test source**: → CLAUDE.md § Testing / Quality Gates Baseline
- **Load first**: CLAUDE.md → docs/plan/invariants.md → this stub

## Context
> Read before any implementation. Do not rely on conversation history alone.
- **Stage objective**: Experiment list status dropdown + name/ID search for navigability at scale
- **Depends on**: none
- **Global invariants**: → `docs/plan/invariants.md`
> Executor may diverge from plan if new evidence warrants — document deviations in PROGRESS.md before marking PASSED.

## Non-goals
> Out of scope for this slice — do not implement here.
- Server-side pagination redesign; Search Explorer filters (Slice 30/11)

## Output contract
> Observable shape of completion (shape only — not exact file paths).
- **Baseline**: note current TRAIL/PROGRESS status and `git status` before edits
- List screen filters client-side (or agreed API); empty/no-match state covered by tests

## Before-Checks

- [ ] `npm run typecheck` passes on main
- [ ] `npm run build` passes on main
- [ ] Branch `slice/31-experiment-list-filter` created from latest main

## After-Checks

- [ ] `./scripts/quality-gates.sh` pass
- [ ] Specification coverage: every GWT scenario has ≥1 test; no-match state covered
- [ ] Complexity evidence: policy `reporting` for FE (ESLint complexity via `bash scripts/ci/complexity-report.sh` → `.reports/complexity/pr-body.md`); backend xenon `enforcing` E/C/C when `server/`/`cli/` touched
- [ ] Branch coverage: 100% target for filter utility functions; exclusions documented (test-writing-craft-quality.mdc §12)
- [ ] Mutation testing: survival budget met if slice is feature-complete (§23)
- [ ] Manual: with 5+ experiments of mixed status → confirm filter narrows list correctly
- [ ] Manual: search + status filter compose correctly (not OR — both must match)

## Commits

```
feat(slice-31): add status filter and name/ID search to experiments list
```

### Closing Gates
- [ ] `nw-at-completeness-check` — AT completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline review (slice close gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data flow review (gate #9, parallel, for slices with runtime data flow changes)
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)
