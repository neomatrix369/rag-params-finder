# Slice 41 — Documentation Plan/Slices SSOT Alignment

**Status**: 📋 PLANNED

**MoSCoW**: Should

**Branch**: `slice/41-documentation-ssot-alignment`

**Depends on**: none

**Target time**: ~45–60 min

## Problem

The repository has both:

- `docs/plan/*` (planning artifacts, policy, and process records), and
- `docs/slices/*` (per-slice specs plus the SSOT `PROGRESS.md` progress tracker).

There is still occasional confusion between these folders, and previous continuity work left repeated references that can be misread as duplicate progress trackers.

This slice removes ambiguity by explicitly documenting the role boundary and updating the active tracking artifacts.

## Goal

Make documentation ownership explicit so every contributor can tell:

- which files are canonical for execution status (`docs/slices/PROGRESS.md`),
- which files are canonical for plan decisions and continuity (`docs/plan`),
- and where to find this slice.

## Acceptance criteria

- [ ] `docs/slices/SLICE-41-DOCS-PLAN-SLICES-SSOT.md` exists with a clear problem, goal, and behavioral criteria.
- [ ] `docs/slices/PROGRESS.md` includes this slice in its Quick Status and Plan Track entries with `📋 PLANNED`.
- [ ] `docs/plan/TRAIL.md` includes this slice row, same status, and a non-disruptive execution-note update.
- [ ] `docs/plan/DECISIONS.md` records the boundary decision and the rationale.
- [ ] No plan execution sequencing is changed for the migration path (`32 → 33 → 34 → 35 → 36 → 37 → 38`).

## Behavioral scenarios (GWT)

```text
Scenario: Canonical status tracker is obvious
  Given an engineer opens docs/plan and docs/slices
  When they search for current execution status
  Then they can identify `docs/slices/PROGRESS.md` as the SSOT status tracker
  And they can find slice-level detail in `docs/slices/SLICE-*.md`

Scenario: Canonical boundary for planning records is preserved
  Given a future implementation decision is made
  When the decision is recorded in docs/plan/DECISIONS.md
  Then the execution artifacts in docs/slices are updated without duplicating `docs/plan/PROGRESS.md`
  And there is no active `docs/plan/PROGRESS.md` source of truth conflict

Scenario: Planner slice list remains stable
  Given slices 32–38 are required before migration cutover
  When this slice is complete
  Then the execution order in `docs/plan/TRAIL.md` still presents `32 → 33 → 34 → 35 → 36 → 37 → 38` as the critical path
```

## Implementation details

- Do not introduce new runtime code.
- Keep changes limited to planning artifacts (`docs/slices/PROGRESS.md`, `docs/plan/TRAIL.md`, `docs/plan/DECISIONS.md`).
- Use a neutral wording that avoids implying a second SSOT.

## Files to update

- `docs/slices/SLICE-41-DOCS-PLAN-SLICES-SSOT.md` (new)
- `docs/slices/PROGRESS.md`
- `docs/plan/TRAIL.md`
- `docs/plan/DECISIONS.md`
