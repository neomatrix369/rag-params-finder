# SLICE 38 — Side-by-Side Quality Gate + ADR-004 + Default Cutover

**MoSCoW:** MUST
**Target time:** ~3–4 h
**Status:** ✅ COMPLETE
**Depends on:** 37
**Branch:** `slice/38-cutover-adr-004`
**PR:** https://github.com/neomatrix369/rag-params-finder/pull/118
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../../PRD-supabase-pgvector-migration.md) §6.6, §9

> **Closed 2026-07-26:** ADR-004 Accepted · local comparison VERIFIED · CI dual-backend recorded · **no default flip** (DECISIONS #130 Won't) — code default stays `mongodb`; backends independently selectable (#129).

---



## Slice Workflow Bundle

- Slice name: `slice-38-cutover-adr-004`
- Branch: `slice/38-cutover-adr-004`
- PR: [https://github.com/neomatrix369/rag-params-finder/pull/118](https://github.com/neomatrix369/rag-params-finder/pull/118) (Slice 38 COMPLETE; default not flipped)
- Files (expected):
  - `docs/adr/ADR-004-postgresql-pgvector-vector-store.md` (**Accepted** 2026-07-26 — dual-backend; no default flip #130)
  - `docs/adr/ADR-003-mongodb-atlas-vector-store.md` — Status → **Superseded** by ADR-004 (Mongo still supported)
  - `docs/plan/gate-evidence/slice-38-quality-comparison.md` — Mongo vs Postgres rankings + latency (**VERIFIED** 2026-07-26)
  - `docs/plan/gate-evidence/slice-38.json` — gate closure (**PASSED** — CI + comparison; flip gate removed #130)
  - **Default flip surfaces (all three — BLOCKER-1; flip still deferred):**
    - `server/settings.py` — `storage_backend` default (+ placeholder URI reject — **landed**)
    - `scripts/lib/storage_mode.sh` — bare-start `${STORAGE_BACKEND:-…}` fallback + `export_storage_backend_for_stack` (**landed**)
    - `docker-compose.yml` — `STORAGE_BACKEND: ${STORAGE_BACKEND:-…}` + comment; Mongo/Postgres image pins (**landed**)
  - `start-services.sh` — Mongo branch of `apply_stack_profiles()` exports `STORAGE_BACKEND=mongodb` (**landed**)
  - `scripts/lib/compose.sh` — FCV / `Wrong mongod version` hint on unhealthy / timeout (**landed**)
  - `.github/workflows/ci.yml` — Atlas Local + pgvector image pins match compose (**landed**)
  - `.env.example` — comment out placeholder `SUPABASE_URI`; document postgres default; placeholder rejection for Postgres URIs (`<project-ref>`) (**landed** for reject + comment-out)
  - Docs: README / getting-started / postgres-setup / mongodb-setup cross-links; `CLAUDE.md` Key Files default note; mongodb-setup FCV callout (**landed**)
  - Rollback docs: two-command recipes (`--mongodb-*` / `--postgres-*` + matching `configs/{mongodb,supabase}/…`)
  - Optional: remove dead Mongo-only docs paths only after comparison signed off
  - ~~Deprecated~~ `--local` ~~/~~ `--postgres` ~~flag aliases~~ — **DONE in Slice 37** (DECISIONS #108/#109); env `RAG_LOCAL_`* remain until a later cleanup
- Exit criteria: local dual-backend comparison documented; ADR-004 Accepted; backends independently selectable (#129); no default-flip gate (#130); `slice-38.json` PASSED
- Commit pattern: `docs(slice-38): adr-004 pgvector cutover and quality comparison`
- **Doc exit (Must):** CHANGELOG + PROGRESS/TRAIL + ADR files. Operator `/sync-docs` footprint → Slice 43 residuals (#126)

---



## Landed on this branch (accounted — do not re-implement)


| Item                                                                          | Evidence                                                                                                                                        | Status                        |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| Mongo flags force `STORAGE_BACKEND=mongodb` (hostile leftover `.env`)         | `export_storage_backend_for_stack`; `compose_export_local_atlas_env`; `apply_stack_profiles`                                                    | ✅ `96316bb`                   |
| Reject placeholder Postgres URIs (`<project-ref>`, etc.)                      | `ensure_stack_mode_env` + `Settings.ensure_storage_ready`                                                                                       | ✅ `96316bb`                   |
| Comment out `.env.example` `SUPABASE_URI` placeholder                         | `.env.example`                                                                                                                                  | ✅ `96316bb`                   |
| Code default stays `mongodb` permanently (#130 Won't flip) | settings + shell + compose fallbacks unchanged; backends independently selectable (#129) | ✅ (#119 remediations; #129 independence; #130 Won't) |
| Unit coverage for resolver / URI alias                                        | `tests/test_storage_mode_resolve.py`, `tests/test_supabase_uri_alias.py`                                                                        | ✅                             |
| Pin Atlas Local `mongodb/mongodb-atlas-local:8.3.3`                           | `docker-compose.yml`, CI `mongo-integration`, ADR-003 / architecture / mongodb-setup / CHANGELOG                                                | ✅ (#120; revised off `8.0.9`) |
| Pin local pgvector `pgvector/pgvector:0.8.5-pg16`                             | `docker-compose.yml`, CI                                                                                                                        | ✅ (#120)                      |
| FCV mismatch operator hint                                                    | `wait_for_mongodb_local_healthy` in `scripts/lib/compose.sh`; mongodb-setup callout                                                             | ✅                             |
| Runtime recovery after FCV churn                                              | `mongodb reset` + `mongodb start` + restart server when ping-healthy but `NotPrimaryOrSecondary` / invalid RS                                   | ✅ verified 2026-07-26 (#121)  |
| Postgres container ops parity (wait helper, reset hints, `:5433` conflict UX) | `wait_for_postgres_local_healthy` + `print_postgres_local_reset_hint`; hints use `postgres reset`                                               | ✅ (#122)                      |
| Dual-container `health-check.sh`                                              | Active `/healthz` backend + probe present Atlas Local **and** pgvector containers                                                               | ✅ (#123)                      |
| Mongo↔Postgres operator doc parity (sync-docs)                                | QUICKSTART Path D, postgres-setup native-dev/ops table, troubleshooting, local-environment, architecture, CLAUDE indexes, mode-aware SIE footer | ✅ (#124)                      |


**Complete (#130 Won't flip):** ADR-004 · CI dual-backend (`slice-38.json`) · mutation #128 · local comparison VERIFIED · tracker/CHANGELOG close-out · code default stays `mongodb` with no flip gate. Non-100%-Yes gates → Slice 43 residuals (#125/#126).

---



## Already landed elsewhere (do not re-scope)


| Foundation                                                           | Owner                   | Live evidence                                                                                                                                                                                          |
| -------------------------------------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Storage + Retriever ports; Mongo + Postgres adapters                 | Slices **32–35**        | Code on `main`; formal 32/32B/32C/33 tracker still open (gate-closure debt — **not** a cutover blocker if 34–37 evidence holds; ADR-004 Consequences: 32C must not change port semantics post-cutover) |
| Dense pgvector + Atlas-scale scores                                  | Slice **34**            | `gate-evidence/slice-34.json`                                                                                                                                                                          |
| Sparse tsvector + hybrid RRF; Lucene drift → CONDITIONAL             | Slice **35**            | `gate-evidence/slice-35.json` — full dual-backend matrix **owned here**                                                                                                                                |
| Catalog preflight 422 + four-value `storage_mode`                    | Slice **36**            | `gate-evidence/slice-36.json`                                                                                                                                                                          |
| Four-flag grid + config↔server 422 + `SUPABASE_URI` + hosted smoke   | Slice **37**            | `gate-evidence/slice-37.json` — exp `1903dc76…` local, `49c23d41…` hosted                                                                                                                              |
| `configs/supabase/*` twins + operator `STORAGE_BACKEND` vs YAML docs | Slice **43**            | `gate-evidence/slice-43.json`; 16/16 local Postgres smoke (**authoritative comparison shape** — DECISIONS #115)                                                                                        |
| Shared live `StorageBackend` contract suite                          | Hygiene (pre-38)        | `tests/contract/test_storage_backend_contract.py` + CI `mongo-integration` / `postgres-integration`                                                                                                    |
| Canonical token `STORAGE_BACKEND=mongodb` (`mongo` alias)            | Slice **43** / settings | `normalize_storage_backend()` — **never** document bare `mongo` as the cutover/rollback spelling                                                                                                       |


---



## Goal

Close the migration: document retrieval-quality comparison (**equivalent quality, not identical scores**), author ADR-004 superseding ADR-003, and keep both adapters as **independent** selectable engines. The **code + documented default** stays `mongodb` permanently (DECISIONS #130 — **Won't** flip). Comparison evidence supports operator A/B choice, not a default cutover (DECISIONS #129).

**Production target mode (aspirational):** `postgres-cloud` remains a recommended **hosted Postgres** choice in ADR-004 prose (Pro / non-pausing tier note). **Local comparison** (`mongodb-local` ↔ `postgres-local`, Slice 43 shape) records quality/latency so operators can choose; it does not flip the code default (#130) and does not make one backend a safety net for the other. Hosted quality/latency matrix and production-claim sign-off are parked on **Slice 43** residuals (not a Slice 38 COMPLETE blocker).

**Authoritative comparison baseline (DECISIONS #115):** Slice 43 shape — mirrored stems under `configs/mongodb/` and `configs/supabase/` (e.g. `example-local.yaml`), **384-dim local** embeddings, dense/sparse/hybrid (+ cross_encoder if present). ADR-003 records **no** baseline p99 — both backends are measured **fresh** in this slice. The PRD's illustrative `36×1000×1024` Voyage shape is **not** required for the dual-backend claim (infeasible at free-tier RPM inside 3–4 h).

**Latency metric (DECISIONS #114):** Use **QUERYING-phase** `elapsed_ms` already recorded on `run_status` (median and max across matched runs). Record Postgres/Mongo median and max ratios as operator evidence. Do **not** invent a p99 probe in this slice. Whole-run Aim `latency_ms` may be noted as secondary context only.

**Operator vocabulary (from Slice 37 — do not regress):**


| Flag / mode                           | Product wording           |
| ------------------------------------- | ------------------------- |
| `--mongodb-cloud` / `mongodb-cloud`   | Atlas cloud               |
| `--mongodb-local` / `mongodb-local`   | Atlas Local               |
| `--postgres-cloud` / `postgres-cloud` | Supabase-hosted Postgres  |
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
  And top-3 overlap is always recorded numerically (informational under #129)
  And the artifact states mode scope mongodb-local + postgres-local
    (hosted postgres-cloud production-claim matrix → Slice 43 residuals)
  And historical PASS/CONDITIONAL labels may annotate closeness
    but cross-engine mismatch does not fail the independent-backend model (#129)

Scenario: Latency evidence recorded
  Given matched QUERYING-phase elapsed_ms samples on both local backends
  When median and max are compared
  Then the artifact records the raw medians/maxes and Postgres/Mongo ratios
    (no silent proxy substitution)
  And those ratios are operator evidence only
    (backends remain independently selectable — DECISIONS #129; no default flip — #130)

Scenario: ADR-004 supersedes ADR-003
  Given ADR-004 is Accepted (context, decision, consequences,
    local quality rationale, cost note, independent engine switch, monitoring,
    32C port-semantics freeze)
  When ADR-003 is opened
  Then its status is Superseded (Accepted→Superseded) and links to ADR-004

Scenario: Independent engine switch under hostile leftover .env
  Given .env still contains STORAGE_BACKEND=postgres
    (hostile leftover postgres + Mongo flags)
  When ./start-services.sh --mongodb-local runs
  Then /healthz reports storage_mode=mongodb-local
    (Mongo branch exports STORAGE_BACKEND=mongodb symmetrically —
     deliberate engine select, not fail-over)

Scenario: Dual-backend CI evidence recorded
  Given CI jobs mongo-integration and postgres-integration
  When the cutover PR completes
  Then gate-evidence/slice-38.json records each job's conclusion + run URL
    (skipped ≠ green; dual-backend green is the union of both jobs)

Scenario: Comparison run aborts or is partial
  Given a dual-backend comparison that fails mid-flight or covers only one mode
  When the artifact is written
  Then it states partial scope and must NOT claim PASS or change the code default (#130)
```

---



## Non-goals this slice

- Deleting the Mongo adapter (Won't until a later cleanup slice)
- Claiming byte-identical scores or closing Slice 35 Lucene/`ts_rank` drift as identical
- Building a new per-query p99 latency probe (use QUERYING `elapsed_ms` — DECISIONS #114)
- Running the illustrative PRD 36×1000×1024 Voyage sweep as a hard Before-Check (DECISIONS #115)
- Formal gate-closure / PRD §9 tick of tracker rows 32 / 32B / 32C / 33 → **Slice 43** residuals
- Re-doing Slice 37 flag/422/hosted DX work
- Mandatory removal of env `RAG_LOCAL_*` aliases (Could — later cleanup)
- Frontend coverage floor (Slice **44**)
- Changing Atlas Local / pgvector healthchecks to assert writable primary (Could — #121)
- Everything in Slice **43** §Parked from Slice 38 (hosted production claim, Pro-tier ADR mandate, sync-docs/doc-matrix, shell coverage, Graphiti, baked-date PRD spelling, tracker one-liners)
- Changing the code/docs default from `mongodb` to `postgres` (DECISIONS #130 Won't)

---

## Before-Checks [GATE]

- [x] Slices **34–37** and **43** ✅ COMPLETE with gate-evidence on disk
- [x] Contract suite + CI dual-backend jobs exist (`tests/contract/`, `mongo-integration`, `postgres-integration`)
- [x] Authoritative baseline configs identified (mirrored Slice 43 stems) — both backends measurable fresh
- [x] Rollback playbook smoke-tested including **hostile** leftover `STORAGE_BACKEND=postgres` + `--mongodb-local`

---

## After-Checks [GATE]

Must for COMPLETE — only unambiguous cutover outcomes:

- [x] Comparison artifact `docs/plan/gate-evidence/slice-38-quality-comparison.md` for **local** dual-backend (Slice 43 shape) — **VERIFIED** 2026-07-26:
  - Query set, corpus, configs used, snapshot date
  - Metrics (top-1, top-3, top-5 rank overlap; NDCG optional) — **numeric top-3 present** (overall 45.7%; dense 92.9%)
  - **Latency:** QUERYING elapsed_ms median/max Mongo vs Postgres — **PASS** (≤2×); operator evidence only (#129/#130)
  - **Rank overlap:** recorded as **informational** under independent backends (#129) — not a fail-safe tripwire; historical ≥80%/≥50% labels kept as context only
  - Dense/sparse/hybrid results for Mongo and Postgres
  - Mode scope: `mongodb-local` + `postgres-local` only
  - Equivalence reading: comparison complete; mismatch expected across engines (#129)
  - **Secrets redaction:** provider + region-level host + variable *name* only — never full URIs or passwords
- [x] Cutover model explicit (**DECISIONS #129** + **#130**): Mongo and Postgres are **independent** selectable backends — neither is a fail-safe for the other. ADR-004 **Accepted** (dual-backend). Code/docs default stays `mongodb` permanently — **no flip gate**. Comparison evidence supports operator A/B only. Two-command rollback = switch engines, not automatic failover.
- [x] ADR-004 authored + ADR-003 Status → Superseded; Consequences include local quality rationale, cost note (Atlas M0 vs Supabase), 32C port-semantics freeze, rollback >30 min two-command recipe, monitoring via `/healthz` + QUERYING failures — **Accepted 2026-07-26**
- [x] CI dual-backend evidence: `docs/plan/gate-evidence/slice-38.json` stores each job conclusion + run URL (skipped ≠ green) — run `30218369352` on PR #118; both `mongo-integration` and `postgres-integration` conclusion=`success`
- [x] Mutation: waive with DECISIONS row (pattern #95/#101) unless non-trivial new Python logic is added — **#128**
- [x] `docs/plan/slices/PROGRESS.md` + `TRAIL.md` updated; CHANGELOG notes cutover decision — **COMPLETE** 2026-07-26; default-flip gate **removed** (#130 Won't)



## Gate Status

✅ COMPLETE — no default flip (#130 Won't)


| Gate area                                                                          | State                                                                     |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Review remediations (#114–#119)                                                    | ✅ IMPLEMENTED (`96316bb`)                                                 |
| Local DB image pins + FCV recovery docs (#120–#121)                                | ✅ IMPLEMENTED / VERIFIED (healthy `8.3.3` + writable primary after reset) |
| Postgres ↔ Mongo container-ops UX parity (#122)                                    | ✅ IMPLEMENTED (shared wait + reset hints + `:5433` conflict)              |
| Dual-container health-check + operator doc parity (#123–#124)                      | ✅ IMPLEMENTED / sync-docs APPLIED                                         |
| Before-Checks (prerequisites + hostile rollback)                                   | ✅                                                                         |
| Local dual-backend quality + latency comparison                                    | ✅ VERIFIED (`slice-38-quality-comparison.md`; latency PASS; overlap informational #129) |
| ADR-004 + ADR-003 Superseded                                                   | ✅ ADR-004 Accepted; ADR-003 Superseded                                    |
| Cutover model (independent backends, not fail-safe)                            | ✅ DECISIONS #129                                                          |
| Default flip to `postgres`                                                     | ✅ WON'T (#130) — gate removed; code default stays `mongodb` permanently   |
| `slice-38.json` dual-backend CI (skipped ≠ green)                                  | ✅ VERIFIED (run 30218369352; both jobs success)                           |
| Mutation waive                                                                     | ✅ DECISIONS #128                                                          |
| `slice-38.json` cutover close-out + tracker/CHANGELOG                              | ✅ COMPLETE                                                                |
| Non-100%-Yes gates (hosted claim, sync-docs, Pro-tier mandate, …) | → Slice **43** residuals (#125/#126)                                      |


**PR #118** — Slice 38 close-out; no default flip.
