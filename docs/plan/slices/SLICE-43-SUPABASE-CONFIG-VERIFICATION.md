# SLICE 43 — Supabase Example-Config Verification & Operator QoL

**MoSCoW:** Could
**Target time:** ~1–2 h
**Status:** 📋 PLANNED
**Depends on:** 35 ✅ (soft: 37 for hard config↔server 422)
**Non-blocking / non-urgent:** Does not gate 36–38 cutover. Pick up when operator friction appears or after Slice 37.

**Origin:** 2026-07-26 sanity check of `configs/supabase/` twins derived from `configs/mongodb/` — configs load/expand/parity ✅; residual risks recorded here. Extended same day with operator FAQ (“Supabase equivalent of `MONGODB_URI`?” → env naming asymmetry, §3) and by collating deferred/open items from PR bodies [#109](https://github.com/neomatrix369/rag-params-finder/pull/109)–[#113](https://github.com/neomatrix369/rag-params-finder/pull/113) (bodies only; provenance in *PR-body source index*).

**Planning quality lens (2026-07-26):** 9/10 pass. Fail = check 3 (SLAP) — the frontend-coverage item was a different abstraction level and has been spun out to [`SLICE-44-FRONTEND-COVERAGE-GATE.md`](SLICE-44-FRONTEND-COVERAGE-GATE.md). Duplications removed (old §6a ↔ §§1–5; old §6b ↔ §7). **MoSCoW note:** the slice priority is *Could* relative to the 36–38 migration track, but §1 (recorded live supabase smoke) is this slice’s definition-of-done, not optional.

---

## Slice Workflow Bundle

- Slice name: `slice-43-supabase-config-verification`
- Branch: `slice/43-supabase-config-verification`
- Files (expected):
  - `docs/user-guide/postgres-setup.md` (first-prove + hosted caveats + env table)
  - `docs/user-guide/configuration.md` (backend-switch note)
  - optional `configs/supabase/example-local-smoke.yaml`
  - optional live smoke notes under `docs/plan/gate-evidence/`
- Exit criteria (canonical “done” — After-Checks is the checkbox gate): recorded live smoke of ≥1 supabase example against Postgres; operator docs state `STORAGE_BACKEND` vs `database_provider` and the Mongo↔Postgres env asymmetry (rename backlog owned by 37); preferred short configs called out for hosted; each *Owned elsewhere* item still points at its owner slice.
- Commit pattern: `docs(slice-43): verify supabase example configs and clarify backend switch`

---

## Goal

Close the gap between **static** validation of `configs/supabase/*` (already green via `test_config_examples.py` + structural parity with mongodb twins) and **operator-proven** use against a live Postgres/Supabase backend — without blocking the Must migration track (36–38).

---

## In-scope work (MoSCoW for this slice)

| Priority | Item | Detail |
|----------|------|--------|
| **Must** | Live supabase smoke + recorded evidence | §1 |
| **Must** | Document backend switch is env (`STORAGE_BACKEND=postgres`), not YAML `database_provider` | §2 |
| **Must** | Document Mongo↔Postgres env asymmetry (no `SUPABASE_URI`; `DATABASE_URL` + backend flag) | §3 |
| **Should** | First-hosted-prove guidance; optional `example-local-smoke.yaml` | §4 |
| **Should** | Confirm HNSW truncated-top-k warning present in operator path | §5 |
| **Should** | Regression watch: docs don’t re-introduce Atlas/Mongo wording on Postgres paths | §6 |
| **Won’t (43)** | Env renames/aliases, config↔server 422, and everything under *Owned elsewhere* | → 22/32/36/37/38/41 |

---

## Findings already closed (do not re-open)

| Finding | Status | Source |
|---|---|---|
| YAML load / Pydantic / sweep expand for all 9 stems | ✅ Verified 2026-07-26 | Local sanity + [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) config reorg (`test_config_examples.py`) |
| Mongo ↔ Supabase structural parity (embedding/chunking/retrieval/execution) | ✅ Verified | Same; [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) notes 120-run grid parity |
| Dim → column map (384 / 1024) | ✅ Verified | Slice 33/34 |
| Sparse + hybrid on Postgres (`tsvector` + RRF) | ✅ Slice 35 | [#112](https://github.com/neomatrix369/rag-params-finder/pull/112) |
| Stale “Slice 35 raises” comments in supabase YAMLs | ✅ None remaining | Post-35 scrub |
| Atlas search-index preflight on Postgres / `/healthz` Mongo-only | ✅ Fixed | [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) (`d1385c5`, `636a46d`) |
| Ambient `STORAGE_BACKEND=postgres` poisoning unit / pre-push | ✅ Mitigated | [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) + [#113](https://github.com/neomatrix369/rag-params-finder/pull/113) unit/live split |
| Unit tier without `MONGODB_URI` | ✅ Fixed | [#113](https://github.com/neomatrix369/rag-params-finder/pull/113) (`6642cdd`) |
| Supabase/Postgres UI copy still saying Atlas/Mongo host | ✅ Scrubbed in 35; hygiene in 113 | [#112](https://github.com/neomatrix369/rag-params-finder/pull/112), [#113](https://github.com/neomatrix369/rag-params-finder/pull/113) |

---

## Residual issues — in scope for this slice (§§1–6)

### 1. Live E2E smoke missing
Static checks passed; no observed end-to-end sweep of a **supabase** example against running Postgres as operator evidence for this slice.

**Refs:** [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) proved dense smoke on local Postgres and config load/expand; it did **not** claim a recorded `configs/supabase/*` CLI sweep as gate evidence for operators. [#112](https://github.com/neomatrix369/rag-params-finder/pull/112) verified sparse/hybrid GWT on pgvector, not a full supabase-stem smoke table.

**Acceptance**
- [ ] Run and record: `./start-services.sh --postgres` then
  `rag-params-finder run --config configs/supabase/example-unified-retrievers.yaml`
  (16 runs — dense · sparse · hybrid · cross_encoder, local embeddings)
- [ ] Gate evidence note (command, date, experiment id / outcome) under `docs/plan/gate-evidence/` or PROGRESS Decision Log
- [ ] Optional stretch: same config (or smoke twin) against hosted Supabase `DATABASE_URL`

### 2. Backend switch is env, not YAML
`database_provider: supabase` is **metadata** (db-stats / labels). Runtime path is `STORAGE_BACKEND=postgres` + `DATABASE_URL`. Operators can submit a supabase YAML while the server is still on mongo.

**Refs:** Explicit deferred item in [#113](https://github.com/neomatrix369/rag-params-finder/pull/113) Documentation (“`database_provider` metadata”); config split in [#111](https://github.com/neomatrix369/rag-params-finder/pull/111); hard 422 owned by Slice 37.

**Acceptance**
- [ ] `postgres-setup.md` + `configuration.md` state this in one clear sentence each
- [ ] Hard reject / HTTP 422 on config↔server mismatch remains **Slice 37** — this slice only documents today’s behaviour and links to 37

### 3. Connection-env naming is asymmetric (Mongo vs Postgres/Supabase)

Operators naturally ask “what’s the Supabase equivalent of `MONGODB_URI`?” Today the answer is **not** a parallel name:

| Concern | Mongo (today) | Postgres / Supabase (today) |
|---|---|---|
| Connection string | `MONGODB_URI` | `DATABASE_URL` (no `SUPABASE_URI` / `POSTGRES_URI`) |
| Backend select | Often implicit (`STORAGE_BACKEND` defaults to `mongo`) | Explicit second knob: `STORAGE_BACKEND=postgres` |
| Config folder / YAML label | `configs/mongodb/` · `database_provider: mongodb` | `configs/supabase/` · `database_provider: supabase` |
| Runtime backend token | `mongo` (settings) | `postgres` (settings) — **not** `supabase` |

Definition and use diverge on three axes: **URI name**, **whether a backend flag is required**, and **folder/YAML label vs `STORAGE_BACKEND` value**. Correct, but easy to mis-teach and mis-configure.

**Refs:** Operator FAQ 2026-07-26; [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) commit narrative (“Selecting the postgres backend also drops the `MONGODB_URI` requirement”); `.env.example` comments.

**Acceptance (document now; rename later)**
- [ ] `postgres-setup.md` (and `.env.example` comment block) include a one-row “Mongo ↔ Postgres env” table matching the above
- [ ] Explicit note: there is no `SUPABASE_URI`; hosted and local both use `DATABASE_URL`
- [ ] Cross-link Slice **37** for future rename / alias work — **this slice does not rename env vars** (alias/one-knob backlog is owned by 37; see *Owned elsewhere*)

### 4. Hosted free-tier / large-grid risk
Full grids (e.g. `example-local.yaml` = 120 runs) may be slow or hit Supabase free-project limits. Not a correctness bug.

**Refs:** [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) verified mongodb vs supabase local parity at **120 runs** — fine for local CI/dev but a poor first hosted prove.

**Acceptance**
- [ ] Docs recommend first hosted prove: `example-unified-retrievers.yaml` or `*-bayesian.yaml` (dense-only)
- [ ] Optional: add `configs/supabase/example-local-smoke.yaml` (1 method × 1 size × dense) if operators still overshoot

### 5. HNSW post-filter recall (operator-invisible shortfall)
With filters (`experiment_id` / `embedding_model` / `run_id`), HNSW can return fewer than `LIMIT` rows unless `hnsw.iterative_scan = strict_order` is on. Failure mode is silent: scores change, no error.

**Refs:** [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) (`feat(slice-34)` + HNSW recall finding); already partially documented in `postgres-setup.md`.

**Acceptance**
- [ ] First-prove / troubleshooting section still warns about truncated top-k if iterative scan is off
- [ ] Link to existing postgres-setup HNSW note (do not duplicate a second long explanation)

### 6. Docs must not re-introduce Atlas/Mongo wording on Postgres paths
Regression watch after the Slice 35 / #113 copy scrub: operator docs and UI copy on Postgres/Supabase paths must not describe Atlas/Mongo as the live backend.

**Refs:** [#112](https://github.com/neomatrix369/rag-params-finder/pull/112) Outcome; [#113](https://github.com/neomatrix369/rag-params-finder/pull/113) Summary.

**Acceptance**
- [ ] `postgres-setup` / `configuration` / `troubleshooting` reviewed — no Atlas-only host wording on Postgres paths
- [ ] Optional: a lightweight note so future edits don’t regress

---

## Owned elsewhere (NOT this slice)

Single routing table (merges the former “collated 6b” and “non-goals 7” tables — do **not** implement here).

| Item | Owner | Ref |
|---|---|---|
| SPLADE / `sparsevec` / 30522-dim storage | Slice **22** | [#112](https://github.com/neomatrix369/rag-params-finder/pull/112), [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) |
| ADR-004 (dual-backend record) + cross-backend quality / rank-overlap (Lucene vs `ts_rank`) matrix | Slice **38** | [#113](https://github.com/neomatrix369/rag-params-finder/pull/113), [#112](https://github.com/neomatrix369/rag-params-finder/pull/112); DECISIONS #93 |
| Env renames/aliases, `--<db>-local\|cloud`, four-value `storage_mode`, config↔server 422, two-command switching | Slice **37** | [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) operator contract |
| IndexBackend / index-seam + Atlas preflight parity for Postgres | Slice **36** | [#110](https://github.com/neomatrix369/rag-params-finder/pull/110) |
| `_id` synthesised on Postgres reads (not stored) | Documented deferral / hygiene (existing slices, not 43) | [#113](https://github.com/neomatrix369/rag-params-finder/pull/113), [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) |
| Protocol craft leftovers / gate closure + parent SLICE-32 After-Checks routing | Slices **32C** / **32B** | [#110](https://github.com/neomatrix369/rag-params-finder/pull/110) |
| Bayesian advanced/extended coverage gates (health-check Gap 8) | Slices **41B** / **41C** | [#109](https://github.com/neomatrix369/rag-params-finder/pull/109); DECISIONS #79 |
| Mutation testing waived to nightly (no local mutmut runner) | Nightly CI | [#112](https://github.com/neomatrix369/rag-params-finder/pull/112); DECISIONS #95 |
| Keeping mongodb/supabase YAML twins in sync forever | Automated — `tests/test_config_examples.py` | — |
| No GitHub Issues linked from these PRs (PROGRESS/TRAIL only) | Process note — optional later GH issue mirror | [#112](https://github.com/neomatrix369/rag-params-finder/pull/112), [#113](https://github.com/neomatrix369/rag-params-finder/pull/113) |

### PR-body source index (provenance)

| PR | State | Title (short) |
|---|---|---|
| [#113](https://github.com/neomatrix369/rag-params-finder/pull/113) | OPEN | Mongo/Postgres boundary hygiene + contract suite |
| [#112](https://github.com/neomatrix369/rag-params-finder/pull/112) | MERGED | Slice 35 sparse/hybrid + Supabase-mode copy |
| [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) | MERGED | Slices 33–34 + `configs/mongodb`/`supabase` split |
| [#110](https://github.com/neomatrix369/rag-params-finder/pull/110) | MERGED | Slice 32 StorageBackend protocol + 32C/32B split |
| [#109](https://github.com/neomatrix369/rag-params-finder/pull/109) | MERGED | Plan health-check Gap 8 → 41B/41C coverage gates |

---

## Spec (GWT)

```
Scenario: Recommended supabase example completes on local Postgres
  Given STORAGE_BACKEND=postgres and a healthy local pgvector
  When the operator runs configs/supabase/example-unified-retrievers.yaml
  Then all 16 runs reach a terminal status without retrieval NotImplemented errors
  And dense, sparse, hybrid, and cross_encoder each produce at least one result row

Scenario: Docs distinguish YAML provider from server backend
  Given an operator reading postgres-setup or configuration
  When they look for how to “use supabase configs”
  Then they are told to set STORAGE_BACKEND=postgres (+ DATABASE_URL)
  And database_provider: supabase is described as labeling metadata, not the switch

Scenario: Docs answer “what is the Supabase equivalent of MONGODB_URI?”
  Given an operator coming from Atlas / MONGODB_URI
  When they look for the Postgres/Supabase connection env var
  Then docs name DATABASE_URL (not SUPABASE_URI) and require STORAGE_BACKEND=postgres
  And any future aliases are listed as backlog owned by Slice 37, not as current behaviour

Scenario: Docs warn about HNSW truncated top-k
  Given an operator following first-prove instructions for Postgres
  When they read the HNSW / iterative_scan note
  Then they understand a short result set can change scores without an error
```

---

## Before-Checks [GATE]

- [ ] Slice 35 ✅ COMPLETE (sparse/hybrid available)
- [ ] `configs/supabase/` nine stems present and passing `tests/test_config_examples.py`

---

## After-Checks [GATE]

- [ ] §1 Live smoke evidence recorded
- [ ] §2–§3 Operator docs updated (backend switch + Mongo↔Postgres env table)
- [ ] §4 First-hosted-prove guidance present; optional smoke YAML present **or** explicitly Won’t with reason
- [ ] §5 HNSW truncated-top-k warning present in operator path
- [ ] §6 Atlas/Mongo wording regression watch confirmed on Postgres paths
- [ ] *Owned elsewhere* table reviewed; each item still points at its owner slice
- [ ] PROGRESS.md status → ✅ COMPLETE; Decision Log row
- [ ] No Must-track regression (36–38 untouched unless docs cross-links only)

---

## Moved out (SLAP spin-out)

The frontend test-coverage / gate-embedding residual that briefly lived here was **SLAP-flagged** (not Supabase-specific, different abstraction level) and spun into its own slice:

→ **[`SLICE-44-FRONTEND-COVERAGE-GATE.md`](SLICE-44-FRONTEND-COVERAGE-GATE.md)** (Should) — frontend coverage tests + coverage table/floor in pre-push & CI.

Nothing else in Slice 43 depends on it.

---

## Gate Status

📋 PLANNED
