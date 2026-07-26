# SLICE 37 — Local + Hosted Parity + Low-Friction Switching

**MoSCoW:** MUST
**Target time:** ~3–4 h
**Status:** 📋 PLANNED
**Depends on:** 36
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../PRD-supabase-pgvector-migration.md)

> Atlas Local (25/25B) analogue for **operator DX**. Local pgvector compose already shipped in Slice 33 (`--postgres`). This slice owns the symmetric flag vocabulary, hosted Supabase start without Mongo URI, config↔server consistency, lifecycle subcommands, Path B docs, and **least-friction Mongo ↔ Postgres switching**.

---

## Slice Workflow Bundle

- Slice name: `slice-37-postgres-local-cloud-parity`
- Branch: `slice/37-postgres-local-cloud-parity`
- Files (expected):
  - `start-services.sh` / `scripts/lib/compose.sh` — four-flag parse + `ensure_env` + hints + `postgres` lifecycle
  - `docker-compose.yml` — profiles renamed/aliased to `mongodb-local` / `postgres-local`
  - `server/settings.py` / `store_factory.py` — `STORAGE_BACKEND` accepts `mongodb` (+ legacy `mongo`)
  - `server/models/config.py` — normalize `database_provider` (`supabase` → `postgres`)
  - `server/api/experiments.py` (or shared helper) — reject config/backend mismatch before persist
  - `cli/api_client.py` / `cli/main.py` — optional preflight against `/healthz` with same remediation text
  - `configs/supabase/example-local.yaml`, `configs/supabase/example-local.yaml` (+ mongodb cloud example if missing)
  - `server/core/startup_reconciliation.py` — verify Postgres path via StorageBackend + tests
  - `docs/user-guide/postgres-setup.md` — Path B + switching table; **no** separate `supabase-setup.md`
  - Doc sweep: `README.md`, `QUICKSTART.md`, `CLAUDE.md`, `AGENTS.md`, `mongodb-setup.md`, `configuration.md`, `local-environment.md`, `CHANGELOG.md`
- Exit criteria: Two-step switch works for all four modes; hosted smoke; lifecycle parity; mismatch 422 with remediation; Mongo path unchanged under `--mongodb-local` and legacy `--local`
- Commit pattern: `feat(slice-37): low-friction db-type local/cloud switching`
- **Doc exit:** `/sync-docs` — postgres-setup Path B, getting-started switching table, troubleshooting, docs/README, README, development.md

---

## Goal

Make Mongo ↔ Postgres (and local ↔ cloud) switching **smooth and obvious**:

1. One flag starts the stack in the desired mode.
2. One matching example config runs a smoke sweep.
3. A wrong config fails fast with the exact restart command — no silent cross-backend writes.

```text
--<db-type>-<location>
  db-type:  mongodb | postgres
  location: local | cloud
```

| Flag | Env equivalent | Behaviour |
|---|---|---|
| `--mongodb-local` | `RAG_MONGODB_LOCAL=1` | Atlas Local container; no TLS; no cloud `MONGODB_URI` needed |
| `--mongodb-cloud` | `RAG_MONGODB_CLOUD=1` | Atlas cloud; requires `MONGODB_URI` |
| `--postgres-local` | `RAG_POSTGRES_LOCAL=1` | pgvector container; `STORAGE_BACKEND=postgres` |
| `--postgres-cloud` | `RAG_POSTGRES_CLOUD=1` | Hosted Supabase; requires `DATABASE_URL`; **must not require `MONGODB_URI`** |

**Deprecated aliases** (print one-line notice; keep working until Slice 38+ removal):

| Alias | Maps to |
|---|---|
| `--local`, `-l`, `RAG_LOCAL_ATLAS=1` | `--mongodb-local` |
| `--postgres`, `-p`, `RAG_LOCAL_POSTGRES=1` | `--postgres-local` |

