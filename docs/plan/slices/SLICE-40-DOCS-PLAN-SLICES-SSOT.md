# Slice 40 — Documentation Plan/Slices SSOT Alignment

**Status**: 📋 PLANNED

**MoSCoW**: Should

**Branch**: `slice/40-documentation-ssot-alignment`

**Depends on**: none

**Target time**: ~45–60 min

## Problem

The repository has both:

- `docs/plan/*` (planning artifacts, policy, and process records), and
- `docs/plan/slices/*` (per-slice specs plus the SSOT `PROGRESS.md` progress tracker).

There is still occasional confusion between these folders, and previous continuity work left repeated references that can be misread as duplicate progress trackers.

This slice removes ambiguity by explicitly documenting the role boundary and updating the active tracking artifacts.

## Goal

Make documentation ownership explicit so every contributor can tell:

- which files are canonical for execution status (`docs/plan/slices/PROGRESS.md`),
- which files are canonical for plan decisions and continuity (`docs/plan`),
- and where to find this slice.

## Acceptance criteria

- [ ] `docs/plan/slices/SLICE-40-DOCS-PLAN-SLICES-SSOT.md` exists with a clear problem, goal, and behavioral criteria.
- [ ] `docs/plan/slices/PROGRESS.md` includes this slice in its Quick Status and Plan Track entries with `📋 PLANNED`.
- [ ] `docs/plan/TRAIL.md` includes this slice row, same status, and a non-disruptive execution-note update.
- [ ] `docs/plan/DECISIONS.md` records the boundary decision and the rationale.
- [ ] No plan execution sequencing is changed for the migration path (`32 → 33 → 34 → 35 → 36 → 37 → 38`).

## Behavioral scenarios (GWT)

```text
Scenario: Canonical status tracker is obvious
  Given an engineer opens `docs/plan` and `docs/plan/slices`
  When they search for current execution status
  Then they can identify `docs/plan/slices/PROGRESS.md` as the SSOT status tracker
  And they can find slice-level detail in `docs/plan/slices/SLICE-*.md`

Scenario: Canonical boundary for planning records is preserved
  Given a future implementation decision is made
  When the decision is recorded in `docs/plan/DECISIONS.md`
  Then the execution artifacts in `docs/plan/slices/` are updated without duplicating `docs/plan/PROGRESS.md`
  And there is no active `docs/plan/PROGRESS.md` source of truth conflict

Scenario: Planner slice list remains stable
  Given slices 32–38 are required before migration cutover
  When this slice is complete
  Then the execution order in `docs/plan/TRAIL.md` still presents `32 → 33 → 34 → 35 → 36 → 37 → 38` as the critical path
```

## Implementation details

- Do not introduce new runtime code.
- Keep changes limited to planning artifacts (`docs/plan/slices/PROGRESS.md`, `docs/plan/TRAIL.md`, `docs/plan/DECISIONS.md`).
- Use a neutral wording that avoids implying a second SSOT.

## Files to update

- `docs/plan/slices/SLICE-40-DOCS-PLAN-SLICES-SSOT.md` (new)
- `docs/plan/slices/PROGRESS.md`
- `docs/plan/TRAIL.md`
- `docs/plan/DECISIONS.md`

## Before-Checks [GATE]

- [ ] Slice is planning-only and does not require runtime code changes
- [ ] `TRAIL.md` row for this slice exists with status `📋 PLANNED`
- [ ] `slices/PROGRESS.md` contains a `Quick Status` row for this slice with `📋 PLANNED`

## After-Checks [GATE]

- [ ] Specification coverage: every GWT clause has at least one test (BDD/GWT-first); essential error and timeout paths covered
- [ ] Branch coverage: target 100% where practical; document any exclusions
- [ ] Mutation testing run if slice is feature-complete: mutation budget ≤10% survivors
- [ ] Coverage + quality gates
- [ ] `TRAIL.md` and `slices/PROGRESS.md` entries remain synchronized and still show this slice as planned
- [ ] `DECISIONS.md` records at least one boundary decision row
