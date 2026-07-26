# SLICE 37 — Local + Hosted Parity + Low-Friction Switching

**MoSCoW:** MUST
**Target time:** ~3–4 h
**Status:** 🔨 IN PROGRESS
**Depends on:** 36
**Branch:** `slice/37-postgres-local-cloud-parity`
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../PRD-supabase-pgvector-migration.md)

> Atlas Local (25/25B) analogue for **operator DX**. Local pgvector compose already shipped in Slice 33 (`--postgres`). This slice owns the symmetric flag vocabulary, hosted Supabase start without Mongo URI, config↔server consistency, lifecycle subcommands, Path B docs, and **least-friction Mongo ↔ Postgres switching**.
>
> **Also absorbs leftovers from Slice 36 close (2026-07-26):** vocabulary surfaces that still mix Atlas/Supabase product names with the engine × location axes — see [Absorbed from Slice 36](#absorbed-from-slice-36-close--2026-07-26).

---

## Already landed (do not re-scope)

| Foundation | Owner | Live evidence |
|---|---|---|
| Four-value `storage_mode` + `/healthz` | Slice **36** | `resolve_storage_mode()`, `tests/test_storage_mode.py`, `gate-evidence/slice-36.json` |
| Postgres catalog preflight **422** (indexes/extension) | Slice **36** | `search_index_guard.validate_postgres_experiment_indexes` — **distinct** from Slice 37 config↔server 422 |
| Canonical `STORAGE_BACKEND=mongodb` (+ `mongo` alias) | Slice **43** | `normalize_storage_backend()` |
| Path A `--postgres` + compose **service** `postgres-local` | Slice **33** | `start-services.sh --postgres`; service name already matches mode token |
| Path B stub + Session-mode URI guidance + TLS auto | Slices **33/43** | `postgres-setup.md` Path B; `postgres_connect_kwargs` `sslmode=require` — deepen runbook here |
| `configs/supabase/*` twins + local smoke | Slices **34/43** | `test_config_examples.py`; `gate-evidence/slice-43.json` |

---

## Absorbed from Slice 36 close — 2026-07-26

Slice 36 shipped four-value `storage_mode` (`mongodb|postgres` × `local|cloud`) and Postgres catalog preflight. These items were **explicitly out of scope for 36** (or left unfinished) and are **Must/Should/Could/Won't for 37**:

| Item | MoSCoW | Why it is not 36 | 37 action |
|---|---|---|---|
| Four-flag `./start-services.sh --{mongodb\|postgres}-{local\|cloud}` + `ensure_env` | Must | Flags print mode tokens; tokens landed first in 36 | Implement parse + hosted path without requiring `MONGODB_URI` |
| Bare start resolves from `.env` `STORAGE_BACKEND` | Must | Today bare start **always** assumes mongodb-cloud and demands `MONGODB_URI` | Resolve `(db_type, location)` from flags **or** `.env` before `ensure_env` |
| Config ↔ server mismatch **HTTP 422** | Must | Needs flag vocabulary + remediation text | Reject `database_provider` engine ≠ `STORAGE_BACKEND` **before** index/SIE preflight and before persist |
| Compose **profile** `local-postgres` / `local-atlas` vs mode tokens | Must | Profile spelling drift; **service** names already `postgres-local` / `mongodb-local` | Add canonical profiles matching mode tokens; keep old profile names as deprecated aliases |
| `database_provider: supabase` YAML + `settings.default_database_provider()` → `"supabase"` | Must | Label leaks a third “backend”; mode already uses `postgres-cloud` | Accept deprecated `supabase` input, normalize to `postgres` before validation/persistence, and emit a warning |
| `vector_db_id` like `supabase:<host>` | Must | Mixes provider label into stats group key | Use canonical `storage_mode:<host>` identity while retaining host separation between clusters |
| Persist resolved `storage_mode` on create | Must | Health/stats expose mode; experiment docs do not | Write `storage_mode` on experiment doc (top-level and/or `sweep_summary`); no DDL — doc/JSONB field |
| Product-wording map across operator docs | Must | Runtime modes exist; prose still mixes axes | Apply [Product wording](#product-wording-operator-facing) everywhere Slice 37 touches |
| Canonical Engine × Location note in `configuration.md` | Must | Partial env comment only; no dedicated subsection | Add explicit two-axis + shorthand section (see below). **Supersedes** PRD doc-matrix rows that only listed configuration under 33/35/36 for this subsection |
| `postgres` lifecycle `start\|stop\|reset\|status` | Must | Only `mongodb` subcommands exist | Mirror mongodb lifecycle contract |
| Post-start `storage_mode=` + example path | Must | Hints exist; compound + matching example path do not | Print mode + one existing example YAML |
| Boot reconciliation tests (Postgres path) | Should | Runtime path already uses `StorageBackend`; dedicated tests missing | Add unit/integration coverage of orphan interrupt on Postgres |
| Paused-project / pooler remediation | Should | Generic health `"error"` only; Path B incomplete | Doc runbook + health/log remediation substring; **unit inject** acceptable — live paused project not required for gate |
| `prepare_threshold` pool code | Should | HNSW `iterative_scan` already set; Transaction-mode breakage not reproduced | Doc Session-mode runbook first; code change only if breakage is measured |
| CLI surfaces server 422 (no second validator) | Should | Server owns invariant | Render API 422 detail; do not reimplement against `/healthz` |
| URI aliases (`SUPABASE_URI` / `POSTGRES_URI`) | Won't | Slice 43 already documents asymmetry | Keep documenting `DATABASE_URL` + `STORAGE_BACKEND=postgres`; no new env aliases this slice |
| New `configs/mongodb/example-cloud.yaml` | Won't | Voyage / unified twins already cover cloud Mongo | Point switching table at existing `configs/mongodb/example-*.yaml` |
| `configs/supabase/` peer of `configs/mongodb/` | Could | Product folder vs engine folder | **Keep** folder for Path B this slice; document path ≠ `STORAGE_BACKEND`. Full rename → optional follow-up, not a 37 blocker |

---

## Vocabulary contract (operator-facing)

### Canonical axes (do not regress)

1. **Engine** — `STORAGE_BACKEND`: `mongodb` \| `postgres` (what the server speaks)
2. **Location** — `storage_mode`: `{engine}-local` \| `{engine}-cloud` (where that engine lives)
3. **Product shorthand** — Atlas / Supabase name the *usual cloud host* for each engine; they are **not** a peer second axis

YAML `database_provider: supabase` is a deprecated compatibility input. Slice 37 normalizes it to canonical `postgres` before comparing it with the active backend or persisting it. Runtime truth remains `STORAGE_BACKEND=postgres` + a Supabase-shaped `DATABASE_URL` → `storage_mode=postgres-cloud`.

### Product wording (operator-facing)

Use this map in flags help, switching tables, README, getting-started, postgres-setup, mongodb-setup, and troubleshooting:

| `storage_mode` | Product wording |
|---|---|
| `mongodb-cloud` | **Atlas cloud** |
| `mongodb-local` | **Atlas Local** |
| `postgres-cloud` | **Supabase-hosted Postgres** |
| `postgres-local` | **local pgvector / Postgres** |

**Nuance:** “Atlas” alone is ambiguous — always ask **cloud or Local?** “Supabase” implies Postgres cloud; local Postgres is a different mode entirely.

### One-line operator checks (for docs / CLI hints)

- Someone says “I’m on Atlas” → ask: **cloud or Local?**
- Someone says “I’m on Supabase” → engine is Postgres cloud; local Postgres is `postgres-local`, not Supabase

### `configuration.md` subsection (Must — write in this slice)

Add a short canonical block near `STORAGE_BACKEND` / `storage_mode`:

- Axis 1 / Axis 2 / shorthand as above
- Explicit: `database_provider` declares engine intent; `configs/supabase/` is a compatibility path, not an adapter
- Explicit: canonical compose profiles match mode tokens; legacy profile names are aliases only
- Explicit: config↔server engine mismatch 422 ≠ catalog/index preflight 422
- Link the product-wording table

---

## Slice Workflow Bundle

- Slice name: `slice-37-postgres-local-cloud-parity`
- Branch: `slice/37-postgres-local-cloud-parity`
- Files (expected):
  - `start-services.sh` / `scripts/lib/compose.sh` — `(db_type, location)` mode resolver; four-flag parse; conflicting-selector fail; `ensure_env` by mode; hints; `postgres` lifecycle
  - `docker-compose.yml` — canonical profiles `mongodb-local` / `postgres-local` (+ deprecated `local-atlas` / `local-postgres` aliases)
  - `server/settings.py` — `default_database_provider()` returns `postgres` (never bare `supabase`); `normalize_storage_backend` already landed
  - `server/models/config.py` — normalize `database_provider` (`supabase` → `postgres` + warning)
  - `server/db/postgres_stats.py` / `stats_common.py` — canonical `database_provider`; `vector_db_id` uses `storage_mode:<host>`
  - `server/api/experiments.py` (or shared helper) — reject config/backend mismatch **before** search-index/SIE preflight and persist; write `storage_mode` on experiment doc
  - `cli/api_client.py` / `cli/main.py` — **Should:** surface the server's 422 remediation without duplicating backend validation
  - `configs/supabase/example-*.yaml` — keep path; examples work under `--postgres-local` and `--postgres-cloud` after normalize
  - `server/core/startup_reconciliation.py` + tests — dedicated Postgres-path coverage (**Should**)
  - `server/core/health_check.py` — paused/unreachable remediation substring (**Should**)
  - Tests — mode selector conflicts, aliases, hosted env requirements, pre-I/O mismatch rejection, provider normalization, stats grouping, Postgres reconciliation
  - `docs/user-guide/postgres-setup.md` — Path B + switching table with product-wording map; **no** separate `supabase-setup.md`
  - `docs/user-guide/configuration.md` — dedicated Engine × Location subsection (Must)
  - Doc sweep: `README.md`, `QUICKSTART.md`, `CLAUDE.md`, `AGENTS.md`, `mongodb-setup.md`, `getting-started.md`, `local-environment.md`, `CHANGELOG.md` — apply product-wording map
- Exit criteria: Two-step switch works for all four modes; conflicting selectors fail before Docker; bare `.env` `STORAGE_BACKEND=postgres` starts without `MONGODB_URI`; lifecycle parity; mismatch 422 before database I/O with remediation distinct from catalog 422; canonical compose profiles match `storage_mode` compounds while aliases remain compatible; operator docs use the product-wording map; Mongo path unchanged under `--mongodb-local` and legacy `--local`
- Commit pattern: `feat(slice-37): low-friction db-type local/cloud switching`
- **Doc exit:** `/sync-docs` — postgres-setup Path B, getting-started switching table, troubleshooting, docs/README, README, development.md

### Minimal vertical-slice execution order

1. Mode resolution primitive — `(db_type, location)` in `start-services.sh` / `compose.sh`; four flags + env; legacy aliases + notice; `ensure_env` by mode (hosted/local postgres skip `MONGODB_URI`; bare `.env` `STORAGE_BACKEND=postgres` works)
2. Compose profile alias/rename + postgres lifecycle + post-start `storage_mode=` + existing example path
3. Provider normalize (`supabase`→`postgres`) + `default_database_provider` + `vector_db_group_key` / `vector_db_id`
4. Config↔server 422 shared remediation helper; wire API **before** index/SIE preflight; persist `storage_mode`; CLI Should
5. Docs — product-wording map, switching tables, Path B pooler/pause runbook, `configuration.md` subsection, troubleshooting
6. Should polish — paused-project health hint; boot-reconcile tests; optional hosted smoke or documented skip

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

**Bare start today (pre-37):** always assumes mongodb-cloud and demands `MONGODB_URI`.
**Bare start after 37:** resolve `(db_type, location)` from flags **or** `.env` `STORAGE_BACKEND` + URI before `ensure_env` (`postgres` → needs `DATABASE_URL`; `mongodb`/`mongo` → needs `MONGODB_URI`); default remains `mongodb-cloud` when unset.

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
| Postgres → Mongo | `--mongodb-local` or `--mongodb-cloud` + matching existing `configs/mongodb/example-*.yaml` |
| Postgres local → Postgres cloud | `--postgres-cloud` (same `database_provider: postgres` YAML OK) |

**Must not require:** editing YAML to name `supabase`; hand-setting `STORAGE_BACKEND` when a flag is used; providing `MONGODB_URI` for Postgres modes; reading three different docs to guess the mode string; inventing a new `example-cloud.yaml` stem.

Post-start stdout uses this exact shape (values filled from the resolved mode):

```text
storage_mode=postgres-local
STORAGE_BACKEND=postgres
DATABASE_URL=postgresql://rag:rag@localhost:5433/rag_params_finder
Suggested: rag-params-finder run --config configs/supabase/example-local.yaml
```

Mongo modes print `MONGODB_URI=…` and a `configs/mongodb/example-*.yaml` path instead. Cloud Postgres prints the operator's `DATABASE_URL` host (never the password) and a `configs/supabase/example-*.yaml` path.

Conflict failure (before Docker) uses this shape:

```text
ERROR: conflicting mode selectors: --postgres-local and --mongodb-cloud
Pick one of: --mongodb-local | --mongodb-cloud | --postgres-local | --postgres-cloud
```

---

## Config ↔ server consistency (Must)

YAML does **not** flip the process backend (one process = one pool). It declares intent:

| Field | Role |
|---|---|
| `database_provider` | Engine only: `mongodb` \| `postgres` (`supabase` → normalize to `postgres` + deprecation warning) |
| Active `STORAGE_BACKEND` / flag | Selects adapter |
| URI | Selects `local` vs `cloud` → `storage_mode` |

On `POST /experiments`:

1. Normalize `STORAGE_BACKEND` (`mongo` → `mongodb`) and `database_provider` (`supabase` → `postgres`).
2. If engine ≠ backend → **HTTP 422** **before** search-index/SIE preflight, insert, or BackgroundTasks.
3. Remediation text names both the restart flag and a matching example config; message must be **distinct** from catalog/index preflight 422.
4. Persist normalized `database_provider` **and** resolved `storage_mode` on the experiment doc (`sweep_summary.storage_mode` and/or top-level); health/stats remain the live runtime identity.
5. CLI (**Should**) surfaces the API's 422 detail and exits non-zero; it does not reimplement the server invariant.

**Canonical 422 detail template** (fill engine/mode/paths; never reuse catalog-index wording):

```text
Config engine mismatch: database_provider=mongodb but server storage_backend=postgres (storage_mode=postgres-cloud).
Restart with matching backend: ./start-services.sh --mongodb-cloud
Or submit a postgres config, e.g. configs/supabase/example-local.yaml
```

When the server is Mongo and the config is Postgres, swap the sides and suggest `--postgres-local` / `--postgres-cloud` plus a `configs/supabase/example-*.yaml` path.

---

## Why flags land here first

Today `parse_args()` tracks two independent booleans (`LOCAL_ATLAS`, `LOCAL_POSTGRES`) with “cloud” as an invisible fall-through. That shape cannot express “Postgres, hosted”, which is why `ensure_env` still demands `MONGODB_URI` whenever `--postgres` is absent. Resolve a `(db_type, location)` pair **before** branching `ensure_env`, then hosted Supabase becomes a first-class path instead of a special case.

---

## Supabase connection requirements (document in postgres-setup.md Path B)

| Topic | Requirement |
|---|---|
| **URI** | `DATABASE_URL` from Supabase dashboard (Settings → Database) |
| **Pooler** | Prefer **Session mode** pooler for pgvector + prepared statements; document if Transaction mode breaks HNSW queries |
| **TLS** | Required for `*.supabase.co`; disabled for local Docker (**already implemented**) |
| **Free tier** | Projects pause after 7 days idle — document Pro tier ($25/mo) for always-on demos |
| **Extensions** | Enable `vector` in Supabase SQL editor before first deploy |

### Pooler troubleshooting runbook (Slice 37 deliverable)

| Symptom | Likely cause | Action |
|---|---|---|
| Prepared statement errors | Transaction pooler mode | Switch to Session mode URI; document `prepare_threshold` guidance; confirm `hnsw.iterative_scan` (already set in pool) |
| Connection timeout on boot | Paused free-tier project | Resume project in Supabase UI or upgrade tier; health/remediation hint |
| HNSW query failures | Wrong pooler or missing extension | Verify Session mode + `CREATE EXTENSION vector` |

Hosted Path B smoke: **credentials required or documented skip** in Before-Checks. A documented skip does **not** block Must COMPLETE when unit/manual gates for `--postgres-cloud` `ensure_env` (no `MONGODB_URI`) and Session-mode docs are green.

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
  And configs/supabase/example-*.yaml (or any database_provider: postgres/supabase config) is accepted after normalize

Scenario: Bare start respects STORAGE_BACKEND=postgres
  Given .env has STORAGE_BACKEND=postgres and a real DATABASE_URL
  And no mode flag is passed
  When ./start-services.sh runs
  Then ensure_env does not require MONGODB_URI
  And the stack starts in postgres-cloud (or postgres-local when URI is local)

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
  Then HTTP 422 / non-zero exit before index preflight or any experiment row is written
  And the message names ./start-services.sh --mongodb-local (or --mongodb-cloud)
  And suggests configs/supabase/example-*.yaml as the alternate fix
  And the message is distinct from catalog/index preflight 422 text

Scenario: Conflicting mode selectors fail before Docker
  Given more than one canonical flag or RAG_* mode selector is active
  When ./start-services.sh resolves the requested mode
  Then it exits non-zero before invoking Docker
  And the message names the conflicting selectors

Scenario: Legacy aliases still work
  When ./start-services.sh --postgres runs
  Then behaviour matches --postgres-local plus a deprecation notice
  When ./start-services.sh --local runs
  Then behaviour matches --mongodb-local plus a deprecation notice

Scenario: Post-start hint names matching example config
  When any canonical flag starts the stack successfully
  Then stdout includes storage_mode and a suggested existing example-*.yaml path

Scenario: postgres lifecycle subcommands
  Given the postgres-local profile
  When ./start-services.sh postgres start|stop|reset|status runs
  Then container lifecycle mirrors the mongodb subcommand contract

Scenario: Boot reconciliation on Postgres
  Given an experiment left in running state
  When the server restarts with STORAGE_BACKEND=postgres
  Then orphaned in-flight runs are marked interrupted/partial as today

Scenario: Supabase paused / unreachable surfaces clear error
  Given a connection failure that represents a paused or unreachable hosted project
  When the server attempts connection (live or injected unit failure)
  Then logs and health check report unreachable database with remediation hint
```

---

## Drop / retarget (from earlier draft)

| Drop / retarget | New ownership |
|---|---|
| GWT “`--local-postgres` starts stack” | Already shipped as `--postgres`; rename to `--postgres-local` here |
| Create `supabase-setup.md` + `example-supabase-local.yaml` | Expand Path B in `postgres-setup.md`; hosted uses `configs/supabase/example-*.yaml` + `DATABASE_URL` (no separate cloud YAML — 2026-07-26 configs split) |
| Vague “full start-services” | `ensure_env` on resolved `(db_type, location)`; hints; lifecycle; mismatch gate |
| Doc-only pooler rows | Session-mode runbook first; `prepare_threshold` code only if breakage measured |
| CLI duplicates backend validation via a second health call | Server owns the invariant; CLI renders the server's 422 detail (**Should**) |
| Rename Atlas snapshot helper while touching preflight | Out of scope: correct behavior and docstring already exist; no Slice 37 user outcome |
| New `SUPABASE_URI` / `POSTGRES_URI` aliases | **Won't** this slice — keep Slice 43 asymmetry docs |
| New `configs/mongodb/example-cloud.yaml` | **Won't** — use existing mongodb example stems |

---

## Before-Checks [GATE]

- [x] Slice 36 ✅ PASSED — `gate-evidence/slice-36.json` (2026-07-26); four-value `storage_mode` + Postgres preflight landed
- [ ] Supabase project credentials for cloud smoke **or** documented skip (skip does not block Must COMPLETE when `ensure_env` + docs gates pass)
- [ ] Confirm Slice 33 local profile still healthy under current `--postgres` before profile rename

---

## After-Checks [GATE]

- [ ] All four canonical flags documented in `./start-services.sh --help`
- [ ] Switching table in `postgres-setup.md` + `mongodb-setup.md` (two-command recipes; existing example paths only)
- [ ] Hosted Path B docs complete (pooler/pause runbook); live hosted smoke **or** documented skip recorded
- [ ] Config↔server mismatch 422 tested **before** index/SIE preflight; message distinct from catalog 422
- [ ] CLI remediation (**Should**) surfaces server 422 detail
- [ ] `supabase` / `mongo` aliases normalize; no silent cross-backend writes
- [ ] Canonical compose **profiles** align with `storage_mode` compounds; deprecated profile aliases still work; **service** names already OK (regression only)
- [ ] Conflicting flag/env selectors fail before Docker with actionable output
- [ ] Bare `.env` `STORAGE_BACKEND=postgres` does not require `MONGODB_URI`
- [ ] `default_database_provider()` / persisted configs no longer emit `supabase`; stats `vector_db_id` uses `storage_mode:<host>`
- [ ] Experiment create persists resolved `storage_mode`
- [ ] Docs state engine × location axes; product wording matches the four-row map (Atlas cloud / Atlas Local / Supabase-hosted Postgres / local pgvector)
- [ ] `configuration.md` has a dedicated Engine × Location subsection (not only an env comment)
- [ ] Switching tables + `--help` use product wording; “Atlas” alone never means both cloud and Local without qualifier
- [ ] Boot reconciliation tests for Postgres path (**Should**)
- [ ] Mongo `--mongodb-local` and legacy `--local` both work (regression)
- [ ] `ensure_env` never requires `MONGODB_URI` when effective backend is postgres
- [ ] Post-start hint includes matching example config path + printed `storage_mode`
- [ ] Specification coverage: every GWT clause has at least one test or documented manual smoke
- [ ] Branch coverage: target 100% where practical; document any exclusions (shell-heavy paths OK to exclude with note)
- [ ] Mutation testing: same as Slice 36 — waiver via DECISIONS if no local runner / shell-heavy
- [ ] Coverage + quality gates
- [ ] Doc audit: PRD §Documentation matrix rows for slice **37** (setup docs; flag + switching table; configuration Engine × Location supersession noted)
- [ ] `/sync-docs` run — README, docs/README, user-guide, development.md footprint verified
- [ ] `docs/plan/slices/PROGRESS.md` updated

## Review notes (2026-07-26)

`nw-platform-architect-reviewer` returned `NEEDS REVISION` by scoring **missing main-branch implementation** as plan blockers. Reclassification for planning:

| Reviewer label | Planning disposition |
|---|---|
| Four flags / conflict detection / hosted `ensure_env` / compose profiles / provider normalize / mismatch 422 | Already **Must** execution exit criteria — keep; do not treat as plan defects |
| Remediation text / post-start hint format unspecified | **Applied** — concrete stdout + 422 templates above |
| Engine × Location docs / configuration.md | Already **Must**; remains in After-Checks |
| Hosted smoke required for COMPLETE | Rejected — Before-Checks allow documented skip |

Planning verdict after edits: **CONDITIONALLY APPROVED** for execution. Implementation remains incomplete until After-Checks pass.

## Gate Status

🔨 IN PROGRESS — Must+Should code **IMPLEMENTED** (unit-verified); docs synced (`/sync-docs`); live four-mode smoke + `gate-evidence/slice-37.json` still required before ✅ COMPLETE
