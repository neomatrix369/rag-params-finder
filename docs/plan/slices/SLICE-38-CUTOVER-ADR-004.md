# SLICE 38 — Side-by-Side Quality Gate + ADR-004 + Default Cutover

**MoSCoW:** MUST
**Target time:** ~3–4 h
**Status:** 🔨 IN PROGRESS
**Depends on:** 37
**Branch:** `slice/38-cutover-adr-004`
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../PRD-supabase-pgvector-migration.md) §6.6, §9

> **Synced 2026-07-26** (enhanced-flow-planner continuation): foundations from Slices 34–37 + 43 are on `main`; this slice owns comparison artifact, ADR-004, and default flip only — not re-scoping operator DX.
>
> **Remediated 2026-07-26** after [nw-platform-architect-reviewer](42fbfa86-9fb2-45a3-a094-6915b2c22e1a) **NEEDS REVISION** — remediations 1–8 applied (DECISIONS #114–#118).
>
> **Branch accounting 2026-07-26:** Path A code remediations + local DB image pins landed on `slice/38-cutover-adr-004` (commits `96316bb`, `0f6ba2d` + follow-up pin/FCV recovery). Comparison + ADR-004 + default flip remain open.

---

## Slice Workflow Bundle

- Slice name: `slice-38-cutover-adr-004`
- Branch: `slice/38-cutover-adr-004`
- PR: https://github.com/neomatrix369/rag-params-finder/pull/118 (checkpoint — not cutover-complete)
- Files (expected):
  - `docs/adr/ADR-004-postgresql-pgvector-vector-store.md` (**create** — still open)
  - `docs/adr/ADR-003-mongodb-atlas-vector-store.md` — Status → Superseded by ADR-004 (**open**); pin note already updated for Atlas Local `8.3.3`
  - `docs/plan/gate-evidence/slice-38-quality-comparison.md` — Mongo vs Postgres rankings + latency (**open**)
  - `docs/plan/gate-evidence/slice-38.json` — gate closure stub (job conclusions + run URLs, not the word "green") (**open**)
  - **Default flip surfaces (all three — BLOCKER-1; flip still deferred):**
    - `server/settings.py` — `storage_backend` default (+ placeholder URI reject — **landed**)
    - `scripts/lib/storage_mode.sh` — bare-start `${STORAGE_BACKEND:-…}` fallback + `export_storage_backend_for_stack` (**landed**)
    - `docker-compose.yml` — `STORAGE_BACKEND: ${STORAGE_BACKEND:-…}` + comment; Mongo/Postgres image pins (**landed**)
  - `start-services.sh` — Mongo branch of `apply_stack_profiles()` exports `STORAGE_BACKEND=mongodb` (**landed**)
  - `scripts/lib/compose.sh` — FCV / `Wrong mongod version` hint on unhealthy / timeout (**landed**)
  - `.github/workflows/ci.yml` — Atlas Local + pgvector image pins match compose (**landed**)
  - `.env.example` — comment out placeholder `SUPABASE_URI`; document postgres default; placeholder rejection for Postgres URIs (`<project-ref>`) (**landed** for reject + comment-out)
  - Docs: README / getting-started / postgres-setup / mongodb-setup cross-links; `CLAUDE.md` Key Files default note (post-flip `/sync-docs`); mongodb-setup FCV callout (**landed**)
  - Rollback docs: two-command recipes (`--mongodb-*` / `--postgres-*` + matching `configs/{mongodb,supabase}/…`)
  - Optional: remove dead Mongo-only docs paths only after comparison signed off
  - ~~Deprecated `--local` / `--postgres` flag aliases~~ — **DONE in Slice 37** (DECISIONS #108/#109); env `RAG_LOCAL_*` remain until a later cleanup
- Exit criteria: ADR-004 merged; side-by-side comparison documented; default backend Postgres with Mongo still selectable via flags/env; rollback under hostile `.env` verified
- Commit pattern: `docs(slice-38): adr-004 pgvector cutover and quality comparison`
- **Doc exit:** `/sync-docs` — ADR-004, CHANGELOG, README default backend, mongodb-setup + postgres-setup cross-links, architecture dual-backend, CLAUDE.md Key Files

---

## Landed on this branch (accounted — do not re-implement)

| Item | Evidence | Status |
|---|---|---|
| Mongo flags force `STORAGE_BACKEND=mongodb` (hostile leftover `.env`) | `export_storage_backend_for_stack`; `compose_export_local_atlas_env`; `apply_stack_profiles` | ✅ `96316bb` |
| Reject placeholder Postgres URIs (`<project-ref>`, etc.) | `ensure_stack_mode_env` + `Settings.ensure_storage_ready` | ✅ `96316bb` |
| Comment out `.env.example` `SUPABASE_URI` placeholder | `.env.example` | ✅ `96316bb` |
| Default remains `mongodb` until comparison gates PASS | settings + shell + compose fallbacks unchanged for cutover | ✅ fail-closed (#119) |
| Unit coverage for resolver / URI alias | `tests/test_storage_mode_resolve.py`, `tests/test_supabase_uri_alias.py` | ✅ |
| Pin Atlas Local `mongodb/mongodb-atlas-local:8.3.3` | `docker-compose.yml`, CI `mongo-integration`, ADR-003 / architecture / mongodb-setup / CHANGELOG | ✅ (#120; revised off `8.0.9`) |
| Pin local pgvector `pgvector/pgvector:0.8.5-pg16` | `docker-compose.yml`, CI | ✅ (#120) |
| FCV mismatch operator hint | `wait_for_mongodb_local_healthy` in `scripts/lib/compose.sh`; mongodb-setup callout | ✅ |
| Runtime recovery after FCV churn | `mongodb reset` + `mongodb start` + restart server when ping-healthy but `NotPrimaryOrSecondary` / invalid RS | ✅ verified 2026-07-26 (#121) |
| Postgres container ops parity (wait helper, reset hints, `:5433` conflict UX) | `wait_for_postgres_local_healthy` + `print_postgres_local_reset_hint`; hints use `postgres reset` | ✅ (#122) |
| Dual-container `health-check.sh` | Active `/healthz` backend + probe present Atlas Local **and** pgvector containers | ✅ (#123) |
| Mongo↔Postgres operator doc parity (sync-docs) | QUICKSTART Path D, postgres-setup native-dev/ops table, troubleshooting, local-environment, architecture, CLAUDE indexes, mode-aware SIE footer | ✅ (#124) |

**Not landed (still Must for COMPLETE):** dual-backend comparison artifact · ADR-004 · ADR-003 Superseded · default flip · `slice-38.json` · full `/sync-docs`.

---

## Already landed elsewhere (do not re-scope)

| Foundation | Owner | Live evidence |
|---|---|---|
| Storage + Retriever ports; Mongo + Postgres adapters | Slices **32–35** | Code on `main`; formal 32/32B/32C/33 tracker still open (gate-closure debt — **not** a cutover blocker if 34–37 evidence holds; ADR-004 Consequences: 32C must not change port semantics post-cutover) |
| Dense pgvector + Atlas-scale scores | Slice **34** | `gate-evidence/slice-34.json` |
| Sparse tsvector + hybrid RRF; Lucene drift → CONDITIONAL | Slice **35** | `gate-evidence/slice-35.json` — full dual-backend matrix **owned here** |
| Catalog preflight 422 + four-value `storage_mode` | Slice **36** | `gate-evidence/slice-36.json` |
| Four-flag grid + config↔server 422 + `SUPABASE_URI` + hosted smoke | Slice **37** | `gate-evidence/slice-37.json` — exp `1903dc76…` local, `49c23d41…` hosted |
| `configs/supabase/*` twins + operator `STORAGE_BACKEND` vs YAML docs | Slice **43** | `gate-evidence/slice-43.json`; 16/16 local Postgres smoke (**authoritative comparison shape** — DECISIONS #115) |
| Shared live `StorageBackend` contract suite | Hygiene (pre-38) | `tests/contract/test_storage_backend_contract.py` + CI `mongo-integration` / `postgres-integration` |
| Canonical token `STORAGE_BACKEND=mongodb` (`mongo` alias) | Slice **43** / settings | `normalize_storage_backend()` — **never** document bare `mongo` as the cutover/rollback spelling |

---

## Goal

Close the migration: document retrieval-quality comparison (**equivalent quality, not identical scores**), author ADR-004 superseding ADR-003, and switch the **code + documented default** to Postgres while keeping the Mongo adapter for rollback.

**Production target mode:** `postgres-cloud` (Supabase-hosted) is the recommended **production** default — ADR-004 Consequences must state **Pro (or non-pausing) tier** for warm demos (free-tier auto-pause is a known risk). `postgres-local` remains the zero-cloud / CI / laptop path and the safest post-flip first-run experience when no URI is configured.

**Authoritative comparison baseline (DECISIONS #115):** Slice 43 shape — mirrored stems under `configs/mongodb/` and `configs/supabase/` (e.g. `example-local.yaml`), **384-dim local** embeddings, dense/sparse/hybrid (+ cross_encoder if present). ADR-003 records **no** baseline p99 — both backends are measured **fresh** in this slice. The PRD's illustrative `36×1000×1024` Voyage shape is **not** required for the cutover claim (infeasible at free-tier RPM inside 3–4 h).

**Latency metric (DECISIONS #114):** Use **QUERYING-phase `elapsed_ms`** already recorded on `run_status` (median and max across matched runs). Pass if Postgres median ≤ **2×** Mongo median **and** Postgres max ≤ **2×** Mongo max. Do **not** invent a p99 probe in this slice. Whole-run Aim `latency_ms` may be noted as secondary context only.

**Operator vocabulary (from Slice 37 — do not regress):**

| Flag / mode | Product wording |
|---|---|
| `--mongodb-cloud` / `mongodb-cloud` | Atlas cloud |
| `--mongodb-local` / `mongodb-local` | Atlas Local |
| `--postgres-cloud` / `postgres-cloud` | Supabase-hosted Postgres |
| `--postgres-local` / `postgres-local` | local pgvector / Postgres |

Rollback and A/B stay **two-command** (start flag + matching example config). Do not reintroduce hand-edited `STORAGE_BACKEND` as the only documented path.

Canonical URI: `DATABASE_URL`; optional alias: `SUPABASE_URI` (when unset). Placeholder URIs must fail closed with a clear remediation message (BLOCKER-4).

---

## Spec (GWT)

```
Scenario: Side-by-side comparison recorded
  Given the same persona question-set and corpus
    (authoritative: mirrored Slice 43 stems under configs/mongodb/ and configs/supabase/,
     e.g. example-local.yaml — 384-dim local)
  When dense/sparse/hybrid run on Mongo and Postgres
  Then docs/plan/gate-evidence/slice-38-quality-comparison.md exists
    with top-1/top-3/top-5 rank overlap (and optional NDCG)
  And the measured top-3 overlap percentage is always recorded numerically
  And the artifact states whether postgres-cloud and/or postgres-local were measured
  And equivalence is PASS (≥80% top-3 overlap) or CONDITIONAL
    only when measured overlap ≥50% AND a named DECISIONS sign-off exists
    (Lucene BM25 vs ts_rank drift may justify CONDITIONAL above the floor —
     never a self-granted waiver below 50%)

Scenario: Latency gate recorded
  Given matched QUERYING-phase elapsed_ms samples on both backends
  When median and max are compared
  Then Postgres median ≤ 2× Mongo median AND Postgres max ≤ 2× Mongo max
    OR the cutover default is NOT flipped
  And the artifact records the raw medians/maxes (no silent proxy substitution)

Scenario: ADR-004 supersedes ADR-003
  Given ADR-004 is authored (context, decision, consequences,
    quality rationale, cost note, post-cutover monitoring, rollback,
    Pro-tier note for postgres-cloud, 32C port-semantics freeze)
  When ADR-003 is opened
  Then its status is Superseded and links to ADR-004

Scenario: Fresh clone defaults to Postgres without a broken URI
  Given a fresh clone with .env.example copied and no real DATABASE_URL/SUPABASE_URI
  When the server starts under the post-cutover default
  Then the operator gets a clear remediation error requiring DATABASE_URL or SUPABASE_URI
    (or is guided to --postgres-local), not an opaque connect to <project-ref>
  And /healthz with no STORAGE_BACKEND set reports storage_backend=postgres

Scenario: Default backend is Postgres; Mongo still works
  Given post-cutover defaults
  When the operator selects Mongo via --mongodb-cloud or --mongodb-local
  Then Mongo remains usable for rollback
  And rollback docs use canonical mongodb (not bare mongo)

Scenario: Rollback under hostile leftover .env
  Given .env still contains STORAGE_BACKEND=postgres after cutover
  When ./start-services.sh --mongodb-local runs
  Then /healthz reports storage_mode=mongodb-local
    (Mongo branch exports STORAGE_BACKEND=mongodb symmetrically)

Scenario: Dual-backend CI evidence recorded
  Given CI jobs mongo-integration and postgres-integration
  When the cutover PR completes
  Then gate-evidence/slice-38.json records each job's conclusion + run URL
    (skipped ≠ green; dual-backend green is the union of both jobs)

Scenario: Comparison run aborts or is partial
  Given a dual-backend comparison that fails mid-flight or covers only one mode
  When the artifact is written
  Then it states partial scope and must NOT claim PASS or flip the default

Scenario: Hosted Supabase unreachable mid-comparison
  Given postgres-cloud is unavailable (paused / connect error)
  When only postgres-local completes
  Then mode scope is recorded as postgres-local only and the production
    cutover claim is withheld until postgres-cloud is measured
```

---

## Non-goals this slice

- Deleting the Mongo adapter (Won't until a later cleanup slice)
- Claiming byte-identical scores or closing Slice 35 Lucene/`ts_rank` drift as identical
- Building a new per-query p99 latency probe (use QUERYING `elapsed_ms` — DECISIONS #114)
- Running the illustrative PRD 36×1000×1024 Voyage sweep as a hard Before-Check (DECISIONS #115)
- Formal gate-closure of tracker rows 32 / 32B / 32C / 33 (parallel debt; not required to flip default if 34–37 evidence holds — log explicitly in comparison artifact + ADR-004)
- Re-doing Slice 37 flag/422/hosted DX work
- Mandatory removal of env `RAG_LOCAL_*` aliases (Could — later cleanup)
- Frontend coverage floor (Slice **44**)
- Changing Atlas Local / pgvector healthchecks to assert writable primary (Could — ping-only remains; document reset path instead — #121)

---

## Before-Checks [GATE]

- [ ] Slices **34–37** and **43** ✅ COMPLETE with gate-evidence on disk
- [ ] Slice **37** hosted Path B evidence present (`postgres-cloud` smoke in `slice-37.json`) — required for production-default claim
- [ ] Contract suite + CI dual-backend jobs exist (`tests/contract/`, `mongo-integration`, `postgres-integration`)
- [ ] Authoritative baseline configs identified (mirrored Slice 43 stems) — both backends measurable fresh
- [ ] Cutover gates measured (QUERYING elapsed_ms ≤2×; hybrid overlap ≥80% or CONDITIONAL with floor+sign-off)
- [ ] Rollback playbook smoke-tested including **hostile** leftover `STORAGE_BACKEND=postgres` + `--mongodb-local`
- [ ] Tracker note: 32/32B/32C/33 may still show 🔨/📋 — acknowledge in DECISIONS / comparison artifact / ADR-004

---

## After-Checks [GATE]

- [ ] All PRD acceptance criteria for cutover checked or explicitly deferred with reason
- [ ] PRD §9 boxes owned by 33–37 ticked with evidence pointers (`slice-34/35/36/37.json`) so only genuine-38 work remains open
- [ ] Specification coverage: every GWT clause has at least one test **or** dated runtime probe recorded in `slice-38-quality-comparison.md` (docs/ADR slice — probes count; unit/shell tests for default flip + hostile rollback + placeholder rejection still required)
- [ ] Branch coverage: target 100% on touched Python/shell helpers; document exclusions
- [ ] Mutation testing: waive with DECISIONS row if docs-only + small defaults (same pattern as #101/#95) **or** run if non-trivial logic added
- [ ] ADR-004 + ADR-003 status update
- [ ] Comparison artifact in `docs/plan/gate-evidence/slice-38-quality-comparison.md`:
  - Query set, corpus, configs used, snapshot date
  - Metrics (top-1, top-3, top-5 rank overlap; NDCG optional) — **numeric top-3 always present**
  - **Latency:** QUERYING elapsed_ms median/max Mongo vs Postgres; PASS if ≤2×
  - **Hybrid drift / equivalence:** ≥80% top-3 → PASS; else CONDITIONAL only if ≥50% + DECISIONS sign-off
  - Dense/sparse/hybrid results for Mongo and Postgres
  - Mode scope: `postgres-cloud` (required for production claim) and optionally `postgres-local`
  - Equivalence decision: PASS or CONDITIONAL with trade-offs
  - **Secrets redaction:** provider + region-level host + variable *name* only (pattern from `slice-37.json`) — never full URIs or passwords
- [ ] Cutover decision explicit: default backend flipped to postgres **only if** latency + equivalence gates allow; else keep default mongodb and ship ADR as Proposed / deferred flip
- [ ] Rollback criteria documented: revert to mongodb if incident recovery >30 min (two-command recipe); monitoring plan uses existing signals (`/healthz` storage_mode + postgres ok, QUERYING-phase failure counts, Supabase pause remediation)
- [ ] ADR-004 includes quality comparison rationale, cost note (Atlas M0 vs Supabase), Pro-tier note for `postgres-cloud`, 32C port-semantics freeze, and post-cutover monitoring plan
- [ ] CI dual-backend evidence: `slice-38.json` stores each job conclusion + run URL
- [ ] Doc audit: PRD §Documentation matrix rows for slice **38** (ADR-004, ADR-003, gate-evidence, CHANGELOG, mongodb-setup + postgres-setup cross-link, README default, CLAUDE.md Key Files)
- [ ] `/sync-docs` run — full user + contributor footprint after cutover
- [ ] `docs/plan/slices/PROGRESS.md` + `TRAIL.md` updated
- [ ] Graphiti episode: cutover decision (`rag-params-finder-flow-planner`)
- [ ] PRD rollback spelling: `N/A — verified 2026-07-26` (canonical `mongodb` already applied)

## Gate Status

🔨 IN PROGRESS — **partial**

| Gate area | State |
|---|---|
| Review remediations (#114–#119) | ✅ IMPLEMENTED (`96316bb`) |
| Local DB image pins + FCV recovery docs (#120–#121) | ✅ IMPLEMENTED / VERIFIED (healthy `8.3.3` + writable primary after reset) |
| Postgres ↔ Mongo container-ops UX parity (#122) | ✅ IMPLEMENTED (shared wait + reset hints + `:5433` conflict) |
| Dual-container health-check + operator doc parity (#123–#124) | ✅ IMPLEMENTED / sync-docs APPLIED |
| Dual-backend quality + latency comparison | 📋 open |
| ADR-004 + ADR-003 Superseded | 📋 open |
| Default flip to `postgres` | 📋 blocked until comparison PASS (fail-closed) |
| `slice-38.json` + `/sync-docs` + tracker COMPLETE | 📋 open |

**PR #118** is a checkpoint only — not cutover-complete.
