# SLICE 43 — Supabase Example-Config Verification & Operator QoL

**MoSCoW:** Could
**Target time:** ~1–2 h
**Status:** ✅ COMPLETE (live smoke + full gates + mandatory review verified 2026-07-26)
**Depends on:** 35 ✅ (soft: 37 for hard config↔server 422)
**Non-blocking / non-urgent:** Does not gate 36–38 cutover. Pick up when operator friction appears or after Slice 37.

**Origin:** 2026-07-26 sanity check of `configs/supabase/` twins derived from `configs/mongodb/` — configs load/expand/parity ✅; residual risks recorded here. Extended same day with operator FAQ (“Supabase equivalent of `MONGODB_URI`?” → env naming asymmetry, §3) and by collating deferred/open items from PR bodies [#109](https://github.com/neomatrix369/rag-params-finder/pull/109)–[#113](https://github.com/neomatrix369/rag-params-finder/pull/113) (bodies only; provenance in *PR-body source index*).

**Planning quality lens (2026-07-26):** 9/10 pass. Fail = check 3 (SLAP) — the frontend-coverage item was a different abstraction level and has been spun out to [`SLICE-44-FRONTEND-COVERAGE-GATE.md`](SLICE-44-FRONTEND-COVERAGE-GATE.md). Duplications removed (old §6a ↔ §§1–5; old §6b ↔ §7). **MoSCoW note:** the slice priority is *Could* relative to the 36–38 migration track, but §1 (recorded live supabase smoke) is this slice’s definition-of-done, not optional.

> **SUPERSEDED (2026-07-26, Slice 37 / DECISIONS #107):** claims below that there is
> **no** `SUPABASE_URI` are historical. Current truth: `DATABASE_URL` remains
> canonical; `SUPABASE_URI` is an optional alias when `DATABASE_URL` is unset.
> Live hosted Path B smoke is recorded in [`gate-evidence/slice-37.json`](../gate-evidence/slice-37.json).

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
- [x] Run and record: `./start-services.sh --postgres-local` then
  `rag-params-finder run --config configs/supabase/example-unified-retrievers.yaml`
  *(historical note: checklist originally said `--postgres`; that short flag was removed in Slice 37)*
  (16 runs — dense · sparse · hybrid · cross_encoder, local embeddings)
- [x] Gate evidence note (command, date, experiment id / outcome) under `docs/plan/gate-evidence/` or PROGRESS Decision Log — **VERIFIED** 2026-07-26: [`slice-43.json`](../gate-evidence/slice-43.json), experiment `dd107437-be69-4d62-a549-003b743ed841`, 16/16 complete
- [ ] Optional stretch: same config (or smoke twin) against hosted Supabase `DATABASE_URL` — **superseded by residuals §Parked from Slice 38** (full hosted quality matrix, not just smoke)

### 2. Backend switch is env, not YAML
`database_provider: supabase` is **metadata** (db-stats / labels). Runtime path is `STORAGE_BACKEND=postgres` + `DATABASE_URL`. Operators can submit a supabase YAML while the server is still on mongodb.

**Refs:** Explicit deferred item in [#113](https://github.com/neomatrix369/rag-params-finder/pull/113) Documentation (“`database_provider` metadata”); config split in [#111](https://github.com/neomatrix369/rag-params-finder/pull/111); hard 422 owned by Slice 37.

**Acceptance**
- [x] `postgres-setup.md` + `configuration.md` state this in one clear sentence each — **IMPLEMENTED** 2026-07-26 (operator docs rewrite)
- [x] Hard reject / HTTP 422 on config↔server mismatch remains **Slice 37** — this slice only documents today’s behaviour and links to 37

### 3. Connection-env naming is asymmetric (Mongo vs Postgres/Supabase)

Operators naturally ask “what’s the Supabase equivalent of `MONGODB_URI`?” Today the answer is **not** a parallel name:

| Concern | MongoDB (today) | Postgres / Supabase (today) |
|---|---|---|
| Connection string | `MONGODB_URI` | `DATABASE_URL` (no `SUPABASE_URI` / `POSTGRES_URI`) |
| Backend select | Often implicit (`STORAGE_BACKEND` defaults to `mongodb` permanently — #130; legacy alias `mongo`) | Explicit second knob: `STORAGE_BACKEND=postgres` |
| Config folder / YAML label | `configs/mongodb/` · `database_provider: mongodb` | `configs/supabase/` · `database_provider: supabase` |
| Runtime backend token | `mongodb` (settings) | `postgres` (settings) — **not** `supabase` |

Definition and use diverge on three axes: **URI name**, **whether a backend flag is required**, and **folder/YAML label vs `STORAGE_BACKEND` value**. Correct, but easy to mis-teach and mis-configure.

**Refs:** Operator FAQ 2026-07-26; [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) commit narrative (“Selecting the postgres backend also drops the `MONGODB_URI` requirement”); `.env.example` comments. Canonical `STORAGE_BACKEND=mongodb` landed 2026-07-26 (legacy `mongo` alias).

**Acceptance (document now; further rename later)**
- [x] `postgres-setup.md` (and `.env.example` comment block) include a one-row “Mongo ↔ Postgres env” table matching the above — **IMPLEMENTED** 2026-07-26
- [x] Explicit note: there is no `SUPABASE_URI`; hosted and local both use `DATABASE_URL` — **IMPLEMENTED** 2026-07-26
- [x] Cross-link Slice **37** for future rename / alias work beyond the `mongo`→`mongodb` token — **IMPLEMENTED** 2026-07-26 (`postgres-setup.md` footer / Slice 37 pointer). Remaining 37 work: URI aliases, config↔server 422, start-services mode grid.
### 4. Hosted free-tier / large-grid risk
Full grids (e.g. `example-local.yaml` = 120 runs) may be slow or hit Supabase free-project limits. Not a correctness bug.

**Refs:** [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) verified mongodb vs supabase local parity at **120 runs** — fine for local CI/dev but a poor first hosted prove.

**Acceptance**
- [x] Docs recommend first hosted prove: `example-unified-retrievers.yaml` or `*-bayesian.yaml` — **IMPLEMENTED** in `postgres-setup.md` / QUICKSTART Path D
- [x] Optional: add `configs/supabase/example-local-smoke.yaml` — **Won’t for 43** (unified-retrievers is the first-prove config; documented as such)

### 5. HNSW post-filter recall (operator-invisible shortfall)
With filters (`experiment_id` / `embedding_model` / `run_id`), HNSW can return fewer than `LIMIT` rows unless `hnsw.iterative_scan = strict_order` is on. Failure mode is silent: scores change, no error.

**Refs:** [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) (`feat(slice-34)` + HNSW recall finding); already partially documented in `postgres-setup.md`.

**Acceptance**
- [x] First-prove / troubleshooting section still warns about truncated top-k if iterative scan is off — **IMPLEMENTED** in `postgres-setup.md`
- [x] Link to architecture explanation for HNSW iterative scan — **IMPLEMENTED** (design rationale moved to `contributor-guide/architecture.md`)

### 6. Docs must not re-introduce Atlas/Mongo wording on Postgres paths
Regression watch after the Slice 35 / #113 copy scrub: operator docs and UI copy on Postgres/Supabase paths must not describe Atlas/Mongo as the live backend.

**Refs:** [#112](https://github.com/neomatrix369/rag-params-finder/pull/112) Outcome; [#113](https://github.com/neomatrix369/rag-params-finder/pull/113) Summary.

**Acceptance**
- [x] `postgres-setup` / `configuration` / `troubleshooting` reviewed — no Atlas-only host wording on Postgres paths — **AUDITED** 2026-07-26 (docs parity + code/UI storageLabels)
- [x] Optional: lightweight regression note — **IMPLEMENTED** via `postgres-setup.md` “Supabase vs Postgres” table + Slice 43 §6 as the watchlist

---

## Owned elsewhere (NOT this slice)

Single routing table (merges the former “collated 6b” and “non-goals 7” tables — do **not** implement here).

| Item | Owner | Ref |
|---|---|---|
| SPLADE / `sparsevec` / 30522-dim storage | Slice **22** | [#112](https://github.com/neomatrix369/rag-params-finder/pull/112), [#111](https://github.com/neomatrix369/rag-params-finder/pull/111) |
| ADR-004 + **local** dual-backend quality / rank-overlap matrix (Lucene vs `ts_rank`) | Slice **38** | [#113](https://github.com/neomatrix369/rag-params-finder/pull/113), [#112](https://github.com/neomatrix369/rag-params-finder/pull/112); DECISIONS #93 / #125 |
| Hosted `postgres-cloud` production-claim quality/latency matrix + PRD bookkeeping + sync-docs parked from 38 | **This slice — residuals below** | DECISIONS #125 / #126; default flip Won't (#130) |
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

- [x] Slice 35 ✅ COMPLETE (sparse/hybrid available)
- [x] `configs/supabase/` nine stems present and passing `tests/test_config_examples.py` — **VERIFIED** 2026-07-26: 25 passed

---

## After-Checks [GATE]

- [x] §1 Live smoke evidence recorded
- [x] §2–§3 Operator docs updated (backend switch + Mongo↔Postgres env table)
- [x] §4 First-hosted-prove guidance present; optional smoke YAML present **or** explicitly Won’t with reason
- [x] §5 HNSW truncated-top-k warning present in operator path
- [x] §6 Atlas/Mongo wording regression watch confirmed on Postgres paths
- [x] *Owned elsewhere* table reviewed; each item still points at its owner slice
- [x] PROGRESS.md status → ✅ COMPLETE; Decision Log row
- [x] No Must-track regression (36–38 untouched unless docs cross-links only)

---

## Moved out (SLAP spin-out)

The frontend test-coverage / gate-embedding residual that briefly lived here was **SLAP-flagged** (not Supabase-specific, different abstraction level) and spun into its own slice:

→ **[`SLICE-44-FRONTEND-COVERAGE-GATE.md`](SLICE-44-FRONTEND-COVERAGE-GATE.md)** (Should) — frontend coverage tests + coverage table/floor in pre-push & CI.

Nothing else in Slice 43 depends on it.

---

## Gate Status

✅ PASSED — runtime and documentation gates verified 2026-07-26; mandatory nw-documentarist review APPROVED

> **Residuals open (do not reopen COMPLETE):** §Parked from Slice 38 below. Pick up when claiming production `postgres-cloud` cutover or cleaning PRD bookkeeping — not required to keep Slice 43 ✅.

---

## Parked from Slice 38 (2026-07-26 — DECISIONS #125 / #126)

Anything that was **not a clear Yes** on the Slice 38 realism review lives here. Slice 38 COMPLETE gates only on local comparison + ADR + independent dual-backend model (#129) + no default flip (#130) + `slice-38.json` + tracker/CHANGELOG. Slice 43 status stays ✅; these are post-COMPLETE residuals.

| Item | Why not 100% Yes on 38 | Acceptance (when picked up) |
|---|---|---|
| Hosted `postgres-cloud` quality + latency matrix vs Mongo | Production claim ≠ local comparison; free-tier pause risk | Amend comparison artifact with hosted mode scope; QUERYING ≤2×; numeric top-3; claim only if PASS/CONDITIONAL |
| Slice 37 hosted Path B as Before for production claim | Nuanced — required for production claim only | Use `slice-37.json` hosted smoke as Before for this residual |
| Hosted-unreachable / withhold-production-claim GWT | Belongs with hosted matrix | Document partial hosted scope; no PASS claim |
| ~~Post-flip fresh-clone / Mongo rollback GWTs~~ | **Dropped — DECISIONS #130 Won't** (no code-default flip) | N/A |
| ADR **Pro-tier / non-pausing** note as COMPLETE mandate | Production-claim prose, not local comparison | ADR-004 Consequences (or amend) state Pro/non-pausing for warm demos |
| 32/32B/32C/33 tracker one-liner in comparison/ADR | Half-wrong Before; DECISIONS already notes debt | Optional one-liner in artifact/ADR; formal PRD tick separate below |
| PRD §9 boxes for slices 33–37 + evidence pointers | Scope creep / historical bookkeeping | Edit PRD §9 so only genuine open work remains |
| Full PRD §Documentation matrix audit (README default, CLAUDE Key Files, cross-links, …) | Overscoped vs CHANGELOG+ADR | Tick or defer each matrix row with evidence |
| `/sync-docs` operator + contributor footprint for #130 (permanent `mongodb` default) | **APPLIED** 2026-07-26 | README/AGENTS/CLAUDE/getting-started/configuration/postgres-setup/troubleshooting/architecture/`.env.example`/`docker-compose.yml` + plan surfaces |
| Branch coverage **100%** on shell helpers | Unrealistic here | Targeted shell tests **or** permanent exclusions documented |
| Shell-exclusion documentation as After-Check | Softened 100% gate still process debt | Same as row above |
| Separate “specification coverage” After-Check for every GWT | Probes already required inside comparison artifact | Ensure residual GWTs have probes when those residuals run |
| Graphiti dual-backend decision episode as COMPLETE gate | Process hygiene | Optional episode `rag-params-finder-flow-planner` |
| PRD rollback spelling with baked verification date | Brittle checklist date | “Canonical `mongodb` verified” without fixed date, or N/A |

**Won’t re-open Slice 43 COMPLETE** when these land — treat as residual follow-ups / optional amend to gate-evidence.
