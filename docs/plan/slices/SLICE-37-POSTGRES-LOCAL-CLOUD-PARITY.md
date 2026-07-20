# SLICE 37 — Supabase Local + Hosted Parity + Boot Reconciliation

**MoSCoW:** MUST
**Target time:** ~3–4 h
**Status:** 📋 PLANNED
**Depends on:** 36
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../plan/PRD-supabase-pgvector-migration.md)

---

## Slice Workflow Bundle

- Slice name: `slice-37-supabase-local-cloud-parity`
- Branch: `slice/37-supabase-local-cloud-parity`
- Files (expected):
  - `start-services.sh` / `scripts/lib/compose.sh` — `--local-postgres` or `STORAGE_BACKEND=postgres` path
  - `docker-compose.yml` — pgvector profile (extends Slice 33 minimal setup)
  - `server/core/startup_reconciliation.py` — Postgres via StorageBackend
  - `docs/user-guide/supabase-setup.md` — **hosted Supabase** setup (pooler, TLS, pause)
  - `configs/example-supabase-local.yaml`
  - `tests/test_startup_reconciliation_postgres.py`
- Exit criteria: One-command local stack; hosted Supabase smoke; boot reconciliation on both
- Commit pattern: `feat(slice-37): supabase local and hosted parity`
- **Doc exit:** `/sync-docs` — user-guide footprint (supabase-setup, getting-started, troubleshooting, docs/README, README, development.md)

---

## Goal

Mirror Atlas cloud vs Atlas Local DX for **Supabase**: local Docker pgvector and hosted Supabase project behave identically from CLI/dashboard.

---

## Supabase connection requirements (document in user-guide)

| Topic | Requirement |
|---|---|
| **URI** | `DATABASE_URL` from Supabase dashboard (Settings → Database) |
| **Pooler** | Prefer **Session mode** pooler for pgvector + prepared statements; document if Transaction mode breaks HNSW queries |
| **TLS** | Required for `*.supabase.co`; disabled for local Docker |
| **Free tier** | Projects pause after 7 days idle — document Pro tier ($25/mo) for always-on demos |
| **Extensions** | Enable `vector` in Supabase SQL editor before first deploy |

### Pooler troubleshooting runbook (Slice 37 deliverable)

| Symptom | Likely cause | Action |
|---|---|---|
| Prepared statement errors | Transaction pooler mode | Switch to Session mode URI in Supabase dashboard |
| Connection timeout on boot | Paused free-tier project | Resume project in Supabase UI or upgrade tier |
| HNSW query failures | Wrong pooler or missing extension | Verify Session mode + `CREATE EXTENSION vector` |

---

## Spec (GWT)

```
Scenario: Local stack one-command start
  Given Docker available
  When ./start-services.sh --local-postgres runs
  Then server + dashboard + pgvector are healthy with STORAGE_BACKEND=postgres

Scenario: Hosted Supabase URI with TLS
  Given a valid Supabase DATABASE_URL (pooler or direct)
  When the server boots
  Then pool connects and a smoke sweep completes

Scenario: Boot reconciliation on Postgres
  Given an experiment left in running state
  When the server restarts
  Then orphaned in-flight runs are marked interrupted/partial as today

Scenario: Supabase paused project surfaces clear error
  Given a paused free-tier Supabase project
  When the server attempts connection
  Then logs and health check report unreachable database with remediation hint (resume project or upgrade tier)
```

---

## Before-Checks [GATE]

- [ ] Slice 36 ✅ PASSED
- [ ] Supabase project credentials for cloud smoke (or documented skip)

---

## After-Checks [GATE]

- [ ] Local + cloud smoke documented in supabase-setup.md
- [ ] Boot reconciliation tests for Postgres path
- [ ] Mongo `--local` path still works unchanged
- [ ] Specification coverage: every GWT clause has at least one test (BDD/GWT-first); essential error and timeout paths covered
- [ ] Branch coverage: target 100% where practical; document any exclusions
- [ ] Mutation testing run if slice is feature-complete: mutation budget ≤10% survivors
- [ ] Coverage + quality gates
- [ ] Doc audit: PRD §Documentation matrix rows for slice **37** (all user + dev setup docs; `supabase-setup.md` created)
- [ ] `/sync-docs` run — README, docs/README, user-guide, development.md footprint verified
- [ ] `docs/plan/slices/PROGRESS.md` updated

## Gate Status

📋 PLANNED