Bare `./start-services.sh` still works: resolve from `STORAGE_BACKEND` in `.env` (`postgres` → needs `DATABASE_URL`; `mongodb`/`mongo` → needs `MONGODB_URI`); default remains `mongodb-cloud`.

Subcommands reuse the same tokens: `start-services.sh mongodb …` and `start-services.sh postgres start|stop|reset|status`.

---

## Low-friction switching contract (Must)

Happy path is always **two commands**:

```bash
./start-services.sh --postgres-local
rag-params-finder run --config configs/supabase/example-local.yaml
```

| From → To | Operator steps |
|---|---|
| Mongo local → Postgres local | `--postgres-local` + `configs/supabase/example-local.yaml` |
| Mongo cloud → Postgres cloud (Supabase) | put `DATABASE_URL` in `.env`, `--postgres-cloud` + `configs/supabase/example-*.yaml` |
| Postgres → Mongo | `--mongodb-local` or `--mongodb-cloud` + matching `configs/mongodb/example-*.yaml` |
| Postgres local → Postgres cloud | `--postgres-cloud` (same `database_provider: postgres` YAML OK) |

**Must not require:** editing YAML to name `supabase`; hand-setting `STORAGE_BACKEND` when a flag is used; providing `MONGODB_URI` for Postgres modes; reading three different docs to guess the mode string.

Post-start stdout always prints:

- `storage_mode=<compound>`
- host CLI exports (`STORAGE_BACKEND`, URI)
- suggested `rag-params-finder run --config configs/example-<compound>.yaml` (or nearest example)

---

## Config ↔ server consistency (Must)

YAML does **not** flip the process backend (one process = one pool). It declares intent:

| Field | Role |
|---|---|
| `database_provider` | Engine only: `mongodb` \| `postgres` (`supabase` → normalize to `postgres` + deprecation warning) |
| Active `STORAGE_BACKEND` / flag | Selects adapter |
| URI | Selects `local` vs `cloud` → `storage_mode` |

On `POST /experiments` (and CLI before submit):

1. Normalize `STORAGE_BACKEND` (`mongo` → `mongodb`) and `database_provider` (`supabase` → `postgres`).
2. If engine ≠ backend → **HTTP 422** / CLI non-zero **before** insert or BackgroundTasks.
3. Remediation text names both the restart flag and a matching example config.
4. Persist normalized `database_provider` + resolved `storage_mode` on the experiment/run.

---

## Why flags land here first

Today `parse_args()` tracks two independent booleans (`LOCAL_ATLAS`, `LOCAL_POSTGRES`) with “cloud” as an invisible fall-through. That shape cannot express “Postgres, hosted”, which is why `ensure_env` still demands `MONGODB_URI` whenever `--postgres` is absent. Resolve a `(db_type, location)` pair **before** branching `ensure_env`, then hosted Supabase becomes a first-class path instead of a special case.

---

## Supabase connection requirements (document in postgres-setup.md Path B)

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
| Prepared statement errors | Transaction pooler mode | Switch to Session mode URI; set `prepare_threshold` / confirm `hnsw.iterative_scan` under pooler |
| Connection timeout on boot | Paused free-tier project | Resume project in Supabase UI or upgrade tier; health/remediation hint |
| HNSW query failures | Wrong pooler or missing extension | Verify Session mode + `CREATE EXTENSION vector` |

---

## Spec (GWT)

