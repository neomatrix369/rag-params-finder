# Trail
> ~3 min read (this doc) · [GAP_ANALYSIS](GAP_ANALYSIS.md) ~2 min · [DECISIONS](DECISIONS.md) ~2 min · [HANDOFF](HANDOFF.md) ~1 min · [PROGRESS](../plan/slices/PROGRESS.md) ~2 min · [PRD Supabase](PRD-supabase-pgvector-migration.md) ~3 min

## Original Material

- **PCTO Spec** (`docs/PCTO-rag-params-finder-2026-06-27.md`): Add SIE as primary open-source inference backend (encode + score + extract), caller-supplied corpus (`corpus: list[str]` field on `SweepRequest`), Aim for experiment tracking, and two new API endpoints (`POST /api/v1/sweep`, `GET /api/v1/best-config`)
- **Supabase migration PRD** (`docs/plan/PRD-supabase-pgvector-migration.md`, 2026-07-09): Dual-backend storage Protocol; Postgres/pgvector + Supabase as first-class engine alongside Mongo (code default stays `mongodb` — #130 Won't flip)
- **DoubleWord embedder brief** (`docs/plan/BRIEF-doubleword-embedder.md`, 2026-09-24): owner plan titled "SLICE-32" → renumbered **48A–48D** (32 taken by the Storage Protocol track); **batch-first** per the docextract reference project: mixed-provider axis + batch provider + detached watcher → cost + hardening → MRL/instruction axes → realtime (Could) (DECISIONS #188–#207)
- **Redis evaluation brief** (`docs/plan/BRIEF-redis-evaluation.md`, 2026-09-24): owner prompt v2 (adapter review + Redis as vector store / supporting infra) → **52** docs-only spike (reuses the 49/51 review) → **53** Redis vector adapter + full journey (+ **54** Could cache port); ADR-007, QUICKSTART Path F; queue/rate-limit/LangCache/CI → Won't (DECISIONS #220–#229)
- **Codebase** (v0.11.0, 20+ slices complete): Mature Voyage AI + local sentence-transformers RAG sweep pipeline, MongoDB Atlas, FastAPI, React dashboard, Docker, full CI toolchain
- **Constraints**: Hackathon deadline — Slice 21 targets Days 1–5; Voyage AI stays as numeric baseline (not replaced); PCTO changes remain additive; **Slice 39 is a ≤2 h demo interrupt, then storage migration resumes ahead of Slice 22** (2026-07-18)

Routing: Brownfield + Growing Requirement (Flow D) · Chosen: 2026-07-02 · Source: health-check-inferred · Reconfirmed: 2026-07-09 (Supabase PRD Add path)

Model split — Planning: claude-opus-4-8 · Execution: claude-sonnet-5

<!-- harness-scout output -->
```yaml
# planning (detect_confirm) — profile: high/low/"planning session"/interactive (Brownfield)
# Cursor detection is self-report only — read model and mode from the Agent tab header.
extensions_applied: [ambiguity]
recommendation:
  codex:
    model: "Sol"
    effort: "High–Extra High"
    fast_mode: false
    sandbox_mode: "workspace-write"
    approval_policy: "on-request"
  claude_code:
    model: "claude-opus-4-8"
    effort: "High"
    permission_mode: "plan"
  cursor:
    mode: "Agent"
    model: "claude-opus-4-8"
    max_mode: false
    auto_run: false
isolation:
  worktree_required: false
duration:
  profile: "interactive"
  checkpoint_cadence: "N/A"
cost_flag: "elevated"
detect_commands:
  cursor: "self-report — no CLI surface; read from Agent tab header"
confirm_checklist:
  - "Phase 1: Plan/Ask mode, deliberate tier, High–Extra High effort, autonomy off — resolve judgment call first"
  - "Phase 2: switch to workhorse tier, Medium effort, autonomy scoped to expected files"
  - "Do not run the whole slice at Max/Ultra — reserve peak effort for the specific hard sub-problem"
  - "Cursor: self-report detection — confirm Agent tab matches recommendation or document deviation"
freshness:
  stale: false
  stalest_field: "none"
  last_checked: "2026-09-10"
---
# execution (recommend) — profile: low/high/"≤4h (~6 Pomos)"/interactive
# Open Must/Should queue: 32C, 32B (gate-debt only — 32/33 code on main 2eb2990), 28, 31
extensions_applied: [blast_radius_high]
recommendation:
  codex:
    model: "Terra"
    effort: "Medium"
    fast_mode: false
    sandbox_mode: "read-only"
    approval_policy: "untrusted"
  claude_code:
    model: "claude-sonnet-5"
    effort: "Medium"
    permission_mode: "plan"
  cursor:
    mode: "Composer"
    model: "claude-sonnet-5"
    max_mode: false
    auto_run: false
isolation:
  worktree_required: false
duration:
  profile: "interactive"
  checkpoint_cadence: "N/A"
cost_flag: "none"
confirm_checklist:
  - "Human review checkpoint before any commit — required, not optional"
  - "No workspace-write / bypassPermissions / Auto-run for this profile"
  - "git diff --stat main must be empty before first edit (when starting a new slice branch)"
freshness:
  stale: false
  stalest_field: "none"
  last_checked: "2026-09-10"
```

**Slice 22 skill proposal (2026-07-29):** `/tdd` · `/verify-slice` · `/clean-commit` · `/project-hygiene` · `/divergence-check` · `/nw-execute` (primary execution path). Cursor rules: `software-craft.mdc`, `test-writing-*.mdc`, `security.md`, `git-github-best-practices.mdc`. No `/frontend-advisor` (no UI). MCP Won't (#8). Graphiti write on gate PASS → `rag-params-finder-flow-planner`.

## Next Wave Checkpoint (post Slice 22)

Slice **22** ✅ COMPLETE on `slice/22-sie-scooter` (`9805de8` + `383541b`; `/verify-slice` **VERIFIED**). Informational — not a gate:

| Option | Action |
|--------|--------|
| **A (recommended)** | Confirm create-pr draft → merge Slice 22; optional live SIE smoke (`POST /api/v1/sweep` → `GET /api/v1/best-config?task=`) |
| **B** | Close formal **32B** gate debt (parallel Protocol tracker hygiene) |
| **C** | Slice **28** results export (external) or forward Could/Should per PROGRESS |

Logged: DECISIONS #166–#170.

## Flow

**Brownfield + Growing Requirement** (Flow D) — mature codebase; PCTO + storage migration compose on existing pipeline via Protocol/adapters (Decision #10 upgraded only where dual-backend contract requires it).

## Slices

Each PCTO / migration slice lives in its own file below. Specs live under `docs/plan/slices/0N-<theme>/` (theme index: [`slices/README.md`](../plan/slices/README.md)); status SSOT remains flat [`PROGRESS.md`](../plan/slices/PROGRESS.md).

| # | File | Name | MoSCoW | Status | Depends on | Issue | Read time | Last Updated |
|---|------|------|--------|--------|------------|-------|-----------|--------------|
| 21 | [../plan/slices/04-sie/SLICE-21-SIE-SKATEBOARD.md](../plan/slices/04-sie/SLICE-21-SIE-SKATEBOARD.md) | SIE Skateboard — embeddings + Aim + `/api/v1/sweep` | Must | ✅ PASSED | none | — | ~4 min | 2026-06-29 |
| 25 | [../plan/slices/03-platform/SLICE-25-ATLAS-LOCAL.md](../plan/slices/03-platform/SLICE-25-ATLAS-LOCAL.md) | Atlas Local Dev Mode — `mongodb-atlas-local` as opt-in backend | Should | ✅ PASSED | 21 | — | ~2 min | 2026-06-29 |
| 25B | [../plan/slices/03-platform/SLICE-25B-ATLAS-SWITCHING.md](../plan/slices/03-platform/SLICE-25B-ATLAS-SWITCHING.md) | Atlas Backend Switching — single-flag cloud ↔ local switching | Should | ✅ PASSED | 25 | — | ~2 min | 2026-06-29 |
| 29 | [../plan/slices/01-core-pipeline/SLICE-29-PADDING-PROPAGATION.md](../plan/slices/01-core-pipeline/SLICE-29-PADDING-PROPAGATION.md) | Padding cross-cutting propagation — config key, API, types, UI | Must | ✅ PASSED | none | — | ~2 min | 2026-07-05 |
| 32 | [../plan/slices/05-storage/SLICE-32-STORAGE-BACKEND-PROTOCOL.md](../plan/slices/05-storage/SLICE-32-STORAGE-BACKEND-PROTOCOL.md) | Storage Protocol + Mongo adapter (Storage + Retriever ports) | Must | ✅ COMPLETE (code) · gate-debt→32C/32B | none | [#110](https://github.com/neomatrix369/rag-params-finder/pull/110) | ~2 min | 2026-09-23 |
| 32C | [../plan/slices/05-storage/SLICE-32C-STORAGE-PROTOCOL-REVIEW-REMEDIATION.md](../plan/slices/05-storage/SLICE-32C-STORAGE-PROTOCOL-REVIEW-REMEDIATION.md) | Storage Protocol review remediation — craft split, port schemas, index deferral, checklist hygiene | Must | 📋 PLANNED | 32 | [#110](https://github.com/neomatrix369/rag-params-finder/pull/110) | ~2 min | 2026-07-25 |
| 32B | [../plan/slices/05-storage/SLICE-32B-STORAGE-PROTOCOL-GATE-CLOSURE.md](../plan/slices/05-storage/SLICE-32B-STORAGE-PROTOCOL-GATE-CLOSURE.md) | Storage Protocol gate closure — coverage, mutation/waiver, full gates, nw-review, tracker COMPLETE | Must | 📋 PLANNED | 32C | [#110](https://github.com/neomatrix369/rag-params-finder/pull/110) | ~2 min | 2026-07-25 |
| 33 | [../plan/slices/05-storage/SLICE-33-POSTGRES-SCHEMA-CRUD.md](../plan/slices/05-storage/SLICE-33-POSTGRES-SCHEMA-CRUD.md) | Postgres schema + pool + CRUD (+ local pgvector Path A) | Must | ✅ COMPLETE (code) · gate-debt→32C/32B | 32B | — | ~2 min | 2026-09-23 |
| 34 | [../plan/slices/05-storage/SLICE-34-POSTGRES-DENSE-RETRIEVAL.md](../plan/slices/05-storage/SLICE-34-POSTGRES-DENSE-RETRIEVAL.md) | Postgres dense retrieval (pgvector HNSW) | Must | ✅ COMPLETE | 33 | — | ~2 min | 2026-07-25 |
| 35 | [../plan/slices/05-storage/SLICE-35-POSTGRES-SPARSE-HYBRID.md](../plan/slices/05-storage/SLICE-35-POSTGRES-SPARSE-HYBRID.md) | Postgres sparse + hybrid RRF (+ Mongo equivalence gate) | Must | ✅ COMPLETE | 34 | — | ~2 min | 2026-07-26 |
| 36 | [../plan/slices/05-storage/SLICE-36-POSTGRES-PREFLIGHT-STATS.md](../plan/slices/05-storage/SLICE-36-POSTGRES-PREFLIGHT-STATS.md) | Preflight + db-stats + four-value storage_mode | Must | ✅ COMPLETE | 35 | — | ~2 min | 2026-07-26 |
| 37 | [../plan/slices/05-storage/SLICE-37-POSTGRES-LOCAL-CLOUD-PARITY.md](../plan/slices/05-storage/SLICE-37-POSTGRES-LOCAL-CLOUD-PARITY.md) | `--<db>-local/cloud` + config gate + product-wording vocabulary | Must | ✅ COMPLETE | 36 | — | ~2 min | 2026-07-26 |
| 38 | [../plan/slices/05-storage/SLICE-38-CUTOVER-ADR-004.md](../plan/slices/05-storage/SLICE-38-CUTOVER-ADR-004.md) | Quality comparison + ADR-004 + default cutover | Must | ✅ COMPLETE | 37 | [#118](https://github.com/neomatrix369/rag-params-finder/pull/118) | ~2 min | 2026-07-26 |
| 43 | [../plan/slices/05-storage/SLICE-43-SUPABASE-CONFIG-VERIFICATION.md](../plan/slices/05-storage/SLICE-43-SUPABASE-CONFIG-VERIFICATION.md) | Supabase example-config verification + operator QoL | Could | ✅ COMPLETE | 35 (soft: 37) | [#115](https://github.com/neomatrix369/rag-params-finder/pull/115) | ~2 min | 2026-07-26 |
| 44 | [../plan/slices/07-quality-craft/SLICE-44-FRONTEND-COVERAGE-GATE.md](../plan/slices/07-quality-craft/SLICE-44-FRONTEND-COVERAGE-GATE.md) | Frontend coverage + gate summary + structure taxonomy Should (theme map; moves → 45); review remediations #137; Residual §4 Nightly Stryker (#163) **IMPLEMENTED** | Should | ✅ COMPLETE (+ residual IMPL) | none (Vitest harness) | [#131](https://github.com/neomatrix369/rag-params-finder/pull/131) | ~3 min | 2026-07-28 |
| 45 | [../plan/slices/07-quality-craft/SLICE-45-MODULE-THEME-SEPARATION.md](../plan/slices/07-quality-craft/SLICE-45-MODULE-THEME-SEPARATION.md) | Module theme separation — execute Behavior/Feature/Function folder moves; architect APPROVED post-#137 | Could | ✅ COMPLETE | 44 (taxonomy artifacts) | [#130](https://github.com/neomatrix369/rag-params-finder/pull/130) | ~2 min | 2026-07-28 |
| 28 | [../plan/slices/02-dashboard/SLICE-28-RESULTS-EXPORT.md](../plan/slices/02-dashboard/SLICE-28-RESULTS-EXPORT.md) | Results export — CSV/JSONL download (issue #49; @cschanhniem) | Must | 📋 PLANNED | none | [#49](https://github.com/neomatrix369/rag-params-finder/issues/49) | ~3 min | 2026-07-06 |
| 22 | [../plan/slices/04-sie/SLICE-22-SIE-SCOOTER.md](../plan/slices/04-sie/SLICE-22-SIE-SCOOTER.md) | SIE Scooter — reranking + SPLADE sparse path + `/api/v1/best-config` | Must | ✅ COMPLETE | 21, 32 (Protocol on main), 38 ✅ | — | ~3 min | 2026-07-29 |
| 26 | [../plan/slices/05-storage/SLICE-26-LOCAL-MONGODB-DOCS.md](../plan/slices/05-storage/SLICE-26-LOCAL-MONGODB-DOCS.md) | Local MongoDB: smooth path docs + script feedback | Should | 📦 DEFERRED | 25B | — | ~1.5 min | 2026-07-09 |
| 27 | [../plan/slices/05-storage/SLICE-27-MONGODB-MODE-INDICATOR.md](../plan/slices/05-storage/SLICE-27-MONGODB-MODE-INDICATOR.md) | MongoDB mode indicator (cloud vs local) | Should | 📦 DEFERRED | 25B | — | ~2 min | 2026-07-09 |
| 19 | [../plan/slices/05-storage/SLICE-19-STORAGE-QUOTA-GUARD.md](../plan/slices/05-storage/SLICE-19-STORAGE-QUOTA-GUARD.md) | Storage quota guard (cloud production) | Should | 📦 DEFERRED | none | — | — | 2026-07-09 |
| 16 | [../plan/slices/01-core-pipeline/SLICE-16-PARALLEL-SWEEP-RUNS.md](../plan/slices/01-core-pipeline/SLICE-16-PARALLEL-SWEEP-RUNS.md) | Parallel sweep | Should | ✅ PASSED | none | — | — | — |
| 11 | [../plan/slices/02-dashboard/SLICE-11-SEARCH-EXPLORER.md](../plan/slices/02-dashboard/SLICE-11-SEARCH-EXPLORER.md) | Search Explorer enhancements — visualization + query filtering | Could | 📋 PLANNED | none (soft: 30) | — | ~3 min | 2026-07-09 |
| 23 | [../plan/slices/04-sie/SLICE-23-SIE-BICYCLE.md](../plan/slices/04-sie/SLICE-23-SIE-BICYCLE.md) | SIE Bicycle — Ollama + Tier 2–3 methods + Evidently AI | Could | 📋 PLANNED | 22 | — | ~3 min | 2026-07-09 |
| 10 | [../plan/slices/01-core-pipeline/SLICE-10-RUN-RECOVERY.md](../plan/slices/01-core-pipeline/SLICE-10-RUN-RECOVERY.md) | Run recovery | Could | 🔨 PARTIAL | none | — | — | 2026-07-09 |
| 30 | [../plan/slices/02-dashboard/SLICE-30-SEARCH-EXPLORER-UX.md](../plan/slices/02-dashboard/SLICE-30-SEARCH-EXPLORER-UX.md) | Search Explorer UX fixes — tab latency, zero-score, BM25 labels, VDB card | Could | 📋 PLANNED | none | — | ~2 min | 2026-07-07 |
| 31 | [../plan/slices/02-dashboard/SLICE-31-EXPERIMENT-LIST-FILTER.md](../plan/slices/02-dashboard/SLICE-31-EXPERIMENT-LIST-FILTER.md) | Experiment list filter — status dropdown + name/ID search | Should | 📋 PLANNED | none | — | ~2 min | 2026-07-07 |
| 39 | [../plan/slices/02-dashboard/SLICE-39-DEMO-READY-DASHBOARD-POLISH.md](../plan/slices/02-dashboard/SLICE-39-DEMO-READY-DASHBOARD-POLISH.md) | Demo-ready dashboard polish — list-to-detail visual journey | Should | ✅ COMPLETE | none | — | ~3 min | 2026-07-18 |
| 40 | [../plan/slices/07-quality-craft/SLICE-40-DOCS-PLAN-SLICES-SSOT.md](../plan/slices/07-quality-craft/SLICE-40-DOCS-PLAN-SLICES-SSOT.md) | Docs SSOT + numbered theme folders (`01`–`07`, #162) | Should | ✅ COMPLETE | none | — | ~2–3 h | 2026-07-28 |
| 41A | [../plan/slices/06-bayesian/SLICE-41A-BAYESIAN-SEARCH-SIMPLE-FUNCTIONAL.md](../plan/slices/06-bayesian/SLICE-41A-BAYESIAN-SEARCH-SIMPLE-FUNCTIONAL.md) | Bayesian Search: Simple Functional | Could | ✅ COMPLETE | 16 | — | ~2.5 h | 2026-07-23 |
| 41B | [../plan/slices/06-bayesian/SLICE-41B-BAYESIAN-SEARCH-ADVANCED.md](../plan/slices/06-bayesian/SLICE-41B-BAYESIAN-SEARCH-ADVANCED.md) | Bayesian Search: Advanced (parallelism, categorical axes, persistence, random search) | Could | 📦 PARKED | 41A + owner data | — | ~4–6 h | 2026-07-22 |
| 42 | [../plan/slices/03-platform/SLICE-42-DOCKER-BUILD-OPTIMISATION.md](../plan/slices/03-platform/SLICE-42-DOCKER-BUILD-OPTIMISATION.md) | Docker Build Optimisation — multi-stage, BuildKit cache mounts, CI job | Should | ✅ COMPLETE | none | — | ~2.5 h | 2026-07-25 |
| 46 | [../plan/slices/07-quality-craft/SLICE-46-BACKEND-COVERAGE-85.md](../plan/slices/07-quality-craft/SLICE-46-BACKEND-COVERAGE-85.md) | Backend coverage 70.1% → 80–85% (FastAPI TestClient, Typer CliRunner, orchestrator branching) | Should | 📋 PLANNED | none | — | ~3–4 h | 2026-09-23 |
| 48A | [../plan/slices/08-embedding-providers/SLICE-48A-DOUBLEWORD-BATCH-PROVIDER.md](../plan/slices/08-embedding-providers/SLICE-48A-DOUBLEWORD-BATCH-PROVIDER.md) | Mixed-provider axis + DoubleWord **batch** provider (openai SDK, docextract pattern) + detached async watcher + cache + boot resume | Must | 📋 PLANNED | none | — | ~5 min | 2026-09-24 |
| 48B | [../plan/slices/08-embedding-providers/SLICE-48B-DOUBLEWORD-COST-HARDENING.md](../plan/slices/08-embedding-providers/SLICE-48B-DOUBLEWORD-COST-HARDENING.md) | DoubleWord cost capture + double-billing guard + shared batches + progress UI + ctx diagnostics | Must | 📋 PLANNED | 48A | — | ~3 min | 2026-09-24 |
| 48C | [../plan/slices/08-embedding-providers/SLICE-48C-DOUBLEWORD-MRL-INSTRUCTION-AXES.md](../plan/slices/08-embedding-providers/SLICE-48C-DOUBLEWORD-MRL-INSTRUCTION-AXES.md) | MRL `dimensions` + `query_instruction` sweep axes | Should | 📋 PLANNED | 48B | — | ~3 min | 2026-09-24 |
| 48D | [../plan/slices/08-embedding-providers/SLICE-48D-DOUBLEWORD-REALTIME-MODE.md](../plan/slices/08-embedding-providers/SLICE-48D-DOUBLEWORD-REALTIME-MODE.md) | DoubleWord realtime mode (optional; promoted to Must only if V3 fails) | Could | 📋 PLANNED | 48A | — | ~1 min | 2026-09-24 |
| 49 | [../plan/slices/05-storage/SLICE-49-VECTOR-STORE-PORT-SPLIT-REGISTRY.md](../plan/slices/05-storage/SLICE-49-VECTOR-STORE-PORT-SPLIT-REGISTRY.md) | Vector-store `VectorStoreAdapter` protocol + registry + `VECTOR_STORE_BACKEND` (no ES code; relocates 4-place store branching) | Must | 📋 PLANNED | 32, 38 | — | ~3 min | 2026-09-24 |
| 50 | [../plan/slices/05-storage/SLICE-50-ELASTICSEARCH-ADAPTER-CORE.md](../plan/slices/05-storage/SLICE-50-ELASTICSEARCH-ADAPTER-CORE.md) | Elasticsearch adapter core — dense/sparse/hybrid parity, unquantized HNSW, refresh, client-side RRF; `[elasticsearch]` extra | Must | 📋 PLANNED | 49 | — | ~3 min | 2026-09-24 |
| 51 | [../plan/slices/05-storage/SLICE-51-ELASTICSEARCH-OPERABILITY-CI-DOCS-ADR.md](../plan/slices/05-storage/SLICE-51-ELASTICSEARCH-OPERABILITY-CI-DOCS-ADR.md) | ES closeout — compose profile + `--elasticsearch-local` + `GET /api/stores` + configs + drift fixes **＋** nightly CI + 15-stage docs journey + registry-driven docs-parity gate + ADR-006 (merged 51+52, #218; optional 51a/51b PR split) | Must | 📋 PLANNED | 50 | — | ~4 min | 2026-09-24 |
| 52 | [../plan/slices/05-storage/SLICE-52-REDIS-EVALUATION-SPIKE.md](../plan/slices/05-storage/SLICE-52-REDIS-EVALUATION-SPIKE.md) | Redis evaluation spike — candidates + free gate + adoption + throwaway PoC (Redis 8 vs Valkey) + Branch B verdicts + scoring → report + HTML guide + ADR-007 (Proposed) + GO/NO-GO for 53/54. Docs-only; **reuses** the 49/51 adapter review + journey (delta only) | Must *(proposed)* | 📋 PLANNED | none (soft: 49/51 specs) | — | ~3 min | 2026-09-24 |
| 53 | [../plan/slices/05-storage/SLICE-53-REDIS-VECTOR-STORE-ADAPTER.md](../plan/slices/05-storage/SLICE-53-REDIS-VECTOR-STORE-ADAPTER.md) | Redis vector-only store — adapter core **＋** full 15-stage journey (compose `redis-local` + AOF, `--redis-local`, `configs/redis/*`, nightly, `redis-setup.md`, QUICKSTART Path F, ADR-007 Accepted); zero-changes diff guard (fused core+journey, #224; optional 53a/53b PR split) | Should *(proposed; Must on GO)* | 📋 PLANNED | 51, 52 | — | ~4 min | 2026-09-24 |
| 54 | [../plan/slices/08-embedding-providers/SLICE-54-CACHE-BACKEND-PORT-REDIS.md](../plan/slices/08-embedding-providers/SLICE-54-CACHE-BACKEND-PORT-REDIS.md) | `CacheBackend` port over 48A's `embedding_cache.py` (SQLite default) + Redis cache adapter; only if 52 finds a concrete need | Could | 📋 PLANNED | 48A, 52 (soft: 53) | — | ~2 min | 2026-09-24 |
| 47 | [../plan/slices/07-quality-craft/SLICE-47-COMPLEXITY-TIGHTEN.md](../plan/slices/07-quality-craft/SLICE-47-COMPLEXITY-TIGHTEN.md) | Xenon complexity E/C/C → B/A/A (orchestrator CC=40, experiments_lifecycle CC=32) | Should | 📋 PLANNED | none | — | ~2–3 h | 2026-09-23 |

**Execution order**: 21 → 25 → 25B → 29 (done) → **39** *(≤2 h demo interrupt)* → **⭐ 32 → 32C → 32B → 33 → 34 → 35 → 36 → 37 → 38** → **22** → 28*(external)* → 31 → 30 → 16 → 11 → 23 → 10. Slices 40, 41A, and 42 are independent housekeeping/optimisation slices and can run at any time without blocking the Supabase migration sequence.
*Slice 28 is an external contributor PR (@cschanhniem / #49); core team resumes at Slice 31 after 28 merges or stays deferred — it does not block the storage critical path.*
*Deferred Mongo QoL: 26, 19 — re-scope after cutover. Slice 27 scope absorbed into 36 as four-value `storage_mode` (`mongodb|postgres` × `local|cloud`).*

> **Reconcile 2026-09-23 (audit_reconcile):** Slices **32** (Storage Protocol) and **33** (Postgres schema+CRUD) code is fully on `main` since 2026-07-28 (`2eb2990`) — every downstream slice (34–38, 22) that depends on them is already ✅ COMPLETE. Their status is now **✅ COMPLETE (code)**; the remaining **formal gate closure** (coverage/mutation/nw-review sign-off + full gate-evidence schema) stays the open debt owned by slices **32C → 32B** per DECISIONS #179. Placeholder `gate-evidence/slice-32.json` / `slice-33.json` are `PENDING_VERIFICATION` — **not** PASS evidence. Slices **46/47** (genuinely open, code not started) added to the table above from PROGRESS. No code changes on `main` since 2026-09-11 (CI-cadence split, docs already synced). See DECISIONS #186–#187.

**Embedding-provider track (2026-09-24, rescoped batch-first):** **48A → 48B → 48C** (+ **48D** Could). DoubleWord is batch/async by nature: 48A ports the docextract pattern (`playgroup_202602_docextract/llm_doubleword.py` + `extractor.py::_run_all_doubleword`) — submit-all, detached asyncio watcher polling all batches, checkpoint + **boot resume** — because `SWEEP_EXECUTOR` has **one worker** and must never wait hours on a batch. Independent of 32C/32B and 46/47; 48A soft-depends on 47 only for entry-point hygiene (never grow `_run_sweep_inner`). Brief: [`BRIEF-doubleword-embedder.md`](BRIEF-doubleword-embedder.md). DECISIONS #200–#204.

**Elasticsearch vector-store track (2026-09-24, added via EFP Add path; nw-reviewed + reuse-explicit):** **49 → 50 → 51** (all Must, sequential; theme `05-storage`; former 51+52 merged into the Slice 51 closeout — #218). Each slice carries an explicit **Reuse ledger** (reuse→extend→extract→write-new) — #219. Three nw reviewers ran on the draft (architect / data-engineer / acceptance-designer); findings applied, misreads corrected, out-of-scope pushed back — #217. Third swappable vector store behind the Slice 49 `VectorStoreAdapter` registry — config-only switching, full dense/sparse/hybrid parity, Basic-licence + unquantized HNSW + client-side RRF, local Docker profile, nightly CI, and the full 15-stage user journey with a registry-driven docs-parity gate. **ES is vector-only (D1)** — run state stays on Mongo/Postgres via a new `VECTOR_STORE_BACKEND` that defaults to `STORAGE_BACKEND`. Source: pasted owner spec (verified against `main @ 76d19b3`, re-derived to `main @ dcdbd6f`). **Reconcile:** the spec numbered these 48–51, but 48A–48D is the merged DoubleWord work and `ADR-005` is the DoubleWord ADR — shifted to **49–52** and **ADR-006** (D1–D5 accepted as-is). DECISIONS #213–#216.

**Redis track (2026-09-24, EFP Add path; reuse-explicit; 5 nw reviewers, all findings applied — #230):** **52 → 53** (+ **54** Could). Source: [`BRIEF-redis-evaluation.md`](BRIEF-redis-evaluation.md) (owner prompt v2 + reconciliation). **52** fuses all research steps into one docs-only spike, reusing the 49/51 adapter review and 15-stage journey (only the Redis delta is new), and ends in an owner **GO / NO-GO** per branch. **53** is Branch A: Redis is the *fourth* store and the first to arrive after 49–51's generic machinery, so adapter core + full journey fit in **one** slice. It is also the live test of the zero-changes criterion (no route / sweep / UI-component / CLI-command diff). **54** is Branch B: the embedding cache is the only Redis infra use with a second real implementation, and it reuses 48A's cache key and API. Job queue → **Slice 16 Approach B**; rate limiting, LangCache and Redis-for-CI → **Won't**, with flip triggers (#226). Redis adopts D1–D5; memory, eviction and persistence become adapter preflight/capability values (#223). **Numbering:** Redis = **ADR-007** (005 DoubleWord, 006 ES) and **QUICKSTART Path F**; "Slice 52" in #213–#217 refers to the *former* ES slice merged into 51 (#218), and from #220 on it means the Redis spike. Execution: **52 may run now** (docs-only, parallel with 49); **53 after 51 ✅ + 52 GO**; **54 after 48A ✅ + 52 GO**. DECISIONS #220–#229.

**Slice 52–54 skill proposal (2026-09-24):** 52: `/nw-research` (primary) · `/divergence-check` (49/51 specs vs `main`) · `/verify-slice` · `/clean-commit`; artifact-design for the HTML guide. 53/54: `/tdd` · `/nw-execute` (primary) · `/verify-slice` · `/clean-commit` · `/sync-docs` (53b journey). Rules: `software-craft.mdc`, `test-writing-*.mdc`, `security.md` (`REDIS_URL` secret redaction in `/api/stores`, `rediss://` TLS, bind 127.0.0.1), `shell-script-hygiene.mdc` (bash 3.2-safe `storage_mode.sh`), `documentation-best-practices.mdc`. Model split unchanged (Planning opus-4-8 · Execution sonnet-5; 52 runs at the planning tier since it's research/judgment). **harness-scout:** not re-run at planning time. Fresh `detect_confirm` is a Before-Check in 52, 53 and 54; degradation logged in #228.

**Slice 49–51 skill proposal (2026-09-24):** `/tdd` · `/verify-slice` · `/clean-commit` · `/sync-docs` · `/nw-execute` (primary) · `/divergence-check` (spec vs code, given base-commit drift). Rules: `software-craft.mdc`, `test-writing-*.mdc`, `security.md` (API key + TLS + outbound HTTP redaction), `git-github-best-practices.mdc`, `documentation-best-practices.mdc` (Slice 51 closeout). Frontend touched only for label sourcing (Slice 51) — no `/frontend-advisor`. Model split unchanged (Planning opus-4-8 · Execution sonnet-5). **harness-scout:** not re-run at planning time — Slices 49, 50, 51 must each run fresh `detect_confirm` at slice start (seam refactor / external service / infra-multi-file+CI+docs respectively); degradation logged DECISIONS #216.

**Slice 48 skill proposal (2026-09-24):** `/tdd` · `/verify-slice` · `/clean-commit` · `/sync-docs` · `/nw-execute` (primary) · `/divergence-check` (brief vs spec). Rules: `software-craft.mdc`, `test-writing-*.mdc`, `security.md` (outbound HTTP + secret), `git-github-best-practices.mdc`. No `/frontend-advisor` (badge/progress tweaks only). Model split unchanged. **harness-scout:** not re-run at planning time — 48A, 48B and 48C must each run fresh `detect_confirm` at slice start (external async integration + event-loop/thread seam; 48C identity/index namespace); degradation logged DECISIONS #197/#204, superseded for Slice 48 by #211.

**PCTO escape hatch (Slice 22):** If slices 32–36 slip **>2 days** past the PCTO deadline, start Slice 22 on Mongo via StorageBackend Protocol only (hard dep: 32 merged); budget ~30 min to re-port history queries when Slice 38 lands; retest on Supabase backend after 38.

**CI:** Mandatory Postgres regression job from Slice 33 merge onward; cutover gates in PRD (latency ≤2× p99, hybrid drift ≤5%, rollback >30 min).

**Docs:** Per-slice user/dev guide gates in [PRD §Documentation matrix](PRD-supabase-pgvector-migration.md#documentation-matrix); `/sync-docs` at Slices **37** and **38**.

### Infrastructure slices (complete — tracked in [docs/plan/slices/PROGRESS.md](../plan/slices/PROGRESS.md))

| # | Name | Status | Notes |
|---|------|--------|-------|
| 14 | Docker Compose | ✅ COMPLETE | `./start-services.sh` |
| 18 | Unified retriever config | ✅ COMPLETE | `retrievers` list format |
| 20 | Toolchain hardening | ✅ COMPLETE | quality-gates, gitleaks, dependabot |
| 24 | Port standardisation | ✅ COMPLETE | frontend :5374, SIE :8720 |

## Deferred Work (no slice yet — see GAP_ANALYSIS)

| Area | Blocker | Target |
|------|---------|--------|
| Vite 6 → 8 + `@vitejs/plugin-react` upgrade | Peer dep conflict (#43 closed) | Future toolchain slice |
| ESLint 8 → 9 + react-refresh 0.5 + security 4.0 | Config migration required (#41, #42 closed) | Future toolchain slice |
| eslint-plugin-react-hooks 7 | React 19 hook rules fail CI (#26 closed) | After SearchExplorerScreen refactor |
| sentence-transformers v4+ (+ transformers ≥5.10) | ST 3.x requires `transformers<5`; CrossEncoder API/mypy (#40 closed); clears CVE-2026-4372/5241/1839/9856 | Dedicated ML stack slice — until then: `.trivyignore` / `.meterian` / `pip-audit.sh` |
| langsmith ≥0.8.18 (GHSA-f4xh-w4cj-qxq8) | sie-sdk pins `websockets>=14,<15`; fix needs `websockets≥15` | sie-sdk pin lift — until then: `.trivyignore` / `.meterian` / `pip-audit.sh` |
| aim ≥4.x (CVE-2025-51464 / CVE-2025-5321) | PyPI aim 4.0.0–4.0.3 yanked; latest stable 3.29.1 | Non-yanked aim 4.x stable + AimLogger/aim-ui smoke — until then: `.meterian` + Aim UI opt-in only |
| Mongo adapter removal | Dual-backend kept through Slice 38 | Post-cutover cleanup (Won't this cycle) |

## Supporting Artifacts

| File | Status | Read time | Last Updated |
|------|--------|-----------|--------------|
| PRD-supabase-pgvector-migration.md | updated | ~3 min | 2026-07-26 |
| GAP_ANALYSIS.md | updated | ~2 min | 2026-07-29 |
| DECISIONS.md | updated | ~2 min | 2026-07-29 |
| HANDOFF.md | updated | ~2 min | 2026-07-29 |
| [../plan/slices/PROGRESS.md](../plan/slices/PROGRESS.md) | merged SSOT | ~2 min | 2026-07-29 |
| interview_summary.md | reconstructed | ~1 min | 2026-07-02 |
| gate-evidence/ | backfilled (21, 25, 25B, 29) | — | 2026-07-09 |

## Slice Token Summary

Updated as each slice reaches Gate Status PASSED.

| Slice | Plan tkns in/out | Exec tkns in/out | Turns | Context pressure |
|-------|-----------------|-----------------|-------|-----------------|
| 21 — SIE Skateboard | — / — | — / — | — | — |
| 25 — Atlas Local | — / — | — / — | — | — |
| 25B — Atlas Switching | — / — | — / — | — | — |
| 32–38 — Supabase migration | — / — | — / — | — | — |
| 22 — SIE Scooter | — / — | — / — | — | — |
| 23 — SIE Bicycle | — / — | — / — | — | — |

## Reviews

| Date | Reviewer | Verdict | Notes |
|---|---|---|---|
| 2026-07-09 | nw-solution-architect-reviewer (iter 1) | Conditionally approved | AC coupling, equivalence gates, Slice 22 Protocol dep — edits applied same day |
| 2026-07-09 | local (data/platform/PO) | Partial | Usage limit — merged into PRD/TRAIL/33/36/37 |
| 2026-07-09 | nw-product-owner-reviewer (iter 2) | **APPROVED** | DoR 9/9; escape hatch, soft dep 22→38, Slice 27→36, CI note verified |
| 2026-07-09 | nw-data-engineer-reviewer (iter 2) | **APPROVED** | 8.3/10; 7 non-blocking gaps (CI schedule, cost row, boot-recon GWT, minimal-docker trade-off) |
| 2026-07-09 | nw-solution-architect-reviewer (iter 2) | **APPROVED** | Conditional items verified: behavioral ACs, storage seam, experiment_id contract, SPLADE fallback; ready for Slice 32 |
| 2026-07-09 | nw-platform-architect-reviewer (iter 2) | **Conditionally approved** | Cutover gates + mandatory Postgres CI — applied to PRD/33/38 |
| 2026-07-09 | nw-solution-architect-reviewer (iter 3) | **APPROVED** | Gap-bridge uncommitted delta: TRAIL↔PROGRESS↔specs aligned; Slice 22 dep 32; SLICE-11 created |
| 2026-07-09 | nw-documentarist-reviewer (iter 3) | **APPROVED** | Gap-bridge docs; soft-dep 30 note applied; latency handoff in SLICE-11 |
| 2026-07-26 | nw-platform-architect-reviewer (Slice 37) | **CONDITIONALLY APPROVED** (planning) | Unimplemented Musts reclassified as execution exits; 422 + post-start templates applied |
| 2026-07-26 | nw-platform-architect-reviewer (Slice 37) | **CONDITIONALLY APPROVED** (planning) | Missing Musts reclassified as execution exits; 422 + post-start templates applied |
| 2026-07-26 | nw-platform-architect-reviewer (Slice 38) | **NEEDS REVISION** → remediations applied | BLOCKERs: flip surfaces + Mongo export; latency metric; baseline feasibility; SUPABASE_URI placeholder — DECISIONS #114–#118; pins #120–#121 |
| 2026-07-26 | Slice 38 gate hygiene | All non-100%-Yes gates → Slice 43 residuals | DECISIONS #125/#126 — local comparison only for 38 COMPLETE |
| 2026-07-26 | Slice 38 COMPLETE | ✅ PASSED — no default flip (#130 Won't) | ADR-004 + comparison VERIFIED; default stays mongodb permanently; backends independent (#129) |
| 2026-09-10 | nw-solution-architect-reviewer (EFP final) | **APPROVED** | Remediations #114–#182 verified; escape hatch + evidence honesty + ownership; DECISIONS #184 |
| 2026-09-10 | nw-product-owner-reviewer (EFP final) | **APPROVED** | #179 hatch; 32C→32B order; 32C M2 docs-only; Slice 28/33 cites |
| 2026-09-10 | nw-documentarist-reviewer (EFP final) | **APPROVED** | HANDOFF snapshot + gate-evidence hierarchy; Slice 22 PENDING_VERIFICATION honesty |
| 2026-09-10 | nw-acceptance-designer-reviewer (EFP final) | **APPROVED** | Prior 10 error-path GWT blockers closed; 28/31 happy-path bias non-blocking |
| 2026-09-24 | nw-solution-architect-reviewer (Slice 48 plan) | **CONDITIONALLY APPROVED** → remediated | Pure/effectful pre-embed split; exact SIE-guard call sites (3, not 2); `embedding_providers` back-compat; `provider_for_model` signature — DECISIONS #199 |
| 2026-09-24 | nw-system-designer-reviewer (48B/48C) | **CONDITIONALLY APPROVED** → remediated | Double-billing guard via `metadata.job_key` + V10; per-identity lock; SQLite WAL + single worker; temp-dir WARN; PG >2000-dim 422 moved to 48C (48B has no dim axis) — #199 |
| 2026-09-24 | nw-product-owner-reviewer (48 DoR) | **CONDITIONALLY APPROVED** → remediated | 48C D1–D3 no-auto-proceed; `DOUBLEWORD_MODE` HITL surfaced in PROGRESS; boot-resume deferral in 48B contract — #199 |
| 2026-09-24 | nw-acceptance-designer-reviewer (48 GWT) | **NEEDS REVISION** → partially remediated | Outcome phrasing + business language applied; `@pending_decision` tags on 48C; `@contract-shape` tags **declined** (not a repo convention) — #199 |
| 2026-09-24 | nw-solution-architect-reviewer (iter 2, batch-first) | **CONDITIONALLY APPROVED** → remediated | `defer_for_pre_embed` helper (≤1 branch per entry point) + coverage After-Check; S2-client BLOCKER **declined** (spec already specifies AsyncOpenAI) — #206 |
| 2026-09-24 | nw-system-designer-reviewer (iter 2, batch-first) | **NEEDS REVISION** → remediated | Watcher error isolation + supervisor + `/healthz`; sequential polling, 429 backoff, adaptive interval; parse off event loop; named checkpoint lock + atomic write; key-removed-at-boot handling. Fail-on-transient-error and batch ceiling **declined** — #206 |
| 2026-09-24 | nw-product-owner-reviewer (iter 2) | **APPROVED** | DoR 9/9; S1 ship-first wording and 48C execution gate applied — #206 |
| 2026-09-24 | nw-acceptance-designer-reviewer (iter 2) | **CONDITIONALLY APPROVED** → remediated | Poll-cadence, error-isolation, 429, supervision, key-removed scenarios; analytics fallback Outline; adoption window defined; repeat-run vector identity; 422 phrasing; smoke-test gate note. Retry-only-failed-keys (already covered) and stub-wording change **declined** — #206 |
| 2026-09-24 | EFP health check + quality lens re-run (48A–D, post-merge) | **17/18** → remediated | Spec-coverage lines added to 48B/48C, 48C harness pre-flight; #197 harness note superseded; catalog check (1 embedding model); 48B stays Must; next wave = 48A T0 spike — #208–#212 |
