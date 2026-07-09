# SLICE 37 — Local Postgres + Hosted Supabase Parity + Boot Reconciliation

**MoSCoW:** MUST
**Target time:** ~3–4 h
**Status:** 📋 PLANNED
**Depends on:** 36
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../plan/PRD-supabase-pgvector-migration.md) §5.1.9–5.1.10

---

## Slice Workflow Bundle

- Slice name: `slice-37-postgres-local-cloud-parity`
- Branch: `slice/37-postgres-local-cloud-parity`
- Files (expected):
  - `start-services.sh` / `scripts/lib/compose.sh` — `--local-postgres` or extend `--local` when `STORAGE_BACKEND=postgres`
  - `docker-compose.yml` — pgvector profile
  - `server/core/startup_reconciliation.py` — Postgres queries via Protocol
  - `docs/user-guide/postgres-setup.md` (or supabase-setup.md)
  - `configs/example-postgres-local.yaml`
  - `tests/test_startup_reconciliation_postgres.py`
- Exit criteria: One-command local Postgres stack; hosted Supabase URI works; orphaned `running` → `interrupted`/`partial` on boot
- Commit pattern: `feat(slice-37): postgres local cloud parity and boot reconciliation`

---

## Goal

Mirror Atlas cloud vs Atlas Local DX for Postgres: local Docker pgvector and hosted Supabase behave identically from CLI/dashboard; boot reconciliation works on both.

---

## Spec (GWT)

```
Scenario: Local stack one-command start
  Given Docker available
  When `./start-services.sh` local-postgres mode runs
  Then server + dashboard + pgvector are healthy and STORAGE_BACKEND=postgres

Scenario: Hosted Supabase URI
  Given a valid Supabase DATABASE_URL with TLS
  When the server boots
  Then pool connects and a smoke sweep can complete

Scenario: Boot reconciliation on Postgres
  Given an experiment left in running state
  When the server restarts
  Then orphaned in-flight runs are marked interrupted/partial as today
```

---

## Before-Checks [GATE]

- [ ] Slice 36 ✅ PASSED
- [ ] Supabase project credentials available for cloud smoke (or documented skip)

---

## After-Checks [GATE]

- [ ] Local + cloud smoke documented
- [ ] Boot reconciliation tests for Postgres path
- [ ] Mongo `--local` path still works
- [ ] Coverage + quality gates
- [ ] Doc audit: README + user-guide + CLAUDE.md env table

## Gate Status

📋 PLANNED
