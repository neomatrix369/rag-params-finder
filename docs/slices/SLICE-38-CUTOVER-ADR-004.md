# SLICE 38 — Side-by-Side Quality Gate + ADR-004 + Default Cutover

**MoSCoW:** MUST
**Target time:** ~3–4 h
**Status:** 📋 PLANNED
**Depends on:** 37
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../plan/PRD-supabase-pgvector-migration.md) §6.6, §9

---

## Slice Workflow Bundle

- Slice name: `slice-38-cutover-adr-004`
- Branch: `slice/38-cutover-adr-004`
- Files (expected):
  - `docs/adr/ADR-004-postgresql-pgvector-vector-store.md`
  - Update ADR-003 status → Superseded by ADR-004
  - `docs/plan/gate-evidence/` or `docs/` comparison notes (Mongo vs Postgres rankings)
  - Default `STORAGE_BACKEND` / docs recommend Postgres (Mongo retained for rollback)
  - Optional: remove dead Mongo-only docs paths only after comparison signed off
- Exit criteria: ADR-004 merged; side-by-side comparison documented; default backend Postgres with Mongo still selectable
- Commit pattern: `docs(slice-38): adr-004 pgvector cutover and quality comparison`

---

## Goal

Close the migration: document retrieval-quality comparison (equivalent quality, not identical scores), author ADR-004 superseding ADR-003, and switch the **documented default** to Postgres while keeping the Mongo adapter for rollback.

---

## Spec (GWT)

```
Scenario: Side-by-side comparison recorded
  Given the same persona question-set and corpus
  When dense/sparse/hybrid run on Mongo and Postgres
  Then a short comparison note exists (rank overlap / qualitative) before default flips

Scenario: ADR-004 supersedes ADR-003
  Given ADR-004 is authored
  When ADR-003 is opened
  Then its status is Superseded and links to ADR-004

Scenario: Default backend is Postgres; Mongo still works
  Given fresh .env.example
  When STORAGE_BACKEND defaults (or docs default) to postgres
  Then Mongo remains selectable via env for rollback
```

---

## Non-goals this slice

- Deleting the Mongo adapter (Won't until a later cleanup slice)
- Claiming byte-identical scores

---

## Before-Checks [GATE]

- [ ] Slices 32–37 ✅ PASSED
- [ ] Latency smoke vs ADR-003 baseline noted (pass/fail with numbers)

---

## After-Checks [GATE]

- [ ] All PRD §9 acceptance criteria checked or explicitly deferred with reason
- [ ] ADR-004 + ADR-003 status update
- [ ] Comparison artifact linked from TRAIL/PROGRESS
- [ ] Quality gates + doc audit (architecture, README, user-guide)
- [ ] Graphiti episode: cutover decision

## Gate Status

📋 PLANNED