```
Scenario: Two-step switch Mongo → Postgres local
  Given Docker available and a Mongo stack may already be running
  When ./start-services.sh --postgres-local runs
  And rag-params-finder run --config configs/supabase/example-local.yaml runs
  Then healthz storage_mode is postgres-local
  And the sweep is accepted and stores into Postgres

Scenario: Two-step switch to Postgres cloud (Supabase)
  Given DATABASE_URL points at a Supabase project
  When ./start-services.sh --postgres-cloud runs
  Then ensure_env does not require MONGODB_URI
  And storage_mode is postgres-cloud
  And configs/supabase/example-*.yaml (or any database_provider: postgres/supabase config) is accepted

Scenario: Same postgres YAML works local and cloud
  Given a config with database_provider: postgres
  When submitted to a postgres-local server
  Then it is accepted
  When the same config is submitted to a postgres-cloud server
  Then it is accepted

Scenario: Config/backend mismatch fails fast with remediation
  Given server storage_mode=postgres-cloud
  And config database_provider=mongodb
  When POST /experiments (or CLI run) executes
  Then HTTP 422 / non-zero exit before any experiment row is written
  And the message names ./start-services.sh --mongodb-local (or --mongodb-cloud)
  And suggests configs/supabase/example-*.yaml as the alternate fix

Scenario: Legacy aliases still work
  When ./start-services.sh --postgres runs
  Then behaviour matches --postgres-local plus a deprecation notice
  When ./start-services.sh --local runs
  Then behaviour matches --mongodb-local plus a deprecation notice

Scenario: Post-start hint names matching example config
  When any canonical flag starts the stack successfully
  Then stdout includes storage_mode and a suggested example-*.yaml path

Scenario: postgres lifecycle subcommands
  Given the postgres-local profile
  When ./start-services.sh postgres start|stop|reset|status runs
  Then container lifecycle mirrors the mongodb subcommand contract

Scenario: Boot reconciliation on Postgres
  Given an experiment left in running state
  When the server restarts with STORAGE_BACKEND=postgres
  Then orphaned in-flight runs are marked interrupted/partial as today

Scenario: Supabase paused project surfaces clear error
  Given a paused free-tier Supabase project
  When the server attempts connection
  Then logs and health check report unreachable database with remediation hint
```

---

## Drop / retarget (from earlier draft)

| Drop / retarget | New ownership |
|---|---|
| GWT “`--local-postgres` starts stack” | Already shipped as `--postgres`; rename to `--postgres-local` here |
| Create `supabase-setup.md` + `example-supabase-local.yaml` | Expand Path B in `postgres-setup.md`; hosted uses `configs/supabase/example-*.yaml` + `DATABASE_URL` (no separate cloud YAML — 2026-07-26 configs split) |
| Vague “full start-services” | `ensure_env` on resolved `(db_type, location)`; hints; lifecycle; mismatch gate |
| Doc-only pooler rows | Code + runbook: Session mode, `prepare_threshold`, paused-project remediation |

---

## Before-Checks [GATE]

- [ ] Slice 36 ✅ PASSED (or mode half already pulled forward — note in Progress)
- [ ] Supabase project credentials for cloud smoke (or documented skip)
- [ ] Confirm Slice 33 local profile still healthy under current `--postgres` before rename

---

## After-Checks [GATE]

- [ ] All four canonical flags documented in `./start-services.sh --help`
- [ ] Switching table in `postgres-setup.md` + `mongodb-setup.md` (two-command recipes)
- [ ] Hosted smoke documented in `postgres-setup.md` Path B (not a separate `supabase-setup.md`)
- [ ] Config mismatch 422 + CLI remediation tested
- [ ] `supabase` / `mongo` aliases normalize; no silent cross-backend writes
- [ ] Boot reconciliation tests for Postgres path
- [ ] Mongo `--mongodb-local` and legacy `--local` both work
- [ ] `ensure_env` never requires `MONGODB_URI` when effective backend is postgres
- [ ] Post-start hint includes matching example config path
- [ ] Specification coverage: every GWT clause has at least one test or documented manual smoke
- [ ] Branch coverage: target 100% where practical; document any exclusions
- [ ] Mutation testing run if slice is feature-complete: mutation budget ≤10% survivors
- [ ] Coverage + quality gates
- [ ] Doc audit: PRD §Documentation matrix rows for slice **37** (setup docs; flag + switching table)
- [ ] `/sync-docs` run — README, docs/README, user-guide, development.md footprint verified
- [ ] `docs/plan/slices/PROGRESS.md` updated

## Gate Status

📋 PLANNED
