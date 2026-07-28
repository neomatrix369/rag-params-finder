# Slice 40 — Documentation Plan/Slices SSOT Alignment

**Status**: ✅ COMPLETE

**MoSCoW**: Should (boundary + theme index); folder moves are part of this slice’s Should once taxonomy is locked (#162)

**Branch**: `slice/40-documentation-ssot-alignment`

**Depends on**: none (independent of migration path 32→38)

**Target time**: ~2–3 h (boundary docs + `git mv` + link rewrite)

**Decision**: DECISIONS **#162**

**Gate evidence**: [`docs/plan/gate-evidence/slice-40.json`](../../gate-evidence/slice-40.json)

## Problem

**Previously**, the repository had both:

- `docs/plan/*` (planning artifacts, policy, and process records), and
- `docs/plan/slices/*` (per-slice specs plus the SSOT `PROGRESS.md` progress tracker),

with occasional confusion between these folders. As the slice catalog grew (~40 specs), a flat `SLICE-*.md` directory also became hard to scan by delivery wave.

**Now**, ownership is explicit and specs cluster under numbered theme folders `01`–`07` that reflect delivery-wave order (see [`README.md`](../README.md)).

## Goal

Make documentation ownership and navigation explicit so every contributor can tell:

- which files are canonical for execution status (`docs/plan/slices/PROGRESS.md`),
- which files are canonical for plan decisions and continuity (`docs/plan`),
- which **theme folder** holds a slice spec (delivery-wave numbers),
- and where to find this slice.

**Index rule:** Theme numbers = delivery wave order; slice numbers = identity (unchanged in filenames).

## MoSCoW

| Priority | Scope |
|----------|--------|
| **Must** | Document `docs/plan` vs `docs/plan/slices` boundary; keep `PROGRESS.md` as sole status SSOT; record #162 |
| **Should** | Add `docs/plan/slices/README.md` theme index; `git mv` specs into numbered theme folders; rewrite living links (PROGRESS, TRAIL, HANDOFF, CLAUDE, AGENTS, architecture, CHANGELOG as needed) |
| **Could** | Optional “By theme” section in PROGRESS Quick Status (links only — no duplicate notes) |
| **Won’t** | Put `PROGRESS.md` inside a theme folder; date-named theme folders (`2026-07/`); split mid-chain families (e.g. 32 / 32C / 32B); renumber slices; move `docs/plan/gate-evidence/` into themes; change migration execution order `32 → … → 38` |

## Numbered theme map (DECIDED — #162)

Prefix is **theme chronology**. Filenames keep **`SLICE-<id>-…md`**.

| # | Folder | Wave | Specs (identity) |
|---|--------|------|------------------|
| 01 | `01-core-pipeline/` | First skateboard → sweep / recovery | 01–07, 10, 16, 18, 29 |
| 02 | `02-dashboard/` | List / detail / explorer UX + export | 08–09*, 11, 28, 30–31, 39 |
| 03 | `03-platform/` | Compose, ports, Atlas local, toolchain, Docker build | 14, 20, 24–25B, 42 |
| 04 | `04-sie/` | SIE skateboard → bicycle | 21–23 |
| 05 | `05-storage/` | Ports → Postgres cutover + Mongo residuals | 19, 26–27, 32–38, 43 |
| 06 | `06-bayesian/` | Optuna track | 41A–C |
| 07 | `07-quality-craft/` | Docs SSOT + coverage floors + module themes | 40, 44–45 |

\* Early dashboard work may live only in PROGRESS narrative (no standalone `SLICE-08` file) — place any matching specs that exist; do not invent missing specs.

**Layout after Should:**

```text
docs/plan/slices/
  PROGRESS.md                 # status SSOT (flat — Won’t nest)
  README.md                   # theme index → folders
  01-core-pipeline/
  02-dashboard/
  03-platform/
  04-sie/
  05-storage/
  06-bayesian/
  07-quality-craft/
docs/plan/gate-evidence/      # flat by slice id (unchanged)
```

## Acceptance criteria

- [x] Spec documents plan vs slices boundary + theme map + Won’ts (this file).
- [x] `DECISIONS.md` records #162 (boundary + numbered themes + Won’ts).
- [x] `PROGRESS.md` Quick Status + Plan Track mention theme folders / #162; Decision Log row added.
- [x] `TRAIL.md` Slice 40 row notes theme clustering (#162); migration path `32 → … → 38` unchanged.
- [x] **Should:** `README.md` theme index exists; specs live under `0N-<theme>/` via `git mv`; living links resolve.
- [x] No runtime code changes (planning artifacts only for skateboard step 1).
- [x] Gate evidence paths stay `docs/plan/gate-evidence/slice-N.json` (flat) — unchanged; move still Won’t.

## Behavioral scenarios (GWT)

```text
Scenario: Canonical status tracker is obvious
  Given an engineer opens `docs/plan` and `docs/plan/slices`
  When they search for current execution status
  Then they can identify `docs/plan/slices/PROGRESS.md` as the SSOT status tracker
  And they can find slice-level detail under `docs/plan/slices/0N-<theme>/SLICE-*.md`

Scenario: Theme numbers show delivery wave order
  Given the theme folders are numbered 01–07
  When a contributor lists `docs/plan/slices/`
  Then folder sort order matches delivery-wave chronology
  And slice identity remains in the `SLICE-<id>-` filename

Scenario: Status SSOT is not nested in a theme
  Given theme folders exist
  When looking for PROGRESS.md
  Then it remains at `docs/plan/slices/PROGRESS.md` (not under `0N-*`)

Scenario: Storage family stays together
  Given slices 32, 32C, and 32B form one Must chain
  When specs are clustered
  Then all three live under `05-storage/`

Scenario: Canonical boundary for planning records is preserved
  Given a future implementation decision is made
  When the decision is recorded in `docs/plan/DECISIONS.md`
  Then execution artifacts in `docs/plan/slices/` update without inventing `docs/plan/PROGRESS.md`
  And there is no second status SSOT

Scenario: Planner migration path remains stable
  Given slices 32–38 are the storage critical path
  When this slice is complete
  Then `docs/plan/TRAIL.md` still presents `32 → 32C → 32B → 33 → 34 → 35 → 36 → 37 → 38` as the critical path
```

## Implementation details

- Planning / docs only — no runtime code.
- Prefer **`git mv`** for history.
- Rewrite **living** links; leave historical commit messages alone.
- Historical COMPLETE slice narrative sections inside `PROGRESS.md` may keep relative links updated in the same PR.
- Skateboard order: (1) land #162 + this expanded stub + tracker rows → (2) `README.md` + `git mv` + link rewrite → (3) Could PROGRESS “By theme” section.

## Files to update

| Path | Role |
|------|------|
| `docs/plan/slices/07-quality-craft/SLICE-40-DOCS-PLAN-SLICES-SSOT.md` | This spec (moves into `07-quality-craft/` with peers) |
| `docs/plan/DECISIONS.md` | #162 |
| `docs/plan/slices/PROGRESS.md` | Status notes + Decision Log |
| `docs/plan/TRAIL.md` | Slice 40 row + link paths after move |
| `docs/plan/slices/README.md` | Theme index (Should) |
| `docs/plan/HANDOFF.md` | Key decision #162 |
| Living refs | CLAUDE / AGENTS / architecture / CHANGELOG / HANDOFF as needed after `git mv` |

## Before-Checks [GATE]

- [x] Slice is planning-only and does not require runtime code changes
- [x] `TRAIL.md` row for this slice exists with status `📋 PLANNED`
- [x] `slices/PROGRESS.md` contains a Quick Status row for this slice with `📋 PLANNED`
- [x] Theme map + Won’ts recorded as DECISIONS #162 (**DECIDED**; folder moves **IMPLEMENTED**)

## After-Checks [GATE]

- [x] Theme folders + README exist; every `SLICE-*.md` (except none left flat except PROGRESS/README) lives under `0N-*`
- [x] Living links from TRAIL / PROGRESS / HANDOFF / agent entry points resolve
- [x] `PROGRESS.md` still sole status SSOT at flat path
- [x] `gate-evidence/` unchanged layout
- [x] Migration execution order in TRAIL unchanged
- [x] Spec / GWT coverage: planning artifacts reviewed against acceptance criteria (no product test suite — N/A runtime mutation)
- [x] `bash scripts/ci/repo-lint.sh` passes (markdown)
- [x] nw-review (docs/planning) — APPROVED 2026-07-28; blocking=0; see Review section below
- [x] `docs/plan/gate-evidence/slice-40.json` — `gate_status: PASSED` (verify-slice 2026-07-28)

## Gate Status

✅ **COMPLETE** — Should theme folders + SSOT boundary landed; nw-review APPROVED; gate evidence PASSED.

---

## Review

**Date**: 2026-07-28
**Reviewer**: nw-documentarist-reviewer
**Verdict**: **APPROVED**
**Blocking Issues**: 0
**Summary**: Implementation complete and correct. All 43 specs moved into themed folders `01–07` via git-preserved `git mv`; PROGRESS.md and README.md both accurately updated with theme index and navigational boundaries; DECISIONS.md #162 recorded; living links rewritten across all entry points; SSOT integrity maintained (flat PROGRESS, no nested status tracker). Diataxis fit of README is Reference (task-oriented task finder), Boundary is Tutorial (how PROGRESS and specs live together). Minor praise: execution was precise, link rewrites systematic, spec honesty about AC checklist matching implementation (all checkboxes reflect actual landing).

**Praise**
- ✅ **Methodical link rewrite**: every reference to `SLICE-NN` in PROGRESS, docs/README, TRAIL, HANDOFF, AGENTS, CLAUDE updated to `0N-<theme>/SLICE-NN` with no typos (spot-checked >20); git history preserved by using `git mv`.
- ✅ **README.md captures Diataxis exactly**: "Finding a slice" section is a Navigation/How-To hybrid; "Boundary" section is prescriptive Tutorial; clean, actionable.
- ✅ **AC checklist has zero false-positive marks**: each `[x]` corresponds to verifiable artifact (folders exist, README exists, PROGRESS has theme mention + Decision Log row, TRAIL row updated, no flat specs left, gate-evidence flat as Won't).

**Recommendations** (all low/informational)
- No blocking issues detected.
- No high-severity issues detected.
- All Won'ts honored (gate-evidence flat, PROGRESS flat, no date folders, storage family 32/32C/32B together, migration order 32→38 unchanged).
- Suggestion (INFORMATIONAL): spec itself still contains Problem prose referencing "flat `SLICE-*.md` directory" (lines 17–24) and "as the slice catalog grew (~40 specs)" — this reads as historical narrative of the problem that was just solved. Not a gate failure, but consider a brief editorial pass: "**Previously**: flat…; **Now**: numbered theme folders…" to clarify this is a closure note, not current state. (Minor polish — does not block COMPLETE.)

**Evidence**
- Flat specs count: 0 left at `docs/plan/slices/` root (`find` confirms).
- Themed specs: 43 total distributed `01-core-pipeline`(10) + `02-dashboard`(5) + `03-platform`(6) + `04-sie`(3) + `05-storage`(13) + `06-bayesian`(3) + `07-quality-craft`(3) = 43 ✓
- Stale flat refs in docs/: 0 detected in contributor-guide (`grep -r "SLICE-" … | wc -l`).
- Decision #162 in DECISIONS.md: line 165, recorded 2026-07-28, captures theme clustering + Won'ts.
- PROGRESS.md updates: Quick Status line updated; "By theme" index section added; all ~40 spec links in the table rewritten to themed paths.
- TRAIL.md: Slice 40 row links updated; migration order 32→38 preserved.
- HANDOFF.md: Slice 40 status updated; #162 referenced.
- `docs/README.md` diff: 4 link references updated, Maintainers status changed from "DECIDED" to "IMPLEMENTED", agent row updated, table row synced.
- Gate evidence: `docs/plan/gate-evidence/` remains flat; unchanged layout.

**Diataxis / Documentation Fit**
- **slices/README.md**: Reference (task finder) + brief Tutorial (boundary rules). Correct fit for artifact. ✓
- **SLICE-40 spec itself**: Planning artifact (proposal + boundary doc hybrid). Fit is appropriate for approval.
- **No second SSOT**: PROGRESS.md remains sole status tracker; no nested `PROGRESS-by-theme.md` or duplicate tracking. ✓

**Spec vs. Implementation Alignment**
- All AC checkboxes ✓ correspond to artifacts on disk.
- GWT scenarios all satisfied:
  1. Canonical status tracker obvious → PROGRESS.md remains at flat path ✓
  2. Theme numbers show wave order → folder sort order `01–07` ✓
  3. Status SSOT not nested → PROGRESS at `docs/plan/slices/PROGRESS.md` not `0N-*/` ✓
  4. Storage family together → 32, 32C, 32B all in `05-storage/` ✓
  5. Boundary preserved → `docs/plan/` and `docs/plan/slices/` roles remain distinct ✓
  6. Migration path stable → TRAIL.md `32 → … → 38` order unchanged ✓
