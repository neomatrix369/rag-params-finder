# SLICE 36 — Postgres Index Preflight + DB Stats + Storage Mode

**MoSCoW:** MUST
**Target time:** ~3–4 h
**Status:** ✅ COMPLETE
**Depends on:** 35
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../../PRD-supabase-pgvector-migration.md)

> Absorbs deferred Slice 27 (Mongo cloud vs local indicator) into a **four-value** `storage_mode` that mirrors the operator flag vocabulary from Slice 37.

---

## Baseline as of 2026-07-26 (post 35 / 43 — sync pass)

Landed on `main` (do **not** re-implement):

| Area | Evidence | Still owned by 36? |
|---|---|---|
| Slice 35 sparse/hybrid + Supabase-mode copy hygiene | PR #112, `gate-evidence/slice-35.json` | No — consume as baseline |
| Slice 43 supabase config live smoke + operator docs | PR #115, `gate-evidence/slice-43.json` | No — FAQ/`STORAGE_BACKEND` vs `database_provider` already documented |
| `postgres_stats.py` + `stats_common.py` size assembly | Slice 33; `pg_database_size` / `pg_indexes_size`; `_chunks_index_names()` | **Extend** — emit four-value `storage_mode`; keep shapes dashboard-compatible |
| Atlas preflight short-circuit on Postgres | `preflight_not_applicable()` in `search_index_guard.py` (DECISIONS # / Slice 34) | **Replace** short-circuit with Postgres catalog introspection → 422 |
| `/healthz` | Returns `storage_backend` + ping status only (`health_check.storage_health`) | **Add** `storage_mode` compound |
| Mode tokens in code | `postgres_uri`: `local-postgres` \| `supabase` only; no Mongo pair helper | **Rename** + add Mongo pair |
| Canonical runtime token | `STORAGE_BACKEND=mongodb` (legacy `mongo` alias) — Slice 43 / settings | Keep; mode compounds use `mongodb-*` not bare `mongo` |

**Ownership boundaries (do not steal):**

| Concern | Owner |
|---|---|
| Four-value `storage_mode` on `/healthz`, db-stats, badge; Postgres index preflight 422; indexes CLI on Postgres | **36** ✅ |
| Four-flag parse, `ensure_env`, config↔server 422, compose profile spelling, `database_provider` / `vector_db_id` normalize, Path B docs | **37** (absorbs 36 close leftovers — see SLICE-37 §Absorbed from Slice 36) |
| Side-by-side quality matrix + ADR-004 | **38** |
| Operator FAQ + supabase example smoke evidence | **43** ✅ |

**Not owned by 36 (moved to 37 at close):** start-services four-flag grid; compose `local-postgres` rename; YAML/`default_database_provider`/`vector_db_id` `supabase` label cleanup; configs folder rename (deferred as non-blocker).

---

## Slice Workflow Bundle

- Slice name: `slice-36-postgres-preflight-stats`
- Branch: `slice/36-postgres-preflight-stats`
- Files (expected):
  - `server/core/search_index_plan.py` — add Postgres required-index set (catalog names from schema.sql)
  - `server/core/search_index_guard.py` — **extend** (not new module): Postgres catalog verify path replaces `preflight_not_applicable()` short-circuit
  - `server/db/postgres_stats.py` — **extend** four-value mode tokens in stats payloads
  - `server/db/postgres_uri.py` — rename mode return values to `postgres-local` / `postgres-cloud`
  - `server/db/mongodb_uri.py` — **create** `mongodb_storage_mode()` (or equivalent) using existing `is_atlas_uri`
  - `cli/indexes_cmd.py` — list/reset path for Postgres catalog indexes
  - `server/core/health_check.py` — add `storage_mode` to `/healthz` body
  - Dashboard: update `cluster_tier_type` values in place (`VectorDbStatsPanel` already string-renders it); optional explicit `storage_mode` field
  - `tests/test_postgres_index_guard.py`, `tests/test_storage_mode.py`
- Exit criteria: Missing/wrong indexes → HTTP 422; db-stats panels work; indexes CLI useful; four-value storage mode visible and named after flags
- Commit pattern: `feat(slice-36): postgres index preflight db stats and storage mode`

---

## Goal

Postgres equivalents of search-index preflight and vector DB stats, plus a **storage-mode indicator** — absorbing deferred Slice 27 — using the same vocabulary as the **planned** Slice 37 `start-services.sh` flags (flags themselves land in 37; tokens land here first so 37 can print them):

| `storage_mode` | Meaning |
|---|---|
| `mongodb-local` | Atlas Local Docker / no TLS |
| `mongodb-cloud` | Atlas cloud / TLS |
| `postgres-local` | Docker pgvector / no TLS |
| `postgres-cloud` | Hosted Supabase / TLS |

An operator who sees `postgres-cloud` on the badge knows the exact flag that will produce it once 37 lands. Mode helpers emit the four compounds (`postgres-local` / `postgres-cloud` / `mongodb-local` / `mongodb-cloud`); legacy `supabase` / `local-postgres` must not appear in API responses.

**Cross-cutting invariant:** `storage_mode` values === CLI flag compounds === compose profile local names (`mongodb-local`, `postgres-local`). No third spelling (`supabase`, `local-postgres`, bare `mongo` / bare `mongodb` as a mode).

**Note:** YAML `database_provider: supabase` remains labeling metadata (Slice 43); it must not appear as `storage_mode`.

---

## Preflight behaviour (Postgres-native, not Atlas Admin API)

Indexes come from [`schema.sql`](../../../../server/db/postgres/schema.sql) at pool bootstrap. Preflight **introspects** required HNSW/GIN and returns 422 only when DDL/extension is missing or wrong — not an Atlas quota/create/reconcile dance.

**Module decision (DECISIONS #83 option A):** extend `search_index_guard.py` + `search_index_plan.py` for a Postgres branch — do **not** create `postgres_index_guard.py` or an IndexBackend Protocol in this slice.

### Required catalog objects (always required on Postgres)

| Name | Kind | Source |
|---|---|---|
| `vector` | extension | `CREATE EXTENSION IF NOT EXISTS vector` |
| `chunks_embedding_384_hnsw` | HNSW index on `chunks.embedding_384` | schema.sql |
| `chunks_embedding_1024_hnsw` | HNSW index on `chunks.embedding_1024` | schema.sql |
| `chunks_text_search_gin` | GIN index on `chunks.text_search` | schema.sql (sparse/hybrid) |

Config-conditional rule: if the submitted experiment's retrievers include `sparse` or `hybrid`, GIN is required; dense-only may still verify HNSW + extension. Prefer verifying **all four** always — schema.sql always creates them; missing any means bootstrap failed.

### Catalog queries (contract — implement against these, not invent others)

```sql
-- extension present?
SELECT 1 FROM pg_extension WHERE extname = 'vector';

-- required indexes present on public.chunks?
SELECT indexname
  FROM pg_indexes
 WHERE schemaname = current_schema()
   AND tablename = 'chunks'
   AND indexname = ANY(%s);  -- required name list above
```

Optional amcheck (nice-to-have, not a gate): confirm `pg_am.amname` is `hnsw` / `gin` for those index oids.

### HTTP 422 shape (parity with Mongo)

Reuse `SearchIndexMismatchError` → API maps to HTTP 422. Message via `format_mismatch_message` (or Postgres sibling) must include:

- required index/extension names
- present vs missing sets
- remediation: re-run schema bootstrap / `indexes reset` equivalent — **no** Atlas Admin API wording; **no** Mongo quota/slots lines when backend is postgres

When `STORAGE_BACKEND=postgres`, the guard must never open a Mongo client or call Atlas Admin APIs.

---

## Storage mode contract (observable)

| Observable | Contract |
|---|---|
| `GET /healthz` body | Includes `storage_mode` ∈ {`mongodb-local`,`mongodb-cloud`,`postgres-local`,`postgres-cloud`} |
| db-stats / vector-db-stats group totals | Same four tokens exposed (field may be `storage_mode` and/or renamed `cluster_tier_type` — both must use the four tokens; dashboard already renders `cluster_tier_type` as a string in `VectorDbStatsPanel`) |
| Mongo classification | `STORAGE_BACKEND=mongodb` + Atlas cloud URI (`.mongodb.net`) → `mongodb-cloud`; otherwise local/non-Atlas → `mongodb-local` (helper **created** in `mongodb_uri.py`; today only `is_atlas_uri` exists) |
| Postgres classification | Hosted Supabase URI suffixes → `postgres-cloud`; else → `postgres-local` (rename today's `supabase` / `local-postgres`) |

Legacy tokens `supabase` and `local-postgres` must not appear in API responses after this slice.

---

## Spec (GWT)

```
Scenario: Preflight rejects missing HNSW/GIN indexes
  Given STORAGE_BACKEND=postgres and at least one required catalog object is absent
    (vector extension, chunks_embedding_384_hnsw, chunks_embedding_1024_hnsw, or chunks_text_search_gin)
  When an experiment is submitted
  Then the response is HTTP 422
  And the detail lists required vs missing names with Postgres remediation (no Atlas Admin API wording)
  And no MongoDB client or Atlas Admin API call is made

Scenario: Preflight accepts healthy Postgres schema
  Given STORAGE_BACKEND=postgres and all required catalog objects exist
  When an experiment is submitted
  Then preflight does not 422 for index reasons

Scenario: Db-stats returns sizes without Atlas Admin API
  Given STORAGE_BACKEND=postgres (local or hosted)
  When db-stats / vector-db-stats is called
  Then the response includes database size fields the dashboard already renders
  And storage_mode (and cluster_tier_type if still present) is one of
      mongodb-local|mongodb-cloud|postgres-local|postgres-cloud

Scenario: Storage mode — mongodb-cloud
  Given STORAGE_BACKEND=mongodb (or legacy mongo) and an Atlas cloud MONGODB_URI
  When GET /healthz is queried
  Then the JSON body has storage_mode equal to mongodb-cloud

Scenario: Storage mode — mongodb-local
  Given STORAGE_BACKEND=mongodb and a non-Atlas / localhost MONGODB_URI
  When GET /healthz is queried
  Then the JSON body has storage_mode equal to mongodb-local

Scenario: Storage mode — postgres-local
  Given STORAGE_BACKEND=postgres and a local Docker DATABASE_URL
  When GET /healthz is queried
  Then the JSON body has storage_mode equal to postgres-local

Scenario: Storage mode — postgres-cloud
  Given STORAGE_BACKEND=postgres and a hosted Supabase DATABASE_URL
  When GET /healthz is queried
  Then the JSON body has storage_mode equal to postgres-cloud

Scenario: Mode token matches planned flag vocabulary
  Given any healthy server
  When storage_mode is read from /healthz
  Then docs describe ./start-services.sh --{storage_mode} as the restart command for that mode
  (flags themselves may still be unimplemented until Slice 37)

Scenario: indexes list shows known vs missing indexes on Postgres
  Given STORAGE_BACKEND=postgres
  When rag-params-finder indexes list runs
  Then output distinguishes present vs required-missing catalog index names
```

---

## Before-Checks [GATE]

- [x] Slice 35 ✅ COMPLETE — `gate-evidence/slice-35.json` (PR #112); soft dep on Slice 43 ✅ does not block
- [x] Prefer `pg_*` size functions before Supabase Management API — already used in `postgres_stats._cluster_storage_mb`
- [x] Confirm Slice 33 `postgres_stats.py` baseline before extending — present; emits old `cluster_tier_type` tokens
- [x] Sync with Slice 43 operator contract — `STORAGE_BACKEND` vs `database_provider`; env asymmetry documented; rename backlog stays 37
- [x] nw-solution-architect-reviewer CONDITIONAL → remediations applied (preflight SQL + behavioral GWT + module/mode decisions)
- [x] Branch `slice/36-postgres-preflight-stats` created from current `main`
- [x] Quality gates green on branch tip before RED — unit tier 282 passed; ruff/mypy clean on touched modules (2026-07-26)

---

## After-Checks [GATE]

- [x] 422 parity with Mongo preflight UX (actionable detail; no Atlas calls on postgres)
- [x] Dashboard stats smoke on Postgres — live reload 2026-07-26: `/healthz` → `storage_mode=postgres-local`; vector-db-stats `cluster_tier_type`/`storage_mode` = `postgres-local` (not `local-postgres`); dashboard HTTP 200; `indexes list` all PRESENT
- [x] Storage mode field documented; values match planned Slice 37 flag names exactly
- [x] **Slice 27 absorbed:** named tests for all four modes (`mongodb-local`, `mongodb-cloud`, `postgres-local`, `postgres-cloud`)
- [x] No user-facing **mode** string is `supabase`, `local-postgres`, bare `mongo`, or bare `mongodb` (`database_provider: supabase` remains YAML/metadata until Slice 37)
- [x] Mongo preflight/stats still pass when `STORAGE_BACKEND=mongodb` (legacy `mongo` alias OK)
- [x] Does **not** implement start-services four-flag parse or config↔server 422 (owned by 37)
- [x] Specification coverage: every GWT clause has at least one test; essential error paths covered
- [x] Branch coverage: scoped unit suites for plan/guard/health/mode helpers green (~86% combined with branch); exclusions documented — Atlas I/O branches in `search_index_guard` (Mongo path), URI edge helpers in `mongodb_uri`/`postgres_uri` (`parse_*`, TLS defaults), `postgres_stats` exercised via live smoke rather than unit import
- [x] Mutation testing: **waived** — no local mutmut/cosmic-ray; nightly CI carries mutation signal (DECISIONS #101, #95 precedent)
- [x] Coverage + quality gates — unit tier green after implementation; pre-push gates passed on feat commit
- [x] Doc audit (`/sync-docs`, 2026-07-26): PRD §Documentation matrix rows claimed for **36** — `cli-reference.md` (`/healthz` body + `storage_mode` note), `configuration.md` (storage-mode), `troubleshooting.md` (new §Postgres index preflight failed), `postgres-setup.md` (§Index preflight + operational checks), `architecture.md` (module map + capability rows), `development.md` (test tiers), `local-environment.md`, `CLAUDE.md` (Key Files + 282-test baseline), `AGENTS.md`, `CHANGELOG.md`
- [x] `docs/plan/slices/PROGRESS.md` updated — COMPLETE

## Gate Status

✅ COMPLETE / PASSED — 2026-07-26 (`gate-evidence/slice-36.json`)
