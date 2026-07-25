# SLICE 32B — Storage Protocol Gate Closure

**MoSCoW:** MUST
**Target time:** ~1–2 h
**Status:** 📋 PLANNED
**Depends on:** [Slice 32C — Storage Protocol Review Remediation](SLICE-32C-STORAGE-PROTOCOL-REVIEW-REMEDIATION.md) (and transitively Slice 32)
**Blocks:** Slice 33 (Supabase schema/CRUD) — do not start 33 until 32B ✅ PASSED
**PR:** [#110](https://github.com/neomatrix369/rag-params-finder/pull/110)
**Parent:** Owns remaining **verification** After-Checks (coverage, mutation/waiver, full gates, nw-review APPROVED → COMPLETE). Craft/architecture review BLOCKERs live in **32C**.

---

## Slice Workflow Bundle

- Slice name: `slice-32b-storage-protocol-gate-closure`
- Branch: `slice/32-storage-backend-protocol` (same PR branch — no new branch required) **or** `slice/32b-storage-protocol-gate-closure` if splitting PRs
- Files (expected):
  - `tests/test_mongo_store_acceptance.py` — extend/verify until branch coverage target met
  - `tests/test_store_factory.py`, `tests/test_mongo_store_adapter.py` — keep green
  - `docs/plan/gate-evidence/slice-32.json`, `docs/plan/gate-evidence/slice-32B.json`
  - `docs/plan/slices/SLICE-32-STORAGE-BACKEND-PROTOCOL.md` — parent After-Checks synced
  - `docs/plan/slices/PROGRESS.md`, `docs/plan/TRAIL.md` — 32 + 32B → ✅ COMPLETE
- Exit criteria: Coverage target met or exclusions documented; mutation run or waiver logged; full quality gates green; `/nw-review` APPROVED; parent Slice 32 marked COMPLETE
- Commit pattern: `test(slice-32b): …` / `docs(slice-32b): close gate — progress + evidence`

---

## Goal

Close Slice 32’s remaining **verification and governance gates** so the Storage/Retriever Protocol + Mongo adapter work can be marked ✅ COMPLETE and unblock Slice 33. No new production feature work — only evidence, review, and tracker close-out.

### Pending actions moved from Slice 32 After-Checks

| # | Action | Done when |
|---|---|---|
| 1 | Branch coverage on new modules (`storage`, `retriever_backend`, `store_factory`, `mongo_store`) — 100% target **or** exclusions documented with rationale | Coverage report committed or linked in gate-evidence; exclusions in slice Decision Log |
| 2 | Mutation testing on new port/factory modules **or** explicit feature-complete waiver | mutmut (or equivalent) report **or** DECISIONS.md waiver row |
| 3 | Full `./scripts/quality-gates.sh` (not only `--quick`) | Script exits 0; note date in gate-evidence |
| 4 | `/nw-review` APPROVED | Review verdict recorded; BLOCKERs fixed |
| 5 | Tracker close-out | Slice 32 + 32B → ✅ COMPLETE in PROGRESS + TRAIL; parent Gate Status PASSED; gate-evidence JSON written |
| 6 | PR #110 merge-ready | CI green + review satisfied; merge is optional follow-up (`/merge-pr-to-main`) after PASSED |

---

## Spec (GWT)

```
Scenario: New port modules meet coverage gate
  Given Slice 32 protocols and mongo_store are on the branch
  When coverage is measured for server.db.storage, retriever_backend, store_factory, mongo_store
  Then either each module meets the project branch-coverage target
    Or every miss is listed with a documented exclusion rationale in gate-evidence

Scenario: Mutation or waiver is explicit
  Given the Slice 32 port/factory modules are feature-complete for Mongo default
  When mutation testing is considered
  Then either survivors are within the project budget
    Or a dated waiver is logged in DECISIONS.md with reason (e.g. characterization-heavy adapter)

Scenario: Full quality gates pass
  Given the working tree includes all Slice 32 / 32B commits
  When ./scripts/quality-gates.sh runs (full mode)
  Then the script exits 0 with no regressions

Scenario: Review unlocks COMPLETE
  Given After-Checks 1–3 are satisfied
  When /nw-review is run on the Slice 32 implementation
  Then the verdict is APPROVED (or NEEDS_REVISION items are fixed and re-reviewed)
  And Slice 32 + 32B are marked ✅ COMPLETE in TRAIL and PROGRESS
```

---

## Before-Checks [GATE]

- [x] Slice 32 implementation landed on `slice/32-storage-backend-protocol` (PR #110)
- [x] `./scripts/quality-gates.sh --quick` already green (2026-07-25)
- [x] Acceptance coverage file present: `tests/test_mongo_store_acceptance.py`
- [ ] Confirm current coverage baseline for `mongo_store.py` after acceptance tests (record % in gate-evidence)

---

## TDD / Verification Execution

1. Measure coverage on the four new modules; close gaps or document exclusions
2. Run mutation (scoped) **or** write waiver to `DECISIONS.md`
3. Run full `./scripts/quality-gates.sh`
4. Dispatch `/nw-review`; address BLOCKERs
5. Write `docs/plan/gate-evidence/slice-32.json` + `slice-32B.json`; mark trackers COMPLETE

---

## After-Checks [GATE]

- [ ] Branch coverage: 100% target on `server/db/{storage,retriever_backend,store_factory,mongo_store}.py` **or** exclusions documented in gate-evidence + Decision Log
- [ ] Mutation testing: run for new port/protocol/factory modules **or** explicit waiver in `docs/plan/DECISIONS.md`
- [ ] `./scripts/quality-gates.sh` (full) passes
- [ ] `/nw-review` APPROVED
- [ ] `docs/plan/gate-evidence/slice-32.json` and `slice-32B.json` written (`gate_status: PASSED`)
- [ ] Parent [`SLICE-32-STORAGE-BACKEND-PROTOCOL.md`](SLICE-32-STORAGE-BACKEND-PROTOCOL.md) Gate Status → ✅ PASSED; header Status → ✅ COMPLETE
- [ ] `PROGRESS.md` + `TRAIL.md`: Slice 32 and 32B → ✅ COMPLETE; Slice 33 unblocked
- [ ] Doc audit: N/A for new user-facing docs (gate-closure only) — reason: verification/governance, no API/CLI change

## Gate Status

📋 PLANNED (created 2026-07-25 via /enhanced-flow-planner Path B — pending Slice 32 After-Checks)
