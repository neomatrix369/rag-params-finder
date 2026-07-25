# SLICE 32C — Storage Protocol Review Remediation

**MoSCoW:** MUST
**Target time:** ~2–3 h
**Status:** 📋 PLANNED
**Depends on:** [Slice 32 — Storage Backend Protocol + Mongo Adapter](SLICE-32-STORAGE-BACKEND-PROTOCOL.md)
**Blocks:** [Slice 32B — Gate Closure](SLICE-32B-STORAGE-PROTOCOL-GATE-CLOSURE.md) — do not run final `/nw-review` APPROVED / COMPLETE until 32C ✅ PASSED
**PR:** [#110](https://github.com/neomatrix369/rag-params-finder/pull/110) (same branch preferred)
**Parent:** Owns craft + architecture nw-review BLOCKERs that 32B (verification-only) does not cover

---

## Slice Workflow Bundle

- Slice name: `slice-32c-storage-protocol-review-remediation`
- Branch: `slice/32-storage-backend-protocol` (same PR #110) **or** `slice/32c-storage-protocol-review-remediation` if splitting PRs
- Files (expected):
  - `server/db/storage.py` — Protocol helper return-shape docstrings
  - `server/db/store_factory.py` — hoist or document lazy imports (`no-inline-imports`)
  - `server/db/mongo_store.py` — thin CRUD adapter after split
  - `server/db/mongo_stats.py` — NEW: stats/explore helpers extracted from `mongo_store`
  - `docs/plan/slices/SLICE-32-STORAGE-BACKEND-PROTOCOL.md` — dedupe After-Checks; index-seam decision note
  - `docs/plan/DECISIONS.md` / `docs/plan/slices/PROGRESS.md` Decision Log — index deferral + craft decisions
  - `tests/test_store_factory.py`, `tests/test_mongo_store_adapter.py` — stay green; import path updates only
  - `tests/test_mongo_store_acceptance.py` — commit/wire if in scope (see Before-Checks defaults)
- Exit criteria: Review craft/architecture BLOCKERs closed; Mongo default behavior unchanged; characterization tests green; ready for 32B gate closure
- Commit pattern: `docs(slice-32c): …` / `refactor(slice-32c): split mongo stats from storage adapter`

---

## Goal

Address **nw-review NEEDS_REVISION** findings that are *not* pure verification gates: checklist hygiene, index-seam honesty, Protocol contract documentation, god-adapter size (software-craft / thermo-nuclear), and inline-import rule compliance — with **zero user-visible Mongo behavior change**.

Verification gates (coverage %, mutation/waiver, full `quality-gates.sh`, final APPROVED → COMPLETE) remain owned by **Slice 32B**.

### Scope table (from review remediation plan)

| # | MoSCoW | Action | Done when |
|---|---|---|---|
| M1 | Must | Deduplicate After-Checks in parent SLICE-32 (no duplicate coverage/mutation/full-gates bullets) | Parent checklist has one row per gate |
| M2 | Must | Record index-provisioning seam decision (default: **defer** to Slice 36 — no `IndexBackend` in 32C) | Decision Log + parent/32C note; Slice 33 path explicit |
| M3 | Must | Document `StorageBackend` API-helper return shapes (`load_explore_source`, `list_results_for_experiment`, `get_experiment_db_stats`, `get_vector_db_stats_grouped`) | Docstrings name keys / tuple elements |
| M4 | Must | Split `MongoStorageBackend` / stats helpers — extract `mongo_stats.py`; keep adapter under craft class-size ceiling (~200 lines) | Adapter thin; stats delegated; tests green |
| M5 | Must | Satisfy `no-inline-imports`: hoist safe imports **or** document lazy-import why at each site | Rule met or documented exception |
| M6 | Must | Parent Gate Status remains honest until 32B closes COMPLETE | No false ✅ on parent before 32B |
| S1 | Should | Keep long stats methods in `mongo_stats` as named helpers (already mostly module-level) | Stats file readable; no behavior change |
| S2 | Should | ISP note on Protocol: explore/stats helpers marked as API-helper cluster (second port deferred) | Comment/section in `storage.py` |
| S3 | Could | Note `search` 7-param surface → param object deferred to Slice 34 | One-line note in Protocol or extending.md |

### Out of scope (Won't)

- Implementing Postgres adapters (33+)
- Adding `IndexBackend` Protocol (unless Before-Checks override to option B)
- Splitting `orchestrator.py` below 1k lines
- Final coverage/mutation/full-gates/COMPLETE close-out (→ **32B**)

---

## Spec (GWT)

```
Scenario: Parent After-Checks are unambiguous
  Given SLICE-32 After-Checks previously duplicated coverage/mutation/full-gates rows
  When the checklist is edited in this slice
  Then each gate appears once
  And remaining verification items still point to Slice 32B ownership

Scenario: Index seam is explicit for Postgres follow-on
  Given indexes.py / search_index_guard / search_index_plan remain Mongo-owned
  When Slice 32C records the index-seam decision
  Then either IndexBackend is deferred to a named later slice (default: 36)
    Or a thin IndexBackend Protocol is added with Mongo adapter + Postgres NotImplemented
  And the choice is logged in DECISIONS.md / PROGRESS Decision Log

Scenario: Port helpers are implementable without reverse-engineering Mongo
  Given StorageBackend exposes explore/stats helpers returning dict/tuple
  When a future Postgres adapter author reads the Protocol
  Then each helper documents expected keys and tuple element meaning

Scenario: Mongo adapter meets craft size ceiling after split
  Given MongoStorageBackend concentrated relocated stats logic (~390-line class)
  When stats/explore helpers move to mongo_stats (or equivalent collaborator)
  Then MongoStorageBackend is under the project class-size ceiling (~200 lines)
  And Mongo default CRUD/search behavior is unchanged (characterization tests green)

Scenario: Inline imports comply with project rule
  Given store_factory and mongo helpers use in-function imports
  When 32C completes
  Then imports are module-top OR each lazy import has a one-line documented reason
```

---

## Before-Checks [GATE]

- [x] Slice 32 implementation on `slice/32-storage-backend-protocol` (PR #110)
- [x] nw-review produced NEEDS_REVISION (architect + craft pass, 2026-07-25)
- [x] Slice 32B exists and stays verification-only (not expanded)
- [ ] Confirm defaults below (or override before `/nw-execute`):
  - **Index seam:** A — defer to Slice 36 (no IndexBackend in 32C)
  - **Acceptance tests:** include/commit `tests/test_mongo_store_acceptance.py` on the PR if it supports characterization after the split
  - **M4 split shape:** minimal — `mongo_stats.py` collaborator only (retriever may stay in `mongo_store.py`)

---

## TDD / Execution

1. Docs-first: M1 checklist dedupe + M2 decision log + M3 Protocol docstrings + M5 import comments
2. RED/GREEN only if tests fail after move — prefer characterization stay green (mechanical move)
3. Refactor M4: extract `mongo_stats.py`; thin `MongoStorageBackend`
4. `./scripts/quality-gates.sh --quick` green
5. Hand off to **32B** for full gates + coverage/mutation + final `/nw-review` APPROVED

---

## After-Checks [GATE]

- [ ] M1–M5 complete; S1–S2 done or explicitly deferred with note
- [ ] Specification coverage: every GWT clause ≥1 verification (test or documented checklist evidence)
- [ ] Branch coverage: no regression required beyond existing Slice 32 tests for this refactor; exclusions if any documented
- [ ] Mutation testing: N/A for docs/refactor slice — waiver note “behavior-preserving move; mutation owned by 32B”
- [ ] `./scripts/quality-gates.sh --quick` passes after refactor
- [ ] Parent SLICE-32 After-Checks deduped; index-seam decision recorded
- [ ] `MongoStorageBackend` class ≤ ~200 lines (or residual overage justified in Decision Log)
- [ ] No API/CLI/dashboard behavior change on Mongo default
- [ ] Doc audit: architecture/extending touch only if import paths change; N/A for user-guide (reason: internal remediation)
- [ ] PROGRESS + TRAIL: 32C → ✅ COMPLETE; 32B unblocked
- [ ] `/nw-review` craft/architecture blockers cleared (full APPROVED may wait for 32B evidence)

## Gate Status

📋 PLANNED — created 2026-07-25 via /enhanced-flow-planner Path B (Add 32C; keep 32B medium/gate-only)
