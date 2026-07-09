# rag-params-finder — Build Progress

**Last Updated**: 2026-07-09 (Supabase/pgvector migration PRD → slices 32–38; dual-backend; ahead of Slice 22)
**Current**: Slices **14** ✅ Docker · **20** ✅ toolchain · **21** ✅ SIE Skateboard · **24** ✅ Port standardisation · **25** ✅ Atlas Local · **25B** ✅ Atlas Switching · **29** ✅ padding propagation | Next: **32** 📋 Storage Protocol → **33–38** Postgres/pgvector cutover · then **22** 📋 SIE Scooter · **28** 📋 results export ([#49](https://github.com/neomatrix369/rag-params-finder/issues/49), @cschanhniem) · **26/27/19** 📦 DEFERRED (Mongo QoL) · **30/31/16/11/23/10** as before

PCTO plan context: [`docs/plan/TRAIL.md`](../plan/TRAIL.md) · Gap analysis: [`docs/plan/GAP_ANALYSIS.md`](../plan/GAP_ANALYSIS.md) · Migration PRD: [`docs/plan/PRD-supabase-pgvector-migration.md`](../plan/PRD-supabase-pgvector-migration.md)

---

## Quick Status

| Slice | Status | Time Target | Notes |
|-------|--------|-------------|-------|
| 1 — Skateboard | ✅ COMPLETE | ~75 min | End-to-end pipeline verified |
| 2 — Rerank | ✅ COMPLETE | ~10 min | Voyage + local reranking |
| 3 — Sweep expansion | ✅ COMPLETE | ~15 min | Cartesian product of runs ⭐ CORE FEATURE |
| 4 — Live status + polling | ✅ COMPLETE | ~15 min | Phase tracking, CLI --watch, detail screen |
| 5 — Multiple queries from persona JSON | ✅ COMPLETE | ~10 min | Loop over persona questions |
| 6 — Additional chunkers + retrieval | ✅ COMPLETE | ~45 min | fixed, token, sentence, semantic + sparse/hybrid + 5 new configs |
| 7 — Free/local embedding + reranking | ✅ COMPLETE | ~15 min | sentence-transformers, no API key needed |
| 8 — Dashboard UX improvements | ✅ COMPLETE | ~2 h | Loading feedback panels, polling indicators, pagination, unified chrome |
| 9 — Experiment deletion | ✅ COMPLETE | ~1 h | CLI delete command + dashboard confirmation modal, cascade cleanup |
| — — Vector DB stats + collapsible rows + boot reconciliation | ✅ COMPLETE | ~1.5 h | Cluster/experiment storage stats; collapsible panels; orphan `running` → `partial` on server boot |
| — — Pause/resume + Voyage catalog expansion | ✅ COMPLETE | ~2 h | Cooperative pause/resume; 12 Voyage embedding models; `voyage-context-3` contextualized API + segment splitting |
| — — Voyage sweep UX + Atlas tier specs | ✅ COMPLETE | ~1 h | Elapsed/ETA on progress card; timezone-aware UTC timestamps; `started_at` on first run; cluster tier/provider/region in vector DB stats |
| — — Search index preflight + indexes CLI | ✅ COMPLETE | ~2 h | `search_index_plan` + `search_index_guard`; HTTP 422 on submit; fail before runs; `indexes list\|reset`; 17 pytest scenarios |
| — — Scoped logging (Option A) | ✅ COMPLETE | ~1 h | `scope_log.py` server/CLI; `devLog.ts` dashboard dev console; Voyage error + dashboard failure visibility |
| — — Dashboard polling + API responsiveness | ✅ COMPLETE | ~1 h | `executors.py` thread pools; list 2 s / stats 60 s / explore 15 s polls; batched db-stats; anti-jitter `PollingIndicator` |
| — — Kimchi embedding provider | 🔀 BRANCH | ~2 h | Full CAST integration on `tessl-hackathon-kimchi-integration`; **main** has `kimchi` in `Provider` type only (no registry models / embedder yet) — v0.8.0 release notes are historical |
| — — Unit pytest suite | ✅ COMPLETE | ~1 h | **26 tests** at Slice 20 baseline (now **58** — see `development.md`) |
| 18 — Unified retriever config | ✅ COMPLETE | ~4–6 h | Unified "retrievers" group (traditional search + rerankers); auto-migrate old format; multi-reranker chains; see [`SLICE-18-UNIFIED-RETRIEVER-CONFIG.md`](SLICE-18-UNIFIED-RETRIEVER-CONFIG.md) |
| 10 — Run recovery (retry) | 📋 PLANNED | ~1–2 h | Retry FAILED `(± INTERRUPTED)` runs in-place; boot **reconciliation** done; pause/resume covers not-yet-started combos; **retry** not yet — see [`SLICE-10-RUN-RECOVERY.md`](SLICE-10-RUN-RECOVERY.md) |
| 11 — Search Explorer enhancements | 📋 PLANNED | ~45 min | Visualization + query filtering only — **export moved to Slice 28** |
| 28 — Results export (CSV/JSONL) | 📋 PLANNED | ~1.5 h | Contributor [@cschanhniem](https://github.com/cschanhniem) — [issue #49](https://github.com/neomatrix369/rag-params-finder/issues/49) author/assignee · [`SLICE-28-RESULTS-EXPORT.md`](SLICE-28-RESULTS-EXPORT.md) |
| 29 — Padding cross-cutting propagation | ✅ COMPLETE | ~2 h | `_run_config_key()` + API + TS types + UI — spec: [`SLICE-29-PADDING-PROPAGATION.md`](SLICE-29-PADDING-PROPAGATION.md) |
| 16 — Parallel sweep execution | 📋 PLANNED | ~2–4 h | Bounded concurrent `_run_single`; see [`SLICE-16-PARALLEL-SWEEP-RUNS.md`](SLICE-16-PARALLEL-SWEEP-RUNS.md) |
| 20 — Toolchain hardening | ✅ COMPLETE | ~2–3 h | `quality-gates.sh`, `repo-lint.sh`, `pre-push-gates.sh` (`--quick` on push), `install-git-hooks.sh`, coverage CI, ESLint, bandit, pip-audit, gitleaks, dependabot — [`SLICE-20-TOOLCHAIN-HARDENING.md`](SLICE-20-TOOLCHAIN-HARDENING.md) |
| 14 — Docker Compose | ✅ COMPLETE | ~2–3 h | `./start-services.sh`, prod + `docker-compose.dev.yml`, Atlas `/healthz` — [`SLICE-14-DOCKER-COMPOSE.md`](SLICE-14-DOCKER-COMPOSE.md) |
| ~~15 — CI/CD~~ | ✅ (via 20) | — | Superseded by Slice 20 — CI + `quality-gates.sh` + git hooks |
| 21 — SIE Skateboard | ✅ COMPLETE | ~4–6 h | SIE embeddings (BGE-M3, Stella-v5); caller-supplied corpus (`corpus: list[str]`); Aim logging; `POST /api/v1/sweep`; enhanced `/health`; `embedder_factory.py` dispatch — spec: [`SLICE-21-SIE-SKATEBOARD.md`](SLICE-21-SIE-SKATEBOARD.md) |
| 24 — Port standardisation | ✅ COMPLETE | ~1 h | Unique static ports: frontend 5173→5374 (avoids Vite default), SIE 8080→8720 (avoids Jenkins/Tomcat/etc.); backend 8001 unchanged — spec: [`SLICE-24-PORT-STANDARDISATION.md`](SLICE-24-PORT-STANDARDISATION.md) |
| 25 — Atlas Local Dev Mode | ✅ COMPLETE | ~1 h | `mongodb-atlas-local` Docker image as opt-in local backend; `local-atlas` compose profile; auto-provision all search indexes on boot for local URI; eliminates M0 512 MB ceiling for local dev — spec: [`SLICE-25-ATLAS-LOCAL.md`](SLICE-25-ATLAS-LOCAL.md) |
| 25B — Atlas Backend Switching | ✅ COMPLETE | ~1 h | `./start-services.sh --local`; `./start-services.sh mongodb start\|stop\|reset\|status`; unified [`mongodb-setup.md`](../user-guide/mongodb-setup.md); `scripts/lib/compose.sh` + `server/db/mongodb_uri.py` — spec: [`SLICE-25B-ATLAS-SWITCHING.md`](SLICE-25B-ATLAS-SWITCHING.md) |
| 22 — SIE Scooter | 📋 PLANNED | ~3 h | SIE reranking + SPLADE sparse + `GET /api/v1/best-config` — Must — **after Slice 38** — spec: [`SLICE-22-SIE-SCOOTER.md`](SLICE-22-SIE-SCOOTER.md) |
| 23 — SIE Bicycle | 📋 PLANNED | ~3 h | Ollama + Tier 2–3 retrieval + Evidently AI (Could, post-hackathon) — spec: [`SLICE-23-SIE-BICYCLE.md`](SLICE-23-SIE-BICYCLE.md) |
| 26 — Local MongoDB smooth-path docs | 📦 DEFERRED | ~1 h | Re-scope after Postgres cutover — [`SLICE-26-LOCAL-MONGODB-DOCS.md`](SLICE-26-LOCAL-MONGODB-DOCS.md) |
| 27 — MongoDB mode indicator | 📦 DEFERRED | ~2 h | Re-scope as storage-mode indicator — [`SLICE-27-MONGODB-MODE-INDICATOR.md`](SLICE-27-MONGODB-MODE-INDICATOR.md) |
| 19 — Atlas storage quota guard | 📦 DEFERRED | ~3–5 h | Atlas-specific; Postgres stats in Slice 36 — [`SLICE-19-STORAGE-QUOTA-GUARD.md`](SLICE-19-STORAGE-QUOTA-GUARD.md) |
| 32 — Storage Backend Protocol | 📋 PLANNED | ~3–4 h | **Next** — Protocol + Mongo adapter — [`SLICE-32-STORAGE-BACKEND-PROTOCOL.md`](SLICE-32-STORAGE-BACKEND-PROTOCOL.md) |
| 33 — Postgres schema + CRUD | 📋 PLANNED | ~4–6 h | Pool, schema, cascade delete — [`SLICE-33-POSTGRES-SCHEMA-CRUD.md`](SLICE-33-POSTGRES-SCHEMA-CRUD.md) |
| 34 — Postgres dense retrieval | 📋 PLANNED | ~3–4 h | pgvector HNSW + embedding_model filter — [`SLICE-34-POSTGRES-DENSE-RETRIEVAL.md`](SLICE-34-POSTGRES-DENSE-RETRIEVAL.md) |
| 35 — Postgres sparse + hybrid | 📋 PLANNED | ~4–5 h | tsvector + RRF; SPLADE sparsevec gate — [`SLICE-35-POSTGRES-SPARSE-HYBRID.md`](SLICE-35-POSTGRES-SPARSE-HYBRID.md) |
| 36 — Postgres preflight + stats | 📋 PLANNED | ~3–4 h | Index guard, db-stats, indexes CLI — [`SLICE-36-POSTGRES-PREFLIGHT-STATS.md`](SLICE-36-POSTGRES-PREFLIGHT-STATS.md) |
| 37 — Postgres local/cloud parity | 📋 PLANNED | ~3–4 h | Docker pgvector + Supabase + boot reconciliation — [`SLICE-37-POSTGRES-LOCAL-CLOUD-PARITY.md`](SLICE-37-POSTGRES-LOCAL-CLOUD-PARITY.md) |
| 38 — Cutover + ADR-004 | 📋 PLANNED | ~3–4 h | Side-by-side quality, ADR-004, default Postgres — [`SLICE-38-CUTOVER-ADR-004.md`](SLICE-38-CUTOVER-ADR-004.md) |
| 30 — Search Explorer UX | 📋 PLANNED | ~2 h | Tab latency, zero-score noise, BM25 labels, VDB card — Could — spec: [`SLICE-30-SEARCH-EXPLORER-UX.md`](SLICE-30-SEARCH-EXPLORER-UX.md) |
| 31 — Experiment list filter | 📋 PLANNED | ~2 h | Status dropdown + name/ID search — Should — spec: [`SLICE-31-EXPERIMENT-LIST-FILTER.md`](SLICE-31-EXPERIMENT-LIST-FILTER.md) |

**Legend**: 📋 PLANNED | 🔨 IN PROGRESS | ✅ COMPLETE | 🔀 BRANCH | 📦 DEFERRED

---

## Plan Track (PCTO + storage migration)

Plan-tracked slices with dependencies. Gate evidence: [`docs/plan/gate-evidence/`](../plan/gate-evidence/). PRD: [`docs/plan/PRD-supabase-pgvector-migration.md`](../plan/PRD-supabase-pgvector-migration.md).

| Slice | MoSCoW | Status | Depends on | Notes |
|-------|--------|--------|------------|-------|
| 21 | Must | ✅ COMPLETE | — | SIE Skateboard |
| 25 | Should | ✅ COMPLETE | 21 | Atlas Local |
| 25B | Should | ✅ COMPLETE | 25 | Atlas switching |
| 29 | Must | ✅ COMPLETE | — | Padding propagation |
| 32 | Must | 📋 PLANNED | — | **Next** — Storage Protocol + Mongo adapter |
| 33 | Must | 📋 PLANNED | 32 | Postgres schema + CRUD |
| 34 | Must | 📋 PLANNED | 33 | Dense pgvector |
| 35 | Must | 📋 PLANNED | 34 | Sparse + hybrid RRF |
| 36 | Must | 📋 PLANNED | 35 | Preflight + db-stats |
| 37 | Must | 📋 PLANNED | 36 | Local/cloud parity |
| 38 | Must | 📋 PLANNED | 37 | ADR-004 cutover |
| 28 | Must | 📋 PLANNED | — | External — [@cschanhniem](https://github.com/cschanhniem) / [#49](https://github.com/neomatrix369/rag-params-finder/issues/49) |
| 22 | Must | 📋 PLANNED | 21, 38 | SIE Scooter — after storage cutover |
| 26 | Should | 📦 DEFERRED | 25B | Mongo docs — re-scope post-cutover |
| 27 | Should | 📦 DEFERRED | 25B | Mode indicator — re-scope |
| 19 | Should | 📦 DEFERRED | — | Atlas quota — Postgres path in 36 |
| 16 | Should | 📋 PLANNED | — | Parallel sweep |
| 11 | Could | 📋 PLANNED | — | Search Explorer enhancements |
| 23 | Could | 📋 PLANNED | 22 | SIE Bicycle |
| 10 | Could | 📋 PLANNED | — | Run recovery |
| 30 | Could | 📋 PLANNED | — | Search Explorer UX |
| 31 | Should | 📋 PLANNED | — | Experiment list filter |

**Execution order**: 21 → 25 → 25B → 29 (done) → **32 → 33 → 34 → 35 → 36 → 37 → 38** → **22** → 28*(external)* → 31 → 30 → 16 → 11 → 23 → 10

---

## Maintenance Log (non-slice)

| Date | Item | Outcome |
|------|------|---------|
| 2026-07-01 | Dependabot PR triage #26–#43 | 4 merged (#36–#39), 5 closed (#26, #40–#43) |
| 2026-07-02 | Plan health-check + gap refresh | TRAIL, GAP_ANALYSIS, HANDOFF updated; gate-evidence backfilled |
| 2026-07-02 | Merge plan PROGRESS into slices PROGRESS | Single SSOT — removed `docs/plan/PROGRESS.md` duplicate |
| 2026-07-04 | Merge PRs #56, #57, #58 | Actions upgrades (cache v6, checkout v7) + plan health-check refresh; all merged to main |
| 2026-07-04 | Plan health-check + gap analysis | TRAIL health ✅ OK (0 legacy gaps); PR queue updated; execution order + PR merge prereqs reviewed |
| 2026-07-05 | Merge PRs #47, #48, #59, #60, #61 | Chunker fixes + plan gap analysis + review follow-ups on main; Slice 28 unblocked |
| 2026-07-06 | Plan prereq clearance sync | HANDOFF, PROGRESS queue, slice Before-Checks updated; #47/#48 marked satisfied |
| 2026-07-06 | Slice 28 contributor assigned | @cschanhniem (issue #49 author/assignee) owns implementation; core team on Slice 22 |
| 2026-07-06 | Slice 29 complete | Padding in `_run_config_key()`, explore responses, sweep_summary, TS types, ExperimentDetail + SearchExplorer UI |
| 2026-07-09 | Supabase migration plan | PRD integrated; slices 32–38 Must; dual-backend; ahead of 22; deferred 26/27/19 |

---

## Open PR Queue (snapshot 2026-07-06)

| PR | Verdict | Reason |
|----|---------|--------|
| #13 | Branch track | Kimchi integration — separate hackathon |

---

## Slice 1: Skateboard ✅

**Status**: ✅ BUILT (pending verification) | **Started**: 2026-05-02 | **Completed**: 2026-05-02 | **Target**: ~75 min

### Goal
End-to-end pipeline working with one chunker (RECURSIVE), one embedding model (voyage-3.5-lite), one query, no rerank, no sweep.

### Acceptance Criteria (Code Complete)
- [x] FastAPI boots; `/healthz` returns ok — **Code ready** (needs .env)
- [x] Atlas connection works; 6 collections + vector index exist — **Code ready** (needs manual vector index in Atlas UI)
- [x] `POST /experiments` accepts a minimal config and runs in BackgroundTask — **Code complete**
- [x] Pipeline: parse PDF → RECURSIVE chunker → Voyage embed → Atlas write → Voyage query embed → DENSE search → write results — **Code complete**
- [x] CLI submits and exits cleanly (no `--watch` polling yet) — **Code complete**
- [x] Dashboard ExperimentsScreen renders ONE row from `/experiments` — **Code complete**
- [x] README has Quickstart section (judge can run locally) — **Complete**

### Verification Pending
- [ ] Live test with real .env (VOYAGE_API_KEY + MONGODB_URI)
- [ ] Atlas vector index created manually
- [ ] Sample PDF added to `papers/sample.pdf`
- [ ] End-to-end run: CLI submit → server execute → dashboard display

### Files to Create
**Server**:
- `server/__init__.py`
- `server/main.py` — FastAPI app + /healthz
- `server/api/experiments.py` — POST /experiments, GET /experiments
- `server/core/pdf_parser.py` — pypdf wrapper
- `server/core/chunkers/__init__.py` — Enum + dispatcher
- `server/core/chunkers/recursive.py` — LangChain RecursiveCharacterTextSplitter
- `server/core/embedder.py` — Voyage client singleton
- `server/core/orchestrator.py` — Per-run pipeline executor
- `server/models/enums.py` — ChunkingMethod, RetrievalMethod, Phase
- `server/models/config.py` — Pydantic config models
- `server/models/status.py` — RunStatus model
- `server/models/results.py` — Result models
- `server/db/atlas.py` — MongoDB client + collection helpers
- `server/db/indexes.py` — Vector index creation
- `server/utils/logger.py` — Structured logging

**CLI**:
- `cli/__init__.py`
- `cli/main.py` — Typer app + `run` command
- `cli/config_loader.py` — YAML parser
- `cli/api_client.py` — HTTP client to server

**Frontend**:
- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/tailwind.config.js`
- `frontend/postcss.config.js`
- `frontend/index.html`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/ExperimentsScreen.tsx`
- `frontend/src/services/apiClient.ts`
- `frontend/src/types/index.ts` — Hand-mirrored enums + types

**Configs**:
- `configs/example.yaml`
- `configs/questions.example.json`

**Docs**:
- `docs/slices/SLICE-01-SKATEBOARD.md`
- `docs/ARCHITECTURE.md` (brief)

### Quick-Win Cuts
- No reranking (Slice 2)
- No sweep expansion (Slice 3)
- No live status tracking (Slice 4)
- No multiple queries (Slice 5)
- No recovery logic (Slice 10)
- No --watch CLI flag (Slice 4)

### Verification
```bash
# Server
uvicorn server.main:app --reload --port 8001
curl http://localhost:8001/healthz

# CLI
rag-params-finder run --config configs/example.yaml

# Dashboard
cd frontend && npm run dev
```

### Files Created (53 total)

**Foundation** (7):
- pyproject.toml, .env.example, .gitignore, README.md
- docs/slices/PROGRESS.md, docs/ARCHITECTURE.md, docs/slices/SLICE-01-SKATEBOARD.md

**Server** (20):
- server/{__init__.py, main.py, utils/logger.py}
- server/models/{enums.py, config.py, status.py, results.py}
- server/db/{atlas.py, indexes.py}
- server/core/{orchestrator.py, pdf_parser.py, embedder.py, retriever.py}
- server/core/chunkers/{__init__.py, recursive.py, fixed.py, token.py, sentence.py, semantic.py}
- server/api/experiments.py

**CLI** (4):
- cli/{__init__.py, main.py, config_loader.py, api_client.py}

**Frontend** (13):
- frontend/{package.json, vite.config.ts, tailwind.config.js, postcss.config.js, index.html, tsconfig.json, tsconfig.node.json}
- frontend/src/{main.tsx, App.tsx, index.css}
- frontend/src/components/ExperimentsScreen.tsx
- frontend/src/services/apiClient.ts
- frontend/src/types/index.ts

**Configs** (2):
- configs/{example.yaml, questions.example.json}

**Placeholders** (4 chunkers):
- fixed.py, token.py, sentence.py, semantic.py (NotImplementedError, deferred to Slice 6)

### Decisions
| Decision | Why |
|---|---|
| pypdf over pdfminer.six | Simpler API, sufficient for plain text extraction |
| Voyage voyage-3.5-lite only | Cheapest model for MVP, add others in Slice 7 |
| RECURSIVE chunker only | Most common method, LangChain already has it |
| No rerank in Slice 1 | Simplify to DENSE-only retrieval first |
| BackgroundTasks not Celery | No queue infrastructure for hackathon MVP |
| Tailwind installed locally | No CDN scripts in index.html per spec |
| Hand-mirrored TS types | No codegen tooling for hackathon speed |
| Hardcoded single query | Defer persona JSON loop to Slice 5 |

---

## Slice 2: Rerank ✅

**Status**: ✅ BUILT | **Started**: 2026-05-02 | **Completed**: 2026-05-02 | **Target**: ~20 min | **Actual**: ~10 min

### Goal
Add Voyage rerank-2.5-lite to refine dense search results (top-20 → top-5).

### What Changed
- **NEW**: `server/core/reranker.py` — Voyage rerank client (reuses embedder's client singleton)
- **EDIT**: `server/core/orchestrator.py` — Conditional RERANKING phase after QUERYING; fetches `top_k_initial` candidates, reranks to `top_k_final`
- **EDIT**: `configs/example.yaml` — `rerank_model: rerank-2.5-lite` (was `null`)

### Key Design Decisions
| Decision | Why |
|---|---|
| Reuse embedder's `get_client()` singleton | Voyage SDK uses one client for embed + rerank; avoid duplicate initialization |
| Conditional reranking (gate on `rerank_model`) | Allows `null` to skip reranking for A/B comparison |
| `model_copy(update=...)` for SearchResult | Immutable Pydantic updates — preserves original dense_score alongside rerank_score |

### No Changes Required
- Frontend types already had `rerank_score?: number`
- `Phase.RERANKING` enum already existed
- `RetrievalConfig.rerank_model` already in config model

---

## Slice 3: Sweep Expansion ✅

**Status**: ✅ BUILT | **Started**: 2026-05-02 | **Completed**: 2026-05-02 | **Target**: ~25 min | **Actual**: ~15 min

### Goal
Cartesian product expansion: one YAML config with N models × M methods × P sizes × Q overlaps × R retrieval methods → N×M×P×Q×R independent runs.

### What Changed
- **NEW**: `RunParams` model + `expand_sweep()` in `server/models/config.py`
- **NEW**: `server/api/runs.py` — `GET /runs/{run_id}/status` endpoint
- **NEW**: `server/api/__init__.py` — package init
- **REWRITE**: `server/core/orchestrator.py` — split into `run_sweep()` + `run_single()` (accepts `RunParams`)
- **REWRITE**: `server/api/experiments.py` — shows run_count in POST response, adds `GET /experiments/{id}/results`, includes run statuses in `GET /experiments/{id}`
- **EDIT**: `server/main.py` — register `/runs` router
- **EDIT**: `configs/example.yaml` — multi-value sweep (3 chunk_sizes × 2 overlaps = 6 runs)
- **EDIT**: `frontend/src/types/index.ts` — `run_count`, `failed_count` fields on `Experiment`
- **EDIT**: `frontend/src/components/ExperimentsScreen.tsx` — Runs column + partial status badge

### Key Design Decisions
| Decision | Why |
|---|---|
| `expand_sweep()` as pure function on config | Testable without side effects; called both in API (preview count) and orchestrator (execute) |
| Sequential runs (not parallel) | `parallelism` stored on experiments but orchestrator ignores it pending [Slice 16](SLICE-16-PARALLEL-SWEEP-RUNS.md) |
| `run_sweep()` + `run_single()` split | Single Responsibility — sweep management vs pipeline execution |
| `on_error: continue/stop` | Allows partial completion without losing all results |
| `partial` status for mixed outcomes | Distinguishes "some failed" from "all failed" or "all complete" |

---

## Slice 4: Live Status + Polling ✅

**Status**: ✅ BUILT | **Started**: 2026-05-02 | **Completed**: 2026-05-02 | **Target**: ~30 min | **Actual**: ~15 min

### Goal
Live status tracking with CLI --watch and dashboard drill-down.

### What Changed
- **EDIT**: `cli/main.py` — Added `--watch` flag (default on), Rich Live table polling runs every 2s
- **EDIT**: `cli/api_client.py` — Added `get_experiment()`, `get_run_status()` helpers
- **EDIT**: `server/core/orchestrator.py` — elapsed_ms tracking per run; experiment_id passed from API layer
- **EDIT**: `server/api/experiments.py` — experiment_id created in handler, returned in POST response
- **NEW**: `server/api/runs.py` — `GET /runs/{run_id}/status`
- **NEW**: `frontend/src/components/ExperimentDetailScreen.tsx` — Phase indicator dots, run table, polling
- **EDIT**: `frontend/src/App.tsx` — Simple state-based routing (list ↔ detail)
- **EDIT**: `frontend/src/components/ExperimentsScreen.tsx` — Clickable rows with `onSelect` prop

### Key Design Decisions
| Decision | Why |
|---|---|
| Rich Live table in CLI | Real-time phase display without clearing terminal |
| experiment_id created in API handler | Returned immediately so CLI can poll before background task finishes |
| Phase indicator dots in dashboard | Visual progress without text clutter |
| State-based routing (no react-router) | Minimal dependency; only two screens |

---

## Slice 5: Multiple Queries from Persona JSON ✅

**Status**: ✅ BUILT | **Started**: 2026-05-02 | **Completed**: 2026-05-02 | **Target**: ~20 min | **Actual**: ~10 min

### Goal
Load queries from persona JSON file and loop over all questions per run.

### What Changed
- **NEW**: `server/core/query_loader.py` — `Query` dataclass + `load_queries()` from persona JSON
- **EDIT**: `server/core/orchestrator.py` — Replaced hardcoded query with `load_queries()` loop; stores `persona_id` and `focus` on each `QueryResult`

### Key Design Decisions
| Decision | Why |
|---|---|
| `Query` as frozen dataclass (not Pydantic) | Lightweight read-only data; no serialization needed |
| Loop inside `run_single()` | Each query embeds + searches + reranks independently |
| Rerank phase entered per query | Phase indicator shows reranking activity for each query |

---

## Slice 7: Free/OS Embedding + Reranking Models ✅

**Status**: ✅ BUILT | **Started**: 2026-05-02 | **Completed**: 2026-05-02 | **Target**: ~15 min

### Goal
Add local sentence-transformers models (embedding + reranking) as alternatives to Voyage AI. No API key, no rate limits. Explicit `provider` field in YAML configs drives routing.

### What Changed
- **NEW**: `server/core/model_registry.py` — Unified registry for embedding and reranker models (provider, dimensions, HuggingFace ID)
- **NEW**: `server/core/local_embedder.py` — sentence-transformers SentenceTransformer wrapper (lazy-load, cached)
- **NEW**: `server/core/local_reranker.py` — sentence-transformers CrossEncoder wrapper (lazy-load, cached)
- **NEW**: `configs/example-local.yaml` — All-local experiment config (no Voyage key needed)
- **NEW**: `configs/example-voyage-ai.yaml` — Preserved Voyage AI config for reference
- **EDIT**: `server/models/config.py` — Added `provider` field to `EmbeddingConfig`, `rerank_provider` to `RetrievalConfig`; Pydantic validators cross-check model names match declared provider; `RunParams` carries `embedding_provider` and `rerank_provider`
- **EDIT**: `server/core/embedder.py` — Accepts `provider` param directly (no longer queries registry at runtime)
- **EDIT**: `server/core/reranker.py` — Accepts `provider` param directly
- **EDIT**: `server/core/orchestrator.py` — Passes `embedding_provider` and `rerank_provider` from `RunParams`
- **EDIT**: `cli/config_loader.py` — Validates models against registry at load time; cross-checks declared provider
- **EDIT**: `server/core/retriever.py` — Dynamic vector index name via `get_index_name(model)` (supports `vector_index_1024` and `vector_index_384`)
- **EDIT**: `server/db/indexes.py` — Updated log messages for multi-dimension indexes
- **EDIT**: `pyproject.toml` — Added `sentence-transformers>=2.6.0` dependency
- **EDIT**: `.env.example` — Documented that Voyage key is optional with local models
- **EDIT**: `README.md` — Updated for provider-based config, removed references to deleted `configs/example.yaml`
- **REMOVED**: `configs/example.yaml` — Replaced by `configs/example-local.yaml`

### Key Design Decisions
| Decision | Why |
|---|---|
| Explicit `provider` field in YAML | Config is source of truth for routing — no reliance on model-name-to-provider lookups at runtime |
| Provider flows through RunParams → orchestrator → embedder/reranker | End-to-end explicit routing; server reload issues can't break dispatch |
| Pydantic model_validator cross-checks provider vs model name | Fast-fail at config parse time with clear error messages |
| `sentence-transformers` for both embedding and reranking | Single package; SentenceTransformer for embeddings, CrossEncoder for reranking |
| `all-MiniLM-L6-v2` as first local model | Well-known, fast, 384-dim, ~23MB — proves the abstraction |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` for local reranking | ~23MB, MS MARCO trained, good quality |
| Separate vector indexes per dimension | Atlas requires exact `numDimensions`; `vector_index_1024` (Voyage) + `vector_index_384` (local) |
| Lazy-load and cache models | First run downloads from HuggingFace; subsequent runs instant |
| `numpy<2` pinned | torch requires NumPy 1.x ABI; NumPy 2.x causes `_ARRAY_API not found` crashes |

---

## Slice 8: Dashboard UX Improvements ✅

**Status**: ✅ COMPLETE | **Started**: 2026-05-17 | **Completed**: 2026-05-17 | **Target**: ~2 h

### Goal
Improve dashboard loading UX with progress feedback, add pagination to all screens, and unify page layout with shared components.

### What Changed
- **NEW**: `frontend/src/components/LoadingFeedbackPanel.tsx` — Progress panel with byte-level progress bars and activity feed
- **NEW**: `frontend/src/components/PollingIndicator.tsx` — Subtle "Syncing..." indicator for background polls
- **NEW**: `frontend/src/components/DashboardShell.tsx` — Shared header and navigation across all screens
- **NEW**: `frontend/src/components/AppPageChrome.tsx` — Shared page wrapper (title, back button, actions)
- **NEW**: `frontend/src/services/fetchWithProgress.ts` — ReadableStream-based fetch with byte-level progress tracking
- **NEW**: `VERIFICATION_CHECKLIST.md` — Manual test cases for all loading states and polling behavior
- **EDIT**: `frontend/src/components/ExperimentsScreen.tsx` — Added pagination (10 items/page), integrated LoadingFeedbackPanel and PollingIndicator
- **EDIT**: `frontend/src/components/ExperimentDetailScreen.tsx` — Added pagination to runs table (10 runs/page)
- **EDIT**: `frontend/src/components/SearchExplorerScreen.tsx` — Added pagination to configs (5/page), collapsed sidebar, integrated re-query progress feedback
- **EDIT**: `frontend/src/services/apiClient.ts` — Refactored to use `fetchWithProgress` for streamed downloads
- **EDIT**: `frontend/src/constants.ts` — Added pagination constants (`ITEMS_PER_PAGE_*`)
- **UPDATED**: Screenshots in `docs/images/` — Reflect new UI with pagination and unified chrome

### Key Design Decisions
| Decision | Why |
|---|---|
| Dual loading indicators (panel vs badge) | Full progress panel for initial loads; subtle polling badge for background refreshes — clear state transitions |
| `fetchWithProgress` with ReadableStream | Byte-level progress tracking via `response.body.getReader()` — better UX than spinner for large payloads |
| Shared `DashboardShell` + `AppPageChrome` | Unified header/nav/layout across all screens — consistent UX, easier maintenance, DRY |
| Pagination defaults: 10 (experiments/runs), 5 (configs) | Prevents DOM overload and cognitive fatigue; configs are more verbose so lower per-page count |
| Activity feed in LoadingFeedbackPanel | Shows fetch milestones (start → headers → chunks → complete) — helps debug slow loads |
| `initialLoadDone` flag per screen | Polling indicator only appears after first load completes — avoids visual noise during hydration |

### Acceptance Criteria
- [x] LoadingFeedbackPanel appears during initial loads on all three screens
- [x] PollingIndicator shows during background polls (after initial load)
- [x] Pagination works on ExperimentsScreen (10 items/page)
- [x] Pagination works on ExperimentDetailScreen runs table (10 runs/page)
- [x] Pagination works on SearchExplorerScreen configs (5/page)
- [x] Re-query progress feedback in SearchExplorer when changing query filter
- [x] Unified header/navigation via DashboardShell
- [x] Page titles and back buttons via AppPageChrome
- [x] Screenshots updated to reflect new UI
- [x] Verification checklist created with manual test cases

### Follow-up Enhancements (2026-05-18)

**Extracted reusable progress component** for consistency:
- **NEW**: `frontend/src/components/ExperimentProgressCard.tsx` — Circular progress indicator (default/compact variants)
- **EDIT**: `frontend/src/components/ExperimentDetailScreen.tsx` — Uses `ExperimentProgressCard` (removed inline `ProgressRing`)
- **UPDATED**: Documentation to clarify two progress patterns:
  - `LoadingFeedbackPanel` → Network/API loading (byte-level progress)
  - `ExperimentProgressCard` → Experiment execution (run completion)

**Rationale**: Inline progress visualization in detail screen duplicated logic; extracting to component enables reuse across screens and maintains visual consistency.

---

## Slice 9: Experiment Deletion with Confirmation ✅

**Status**: ✅ COMPLETE | **Started**: 2026-05-19 | **Completed**: 2026-05-19 | **Target**: ~1 h

### Goal
Implement comprehensive experiment deletion with confirmation flows and cascading cleanup across CLI, server, and dashboard.

### What Changed
- **NEW**: `frontend/src/components/ConfirmDeleteModal.tsx` — Confirmation modal with experiment details, warning UI, and deletion statistics display
- **NEW**: `server/api/experiments_shared.py` — Shared delete helpers with cascade deletion logic across all collections
- **EDIT**: `server/api/experiments.py` — Added `DELETE /experiments/{id}` endpoint with `force` query parameter, validation against running experiments
- **EDIT**: `cli/main.py` — Added `delete` command with interactive confirmation prompt and `--force` flag
- **EDIT**: `cli/api_client.py` — Added `delete_experiment()` method for DELETE API calls
- **EDIT**: `frontend/src/components/ExperimentsScreen.tsx` — Added delete button in Actions column, integrated ConfirmDeleteModal, disabled for running experiments
- **EDIT**: `frontend/src/components/ExperimentDetailScreen.tsx` — Added delete button in header actions, integrated ConfirmDeleteModal
- **EDIT**: `frontend/src/services/apiClient.ts` — Added `deleteExperiment()` method with query string support
- **EDIT**: `frontend/src/types/index.ts` — Added `DeleteExperimentResponse` type for deletion statistics
- **EDIT**: `docs/user-guide/cli-reference.md` — Documented `delete` command with examples and use cases
- **EDIT**: `docs/user-guide/troubleshooting.md` — Replaced manual cleanup section with CLI/dashboard delete instructions
- **EDIT**: `CLAUDE.md` — Added delete command to CLI examples and updated key files list

### Key Design Decisions
| Decision | Why |
|---|---|
| Cascade delete across all collections | Prevents orphaned data; removes experiments, run_status, chunks, and results in one operation |
| Confirmation required by default | Deletion is permanent and destructive; explicit confirmation prevents accidental loss |
| `--force` flag for automation | Enables scripted deletion workflows without interactive prompts |
| Block deletion of running experiments | Prevents data corruption; users must cancel experiment first |
| Return deletion statistics | Provides transparency and verification of cascade cleanup |
| ConfirmDeleteModal shows experiment details | Users can verify they're deleting the correct experiment before confirming |
| Shared delete logic in `experiments_shared.py` | DRY principle; both API endpoint and future CLI/admin tools use same logic |

### Acceptance Criteria
- [x] CLI `delete` command with interactive confirmation prompt
- [x] CLI `--force` flag skips confirmation
- [x] DELETE endpoint returns deletion statistics (docs deleted per collection)
- [x] Running experiments cannot be deleted (API returns 400 error)
- [x] Dashboard delete buttons in experiments list and detail screen
- [x] ConfirmDeleteModal shows experiment details and deletion warning
- [x] Delete button disabled for running experiments with tooltip
- [x] Success toast shows deletion statistics
- [x] All pre-commit hooks pass (ruff, mypy, eslint, repo lint, tsc, build); pre-push runs `quality-gates.sh --quick` when hooks installed
- [x] Documentation updated (CLI reference, troubleshooting guide)

### Testing Notes
Manually verified:
- CLI delete with and without `--force`
- Dashboard delete from both list and detail screens
- Confirmation modal shows correct experiment details
- Running experiment deletion blocked with error message
- Deletion statistics displayed correctly in CLI and dashboard
- All associated data removed from MongoDB collections

---

## Vector DB Stats + Collapsible Rows + Boot Reconciliation ✅

**Status**: ✅ COMPLETE | **Started**: 2026-05-19 | **Completed**: 2026-05-19 | **Target**: ~1.5 h

### Goal
Surface MongoDB/Atlas storage footprint in the dashboard, improve experiments list UX with collapsible rows, and automatically fix experiments left `running` after server restart or crash.

### What Changed
- **NEW**: `server/core/atlas_storage.py` — Atlas Admin API cluster quota lookup + `dbStats` footprint; manual `MONGODB_STORAGE_LIMIT_MB` override
- **NEW**: `server/core/startup_reconciliation.py` — on boot, mark in-flight runs `interrupted` and recompute experiment status (`partial` / `complete` / `failed`)
- **NEW**: `server/utils/log_throttle.py` — throttle repetitive polling log lines
- **EDIT**: `server/api/experiments_shared.py` — `mongo_get_experiment_db_stats`, `mongo_get_vector_db_stats_grouped`
- **EDIT**: `server/api/experiments.py` — `GET /experiments/vector-db-stats`, `GET /experiments/{id}/db-stats`
- **EDIT**: `server/main.py` — call `reconcile_orphaned_experiments()` in lifespan
- **NEW**: `frontend/src/components/CollapsibleCard.tsx`, `VectorDbStatsPanel.tsx`, `ExperimentVectorDbStatsCard.tsx`
- **NEW**: `frontend/src/utils/experimentStatus.ts` — `summarizeExperimentRuns()` for outcome buckets
- **EDIT**: `frontend/src/components/ExperimentsScreen.tsx` — collapsible list rows, cluster stats panel, list→detail cache handoff
- **EDIT**: `frontend/src/components/ExperimentDetailScreen.tsx` — compact overview metrics (successful / failed / interrupted / not started), status-accurate outcome banners
- **EDIT**: `.env.example` — Atlas Admin API + storage limit vars

### Key Design Decisions
| Decision | Why |
|---|---|
| Reconcile orphans on every boot (not gated by `RECOVER_ON_BOOT`) | Status correction is safe and idempotent; retry remains opt-in via Slice 10 |
| `partial` when sweep incomplete | Distinguishes “41/90 complete + 48 never started” from green `complete` |
| Atlas quota via Admin API with manual fallback | M0 tier limits vary; hardcoded 512 MB was misleading |
| Outcome metrics from `run_status` phases | `run_count - failed_count` lied when runs never started |
| Collapsible state in `localStorage` | Per-panel persistence without server round-trips |

### Acceptance Criteria
- [x] `GET /experiments/vector-db-stats` returns grouped cluster stats
- [x] `GET /experiments/{id}/db-stats` returns per-experiment chunk/storage breakdown
- [x] Experiments list shows collapsible rows + vector DB stats panel
- [x] Experiment detail shows run-outcome buckets that sum to total runs
- [x] Partial experiments show “Sweep Incomplete” — not green success banner
- [x] Server boot reconciles stale `running` experiments to terminal status
- [x] Pre-commit hooks pass

---

## Voyage Sweep UX + Atlas Tier Specs ✅

**Status**: ✅ COMPLETE | **Started**: 2026-05-23 | **Completed**: 2026-05-23 | **Target**: ~1 h

### Goal
Fix misleading elapsed/duration times on long Voyage sweeps, surface Atlas cluster tier metadata in the dashboard, and polish experiment detail UX for running/paused sweeps.

### What Changed
- **EDIT**: `server/db/atlas.py` — PyMongo client `tz_aware=True`, `tzinfo=timezone.utc`
- **EDIT**: `server/core/orchestrator.py` — `started_at` set when first run begins; all timestamps timezone-aware UTC
- **EDIT**: `server/api/experiments_shared.py` — timezone-aware cancel/pause; db-stats includes `cluster_tier`, `cluster_tier_type`, `cluster_provider`, `cluster_region`
- **EDIT**: `server/core/atlas_storage.py` — `resolve_tier_specs()` from Atlas Admin API; shared-tier storage fallbacks (M0/M2/M5)
- **EDIT**: `frontend/src/components/ExperimentDetailScreen.tsx` — elapsed + ETA on progress card; duration shows — while running/paused; controls only in header
- **EDIT**: `frontend/src/components/VectorDbStatsPanel.tsx` — tier, cloud provider, region display
- **EDIT**: `.env.example` — Tier 1 rate limits as commented block above free-tier defaults
- **EDIT**: `configs/example-mongodb-voyage.yaml` — default to `voyage-3.5-lite` for storage-friendly sweeps

### Key Design Decisions
| Decision | Why |
|---|---|
| `datetime.now(timezone.utc)` everywhere | JSON `Z` suffix; browsers parse elapsed correctly |
| `started_at` on first run, not submission | ETA/duration reflect actual pipeline time |
| Atlas tier via `resolve_tier_specs()` | Reuses Admin API; RAM/vCPU/cost not exposed by Atlas |
| ETA with 1% margin | Small buffer on linear projection |
| Single control button location (header) | Removes duplicate pause/resume/cancel from progress and paused banners |

### Acceptance Criteria
- [x] Running experiment progress shows elapsed + ETA after first run completes
- [x] Duration stat shows — while running or paused
- [x] Vector DB stats panel shows tier/provider/region when Atlas API configured
- [x] New timestamps are timezone-aware UTC
- [x] Debug scripts removed (`test_atlas_api.py`, `test_time_calc.html`, one-off migration scripts)
- [x] Documentation updated

---

## Dashboard Polling + API Responsiveness ✅

**Status**: ✅ COMPLETE | **Started**: 2026-05-19 | **Completed**: 2026-05-23 | **Target**: ~1 h

### Goal
Keep the dashboard responsive during active sweeps and expensive Mongo aggregations; document per-screen poll intervals.

### What Changed
- **NEW**: `server/core/executors.py` — `SWEEP_EXECUTOR` + `HEAVY_READ_EXECUTOR` thread pools
- **EDIT**: `server/api/experiments.py` — sweeps and db-stats on dedicated pools; batched vector-db-stats aggregations
- **EDIT**: `frontend/src/constants.ts` — `EXPERIMENTS_POLL_MS` (2 s), `VECTOR_DB_STATS_POLL_MS` (60 s), `EXPLORE_POLL_MS` (15 s); fetch timeouts 30 s / 90 s
- **EDIT**: `frontend/src/components/ExperimentsScreen.tsx` — decoupled list vs stats polling
- **EDIT**: `frontend/src/components/SearchExplorerScreen.tsx` — 15 s explore poll while experiment running
- **EDIT**: `frontend/src/components/PollingIndicator.tsx` — `showDelayMs` / `minVisibleMs` to reduce sync-badge flicker
- **EDIT**: `docs/user-guide/dashboard-guide.md`, `docs/contributor-guide/architecture.md`

### Acceptance Criteria
- [x] Experiment list loads within a few seconds during an active sweep
- [x] Vector DB stats may lag but do not block the list
- [x] Search Explorer refreshes every 15 s while sweep is running
- [x] Dashboard guide polling table matches `constants.ts`

---

## Slice 6: Additional Chunkers + Retrieval Methods ✅

**Status**: ✅ COMPLETE | **Started**: 2026-05-17 | **Completed**: 2026-05-17 | **Target**: ~45 min

### Goal
Implement the 4 stubbed chunkers (fixed, token, sentence, semantic), add sparse/hybrid retrieval, create 5 new example configs covering every advertised feature.

### What Changed
- **IMPL**: `server/core/chunkers/fixed.py` — character-window slicing with configurable overlap
- **IMPL**: `server/core/chunkers/token.py` — LangChain `TokenTextSplitter` (cl100k_base encoding)
- **IMPL**: `server/core/chunkers/sentence.py` — NLTK `sent_tokenize` with character-budget grouping and overlap
- **IMPL**: `server/core/chunkers/semantic.py` — sentence-transformers cosine similarity grouping; chunk_size as hard cap; overlap ignored (semantic boundaries decide splits)
- **EDIT**: `server/core/retriever.py` — added `sparse_search()` (Atlas $search BM25), `hybrid_search()` (RRF merge, k=60), `search()` dispatcher, `_to_search_results()` helper
- **EDIT**: `server/core/orchestrator.py` — use `search()` dispatcher; conditionally embed query (only for dense/hybrid); import `RetrievalMethod`
- **NEW** *(later replaced — see config reorganisation below)*: `configs/example-voyage-all-models.yaml`, `example-chunking-methods.yaml`, `example-retrieval-methods.yaml`, `example-full-sweep-local.yaml`, `example-full-sweep-voyage.yaml`
- **EDIT**: `docs/user-guide/configuration.md` — Config File Index table, fixed hybrid description
- **EDIT**: `CLAUDE.local.md` — Atlas Full Text Search index setup
- **EDIT**: `README.md` — updated Quick Start config references

### Key Design Decisions
| Decision | Why |
|---|---|
| semantic chunker always uses `all-MiniLM-L6-v2` | Provider-agnostic chunking; keeps chunking independent of embedding config |
| semantic `overlap` param ignored | Semantic boundary is the split signal; character overlap would break topic coherence |
| RRF k=60 | Standard value from original RRF paper; softens rank-1 advantage |
| sparse/hybrid require Atlas Full Text Search index | Atlas $search is the BM25 engine; documented as manual prerequisite |
| `query_embedding` optional in `search()` dispatcher | Sparse doesn't need embedding; avoids wasted API call |

---

## Deferred

- Parallel sweep concurrency *(Slice 16 — [`docs/slices/SLICE-16-PARALLEL-SWEEP-RUNS.md`](SLICE-16-PARALLEL-SWEEP-RUNS.md))*
- All SHOULD/COULD slices
- Error handling (basic only in Slice 1)
- Logging structure (prints for now)
- Type safety everywhere (pragmatic shortcuts OK)

---

## Decision Log

| Date | Slice | Decision | Why |
|------|-------|----------|-----|
| 2026-07-09 | 32–38 | Dual-backend Protocol; migrate to Supabase/pgvector before Slice 22; defer 26/27/19 | Approved PRD + plan-modifier Add; rollback/A-B required; Mongo QoL low value until cutover |
| 2026-07-07 | 22 | Reclassified Slice 22 Should → Must | nw-review: Slice 22 delivers PCTO-critical score/reranking + best-config; both halves of SIE must be Must |
| 2026-07-07 | 30 | Added Slice 30 (Search Explorer UX) | Assessment found 4 untracked UX issues; bundled as Could/~2h |
| 2026-07-07 | 31 | Added Slice 31 (Experiment list filter) | Assessment found navigability gap at scale; Should/~2h |
| 2026-07-06 | 29 | Include padding in `_run_config_key()` tuple after overlap; default 0 for legacy runs | PR #48 added sweep dimension but ranked configs merged runs differing only by padding |
| 2026-06-29 | 21 | Officially close Slice 21; populate HANDOFF.md + update TRAIL.md | All acceptance criteria met; SIE_ENDPOINT rename + preflight + batching refinements landed post-completion |
| 2026-06-29 | 21 | Expand `example-mongodb-sie.yaml` to full chunking/retriever grid + 3 SIE models | Parity with local/voyage examples; bge-m3/stella-v5/splade-v3 are registry top tier |
| 2026-06-29 | 25B | `./start-services.sh --local` single-command switching; cloud URI validation skipped for local mode | Friction after Slice 25: long compose command, manual URI copy-paste, no "switch back" guidance |
| 2026-06-30 | 25/25B | `mongo_client_kwargs()` — TLS only for cloud Atlas URIs | Local `mongodb://` connections failed with SSL handshake when `tlsCAFile` was always set |
| 2026-06-30 | 25B | Compose `--profile` before `up`, not in `up` args | `start-services.sh --local` failed with `unknown flag: --profile` |
| 2026-06-29 | 25B | Consolidate `local-atlas.sh` + dual setup docs into `start-services.sh mongodb` + `mongodb-setup.md` | Single entry point for cloud/local; compose overlay replaced by env-var overrides in `docker-compose.yml` |
| 2026-06-29 | 25 | Implemented `mongodb-atlas-local` as opt-in local backend via `local-atlas` compose profile | Atlas M0 free-tier 500 MB limit hit; local Atlas image supports `$vectorSearch` + `$search` with identical syntax — zero code changes in retriever/indexes; `bootstrap_indexes()` auto-provisions all search indexes for local URI |
| 2026-06-29 | — | Investigating `mongodb/mongodb-atlas-local` Docker image as replacement for Atlas cloud | Atlas M0 free-tier 500 MB limit hit; local Atlas image supports `$vectorSearch` + `$search` with identical syntax — zero code changes required in retriever/indexes |
| 2026-05-27 | 20 | Scoped coverage 80% on four unit-tested modules | Baseline-first (83.6%); whole-repo 28% would force gate off or block merges |
| 2026-05-27 | 20 | pip-audit ML ignores via scripts/pip-audit.sh | torch/transformers CVEs need major sentence-transformers bump — separate slice |
| 2026-05-27 | 20 | Extend pre-commit, not Husky | Python repo already on pre-commit; avoids dual hook systems |
| 2026-05-27 | 20 | Branch chore/slice-20-toolchain-hardening from main | Independent of code-review-graph branch; focused PR |
| 2026-05-02 | 1 | pypdf for PDF parsing | Simpler than pdfminer.six, sufficient for text extraction |
| 2026-05-02 | 1 | voyage-3.5-lite only | Cheapest Voyage model, add others in Slice 7 |
| 2026-05-02 | 1 | RECURSIVE chunker only | Most common method, defer others to Slice 6 |
| 2026-05-02 | 1 | BackgroundTasks not Celery | No queue infrastructure needed for MVP |
| 2026-05-02 | 1 | Tailwind local install | No CDN per spec; postcss + autoprefixer for build pipeline |
| 2026-05-02 | 1 | Hand-mirror TS types | No codegen (typeshare/quicktype); 5 types + 3 enums manageable |
| 2026-05-02 | 1 | Hardcoded query in Slice 1 | Defer persona JSON parsing to Slice 5 for skateboard speed |
| 2026-05-02 | 1 | Atlas vector index manual | Pymongo doesn't support vector index creation; requires Atlas UI |
| 2026-05-02 | 1 | Placeholder chunkers | Create stub files with NotImplementedError to avoid import errors |
| 2026-05-02 | 7 | sentence-transformers for local models | Same package provides SentenceTransformer + CrossEncoder; no extra dep |
| 2026-05-02 | 7 | Explicit `provider` field in YAML config | Config drives routing end-to-end; eliminates runtime model-name lookup failures |
| 2026-05-02 | 7 | Provider passed through RunParams → orchestrator → embedder/reranker | Explicit routing; stale server code can't misroute to wrong provider |
| 2026-05-02 | 7 | Separate vector indexes per dimension | Atlas requires exact numDimensions match; vector_index_1024 + vector_index_384 |
| 2026-05-02 | 7 | all-MiniLM-L6-v2 as first local model | Well-known, fast, 384-dim, proves the abstraction |
| 2026-05-02 | 7 | numpy<2 compatibility pin | torch compiled against NumPy 1.x ABI; 2.x breaks with _ARRAY_API errors |
| 2026-05-17 | 6 | semantic chunker always uses all-MiniLM-L6-v2 | Provider-agnostic chunking; chunking and embedding phases remain independent |
| 2026-05-17 | 6 | RRF k=60 for hybrid retrieval | Standard value from original RRF paper; robust default, smooths rank-1 outliers |
| 2026-05-17 | 6 | sparse/hybrid require text_search_index | Atlas $search is the BM25 engine; full-text + vector indexes can coexist on same collection |
| 2026-05-17 | 6 | query_embedding optional in search() dispatcher | Avoids embedding API call for sparse retrieval runs |
| 2026-05-17 | — | Reorganise configs: 1 file per DB×provider | Replaced 7 single-purpose example files with `example-mongodb-local.yaml` and `example-mongodb-voyage.yaml`; each covers all embedding models, all chunking methods, and all retrieval methods for that DB+provider |
| 2026-05-17 | — | Slice 16 spec for parallel sweep runs | Formalized deferred work: bounded in-process parallelism vs Celery; honor `execution.parallelism`; specs in [`docs/slices/SLICE-16-PARALLEL-SWEEP-RUNS.md`](SLICE-16-PARALLEL-SWEEP-RUNS.md) |
| 2026-05-17 | 10 | Slice 10 spec for run recovery | In-place retry for FAILED runs (`--include-interrupted` optional); reuse `run_id`; delete stale `chunks`/`results` for that run only; config from Mongo `experiments.config`; boot recovery scoped to INTERRUPTED only; spec in [`docs/slices/SLICE-10-RUN-RECOVERY.md`](SLICE-10-RUN-RECOVERY.md) |
| 2026-05-17 | 8 | Dual loading indicators (panel + polling badge) | Full LoadingFeedbackPanel for initial loads provides detailed progress; subtle PollingIndicator for background refreshes avoids visual noise |
| 2026-05-17 | 8 | fetchWithProgress with ReadableStream | Byte-level progress via `response.body.getReader()` enables real-time progress bars; better UX than spinners for large payloads |
| 2026-05-17 | 8 | Shared DashboardShell + AppPageChrome components | Unified header/nav/layout across all screens; DRY principle, consistent UX, easier to maintain |
| 2026-05-17 | 8 | Pagination defaults 10 (lists) / 5 (configs) | Prevents DOM overload and cognitive fatigue; configs more verbose so lower per-page count |
| 2026-05-17 | 8 | initialLoadDone flag per screen | Polling indicator only shows after first load completes; avoids visual confusion during hydration |
| 2026-05-18 | 8 | ExperimentProgressCard reusable component | Extracted circular progress pattern from detail screen; enables consistent progress visualization across screens; separates network progress (LoadingFeedbackPanel) from execution progress (ExperimentProgressCard) |
| 2026-05-19 | — | Boot orphan reconciliation always on | BackgroundTasks die on reload; Mongo `running` must be corrected without waiting for Slice 10 retry |
| 2026-05-19 | — | Run outcome buckets in dashboard | successful + failed + interrupted + not started must sum to `run_count`; fixes misleading partial UI |
| 2026-05-19 | — | Atlas storage quota via Admin API | Avoid hardcoded M0 512 MB; optional manual `MONGODB_STORAGE_LIMIT_MB` override |
| 2026-05-19 | — | Pause/resume cooperative sweep control | `_SweepControl` threading events; `resume_sweep()` skips completed param signatures; status `paused` non-terminal |
| 2026-05-19 | — | voyage-context-3 segment splitting | Contextualized API 32K window; tiktoken cl100k_base sizing; standard Voyage models unchanged (`embed()` path) |
| 2026-05-19 | — | Expanded Voyage model registry | voyage-4 series, domain models, voyage-context-3, voyage-3 legacy; `contextualized` flag drives embedder dispatch |
| 2026-05-23 | — | Timezone-aware UTC timestamps | Fix browser elapsed/duration misparse; PyMongo `tz_aware=True` |
| 2026-05-23 | — | `started_at` on first run | Exclude queue time from duration and ETA |
| 2026-05-23 | — | Atlas tier specs in db-stats | `resolve_tier_specs()` — instance size, provider, region; shared-tier storage fallback |
| 2026-05-23 | — | Progress elapsed + ETA | Linear estimate from completed runs; 1% margin |
| 2026-05-23 | — | Search index preflight before sweeps | Derive required indexes from config; check M0 3-index cluster quota; HTTP 422 / fail fast — no wasted embedding |
| 2026-05-23 | — | `indexes list\|reset` CLI | Inspect known vs unknown cluster-wide; drop unknown or rebuild chunks indexes |
| 2026-05-23 | — | Option A scoped logging | Unified `[rag-params-finder] [Scope] …` in server, CLI, dashboard dev console |
| 2026-05-23 | — | Dedicated sweep + heavy-read thread pools | Default executor starved `GET /experiments` during long sweeps and db-stats aggregations |
| 2026-05-23 | — | Decoupled dashboard poll intervals | List 2 s, vector DB stats 60 s, Search Explorer 15 s while running — constants in `frontend/src/constants.ts` |
| 2026-05-23 | — | Search Explorer `PollingIndicator` anti-jitter | `showDelayMs=600`, `minVisibleMs=1000` — badge no longer flickers on fast explore polls |
| 2026-05-23 | 18 | One retriever per run (corrected) | Each `retrievers` list entry is one sweep dimension; runs never chain retrievers. Reranker runs fetch dense candidates internally (implementation detail only). Supersedes prior "auto-prepend dense" / chaining decisions. |
| 2026-05-23 | 18 | Unified retriever configuration | Treat all retrieval strategies (dense/sparse/hybrid + rerankers) as unified `retrievers` list for sweep expansion |
| 2026-05-23 | 18 | Auto-migrate old retrieval config format | Pydantic `@model_validator` converts `methods` + `retrieval_provider`/`retrieval_model` to separate `retrievers` sweep entries |
| 2026-05-23 | 18 | Maintain old fields indefinitely | Keep `retrieval_method`, `retrieval_provider`, `retrieval_model` in DB — synthesized from single retriever for backward compat |
| 2026-05-23 | 19 | Slice 19 spec for storage quota guard | M0 hit 515/512 MB; writes blocked (cancel/delete deadlock); `dbStats` understated cluster usage; mirror search-index preflight pattern — spec in [`SLICE-19-STORAGE-QUOTA-GUARD.md`](SLICE-19-STORAGE-QUOTA-GUARD.md) |
| 2026-05-27 | 20 | Docs synced to toolchain + test reality | pytest count corrected (was 39); Kimchi on integration branch only; `quality-gates.sh` in interrupt recovery; CI/bandit/gitleaks documented |
| 2026-05-27 | 20 | Repo lint in CI + pre-commit | shellcheck (`scripts/*.sh`), actionlint, markdownlint; `scripts/repo-lint.sh`; pragmatic `.markdownlint.json`; CI `repo-lint` job (4 jobs total) |
| 2026-05-28 | — | Docs navigation (playgroup-style) | Root `QUICKSTART.md`; `docs/README.md` index; `PROGRESS.md` lives under `docs/slices/` beside slice specs |
| 2026-05-28 | 20 | Pre-push = fast gates (`--quick`) | `git push` → `pre-push-gates.sh` (repo lint, ruff, mypy, bandit, pytest, frontend verify, gitleaks); commit hook stays staged pre-commit only |
| 2026-06-27 | 21 | embedder_factory.py as single dispatch point | Factory pattern over Protocol/ABC (Decision #10); orchestrator never does provider if/elif; each provider module exports embed_docs_fn + embed_query_fn |
| 2026-06-27 | 21 | SIEClient per call (no module-level cache) | Module-level client cache caused test state leakage between test runs; per-call instantiation ensures isolation |
| 2026-06-27 | 21 | Minimal FastAPI app in sweep tests | Importing server.main chains into voyageai → torch → OpenMP abort in sandbox; sweep router mounted standalone avoids the crash |
| 2026-06-27 | 21 | SIE health endpoint is /healthz not /health | SIE Docker exposes /healthz; check_sie_health() and CLAUDE.md updated accordingly |
| 2026-05-27 | 14 | Docker Compose (AIE7-adapted) | 2-service stack (no local vector DB); host CLI; prod default + `docker-compose.dev.yml`; `/healthz` MongoDB ping; `hf_cache` volume |
| 2026-05-27 | 14 | Dev overlay vs Compose profiles | `docker-compose.dev.yml` merge (not named profiles) — avoids port conflicts between prod/dev frontends |
| 2026-05-27 | 20 | Pre-push (superseded 2026-05-28) | Was `pre-commit --all-files` on push — replaced by `quality-gates.sh --quick` for pytest + frontend verify |

---

## Blockers & Issues

| Slice | Issue | Severity | Status | Resolution |
|-------|-------|----------|--------|------------|
| 19 | Atlas M0 storage quota blocks all writes; cancel/delete deadlock when cluster full | 🟡 Workaround exists | 📋 Spec written | Delete **complete** experiments to free space; then cancel works. Force-delete + preflight planned in Slice 19. Incident: `example-mongodb-local` 60-run sweep + voyage experiment on one M0 cluster. |

**Severity**: 🔴 Blocker | 🟡 Workaround exists | 🟢 Minor

---

## Slice 21: SIE Skateboard ✅

**Status**: ✅ COMPLETE | **Started**: 2026-06-27 | **Completed**: 2026-06-27 | **Target**: ~4–6 h

### Goal
Integrate SIE (Superlinked Inference Engine) as a third embedding provider, add Aim experiment logging, and expose a new `POST /api/v1/sweep` endpoint for Tier 1 ranked sweeps. Corpus is supplied by the caller via the `corpus: list[str]` field; falls back to the topic string when empty.

### Acceptance Criteria
- [x] `POST /api/v1/sweep` returns ranked retrieval methods with scores
- [x] `GET /health` includes `sie` and `version` fields
- [x] SIE models (BGE-M3, Stella-v5, SPLADE-v3) registered in `model_registry.py`
- [x] `embedder_factory.py` dispatches voyage/local/sie without orchestrator if/elif
- [x] `SweepRequest.corpus` accepts caller-supplied chunks; falls back to topic string when empty
- [x] `aim_logger.py` logs run params to Aim (no-op on failure — non-fatal)
- [x] 58 tests pass, coverage ≥80% threshold
- [x] ruff: 0 errors, mypy: 0 errors, frontend: 0 errors

### Files Created / Modified
| File | Change |
|---|---|
| `server/core/sie_embedder.py` | NEW — SIE BGE-M3/Stella-v5 embedding functions |
| `server/core/aim_logger.py` | NEW — Aim experiment run logging wrapper (no-op on fail) |
| `server/core/embedder_factory.py` | NEW — Provider dispatch factory (voyage/local/sie) |
| `server/api/sweep.py` | NEW — `POST /api/v1/sweep` + health helper functions |
| `server/core/model_registry.py` | SIE models added (bge-m3, stella-v5, splade-v3) |
| `server/models/config.py` | `Provider` Literal extended with `sie` |
| `server/models/status.py` | `Provider` Literal extended with `sie` |
| `server/core/embedder.py` | Voyage functions renamed to `embed_*_voyage`; dispatch removed |
| `server/core/orchestrator.py` | Uses `embedder_factory.get_embedder()` + `AimLogger.log_run()` |
| `server/main.py` | Sweep router mounted + enhanced `/health` endpoint |
| `pyproject.toml` | Added `sie-sdk`, `aim` dependencies |
| `tests/test_sie_embedder.py` | NEW — 5 GWT tests |
| `tests/test_embedder_factory.py` | Rewritten — 6 GWT tests (sys.modules mocking) |
| `tests/test_sweep_endpoint.py` | NEW — 9 GWT tests (minimal FastAPI app) |
| `configs/example-mongodb-sie.yaml` | NEW — CLI full-pipeline SIE sweep (120 runs, bge-m3/stella-v5/splade-v3) |
| `tests/test_config_examples.py` | NEW — example YAML load/expand/index-plan validation |

---

## Forward Roadmap

| Slice | Goal | Priority | Est. |
|-------|------|----------|------|
| ~~6 — Additional chunkers~~ | ~~Implement fixed, token, sentence, semantic~~ | ~~Should~~ | ✅ Done |
| ~~8 — SPARSE/HYBRID retrieval~~ | ~~BM25 + hybrid RRF via Atlas FTS~~ | ~~Should~~ | ✅ Done (merged into Slice 6) |
| 9 — Search Explorer dashboard | Best-params card, ranked configs, per-query results view | Should | ~30 min |
| 10 — Run recovery | Spec: [`SLICE-10-RUN-RECOVERY.md`](SLICE-10-RUN-RECOVERY.md) — `recover` CLI + `POST /experiments/{id}/recover`; per-`run_id` scrub + retry (**FAILED** default; **INTERRUPTED** opt-in); **`RECOVER_ON_BOOT`** retries **INTERRUPTED** only *(not all FAILED)* | Could | ~1–2 h |
| 11 — Dashboard-triggered runs | Submit experiments from the React UI, not just CLI | Could | ~45 min |
| 28 — Results export | Spec: [`SLICE-28-RESULTS-EXPORT.md`](SLICE-28-RESULTS-EXPORT.md) — CSV/JSONL download; [#49](https://github.com/neomatrix369/rag-params-finder/issues/49) | **Must** | 📋 PLANNED — @cschanhniem (~1.5 h) |
| 32–38 — Supabase/pgvector | Dual-backend Protocol → Postgres cutover + ADR-004 — [`PRD`](../plan/PRD-supabase-pgvector-migration.md) | **Must** | 📋 PLANNED — core team next |
| 12 — SSE live updates | Replace 2 s polling with Server-Sent Events | Could | ~20 min |
| 13 — Experiment cleanup CLI | `rag-params-finder cleanup --older-than 30d` | Could | ~15 min |
| 19 — Storage quota guard | Atlas M0 guard — **📦 DEFERRED**; Postgres stats in Slice 36 | Should | deferred |
| 26 — Local MongoDB docs | **📦 DEFERRED** — re-scope after Postgres local path (37) | Should | deferred |
| 27 — MongoDB mode indicator | **📦 DEFERRED** — re-scope as storage-backend indicator | Should | deferred |
| ~~14 — Docker Compose~~ | ~~One-command local setup~~ | — | ✅ Delivered in Slice 14 |
| ~~15 — CI/CD~~ | ~~GitHub Actions~~ | — | ✅ Delivered in Slice 20 |
| 16 — Parallel sweep (`parallelism` > 1) | Bounded concurrent `_run_single` (+ optional Celery upgrade path); Atlas/Voyage-rate-limit aware | Should | ~2–4 h |
| 30 — Search Explorer UX fixes | Spec: [`SLICE-30-SEARCH-EXPLORER-UX.md`](SLICE-30-SEARCH-EXPLORER-UX.md) — tab switch latency, zero-score noise, BM25 score labels, VDB card default-expanded | Could | ~2 h |
| 31 — Experiment list filter | Spec: [`SLICE-31-EXPERIMENT-LIST-FILTER.md`](SLICE-31-EXPERIMENT-LIST-FILTER.md) — status dropdown + name/ID search above experiments table | Should | ~2 h |

---

## Release Cadence

**Current version**: v0.11.0 ([CHANGELOG.md](../../CHANGELOG.md))

**Versioning strategy**: [Semantic Versioning](https://semver.org/) with hybrid approach:
- **Minor** (0.x.0) — Major slice completion, new features, provider additions
- **Patch** (0.x.y) — Bug fixes, polish, documentation improvements, logging enhancements

**When to release**:
- ✅ **After slice completion** — When a numbered slice (10, 11, 16, 19, etc.) is marked ✅ COMPLETE
- ✅ **After significant features** — Multi-slice work like pause/resume, search index preflight
- ✅ **After polish sprints** — Dashboard UX improvements, scoped logging, etc.
- ❌ **Not for every commit** — Bundle related changes; release when value is deliverable

**Release workflow**:
```bash
# After marking slice complete in this file:
./scripts/release.sh minor    # For slice completion or new feature
./scripts/release.sh patch     # For bug fixes or polish

# The script will:
# 1. Bump version in pyproject.toml, frontend/package.json
# 2. Prompt for CHANGELOG.md update
# 3. Create annotated git tag with changelog excerpt
# 4. Optionally push and create GitHub release
```

**See**: [docs/contributor-guide/release-process.md](../contributor-guide/release-process.md) for complete workflow.

**Reminder**: Update CHANGELOG.md **during** development, not at release time. Move items from `## [Unreleased]` to the new version section when ready.

---

## Skill Execution Log

Tracks skill runs across slices and sessions. Appended automatically by `/verify-slice`, `/sync-docs`, `/update-pr`, and other skills. Read this first when resuming a session to know exactly where the slice stands.

| Date | Branch | Skill | Slice | Outcome | Notes |
|---|---|---|---|---|---|
| 2026-07-06 | slice/29-padding-propagation | /update-pr | Slice 29 | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/63 — rebased docs footprint; PR already current; prerequisites: bypassed (no /verify-slice, no /sync-docs) |
| 2026-07-06 | slice/29-padding-propagation | /update-pr | Slice 29 | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/63 — docs footprint commit + PR refresh; prerequisites: bypassed (no /verify-slice, no /sync-docs) |
| 2026-07-06 | slice/29-padding-propagation | /update-pr | Slice 29 | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/63 — rebased footprint row; PR already current; prerequisites: bypassed (no /verify-slice, no /sync-docs) |
| 2026-07-06 | slice/29-padding-propagation | /update-pr | Slice 29 | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/63 — gate-cache gitignore + skill footprints committed; prerequisites: bypassed (no /verify-slice, no /sync-docs) |
| 2026-07-06 | slice/29-padding-propagation | /update-pr | Slice 29 | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/63 — run_id retrieval scoping + pathway tests; prerequisites: bypassed (no /verify-slice, no /sync-docs; pre-push gates passed) |
| 2026-07-06 | slice/29-padding-propagation | /update-pr | Slice 29 | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/63 — Atlas Local volume fix + padding propagation; prerequisites: bypassed (quality-gates --quick passed in session) |
| 2026-07-07 | main | /sync-docs | plan review + nw-review | STAGED | T1-2: PROGRESS.md (Slices 30/31 added, Slice 22 Must, header updated, decision log); DECISIONS.md rows 37-38 (reclassification + AC rewrite); TRAIL.md Slice 22 Must; SLICE-30 ACs rewritten (behavioral only) |
| 2026-07-06 | main | plan sync | Slice 28 status | STAGED | PLANNED (not immediate); active work 22; planning on main via PR #55/#59 |
| 2026-07-06 | main | plan sync | prereq clearance | STAGED | HANDOFF + PROGRESS + slice Before-Checks; #47/#48/#59 merged |
| 2026-07-05 | docs/plan-gap-analysis-jul4 | /update-pr | plan gap analysis | MERGED | https://github.com/neomatrix369/rag-params-finder/pull/59 — footprint backfilled post-merge (commit landed after merge) |
| 2026-07-05 | fix/pr47-review-suggestions | /update-pr | PR #61 follow-up | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/61 — CI all green, mergeState CLEAN; prerequisites: bypassed (no /verify-slice) |
| 2026-07-05 | fix/pr47-review-suggestions | /update-pr | PR #61 follow-up | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/61 — merge commit + conflict resolution reflected; prerequisites: bypassed (no /verify-slice; quality-gates --quick passed in session) |
| 2026-07-05 | fix/pr47-review-suggestions | /sync-docs | PR #61 follow-up | STAGED | T1-2: CHANGELOG (#47/#48/#60/#61), CLAUDE+development+docs/README (97 tests); configuration.md already on branch; no slice status changes |
| 2026-07-01 | chore/toolchain-prettier-security-scan | /update-pr | Toolchain extension | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/46 — main sync, uv.lock + pip-audit fixes; prerequisites: bypassed (no /verify-slice on branch) |
| 2026-07-01 | slice/21-25b-sie-and-atlas-local | /sync-docs | 21/24/25/25B audit | STAGED | Full branch audit: CHANGELOG ✅, CLAUDE ✅, development.md + docs/README (78 tests), configuration.md SIE callout, QUICKSTART --local, README path row, HANDOFF 25B fix; user-guide mongodb/sie already current |
| 2026-07-01 | slice/21-25b-sie-and-atlas-local | /update-pr | 21/24/25/25B | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/52 — SIE screenshot crop + maxkb 1200; prerequisites: met (verify-slice COMPLETE 2026-06-30) |
| 2026-07-01 | slice/21-25b-sie-and-atlas-local | /update-pr | 21/24/25/25B | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/52 — screenshots + Atlas Local docs + pre-commit limit; prerequisites: met (verify-slice COMPLETE 2026-06-30) |
| 2026-07-01 | slice/21-25b-sie-and-atlas-local | /update-pr | 21/24/25/25B | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/52 — prerequisites: met (verify-slice COMPLETE 2026-06-30) |
| 2026-06-30 | slice/21-25b-sie-and-atlas-local | /verify-slice | 21/24/25/25B closing tests | COMPLETE | 78 pytest pass; local+cloud smoke OK; SIE sweep 200; fixes: compose profile + local TLS; docs synced |
| 2026-06-29 | slice/21-25b-sie-and-atlas-local | /verify-slice | Unified MongoDB Entry Points | COMPLETE | 12/12 criteria; quick gates 75 pass; CLI/compose smoke OK; docs current |
| 2026-06-29 | slice/21-25b-sie-and-atlas-local | /update-pr | 21/24/25/25B | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/52 — prerequisites: met (verify-slice COMPLETE) |
| 2026-06-29 | slice/21-25b-sie-and-atlas-local | /verify-slice | Unified MongoDB Entry Points | PARTIAL | 12/12 plan criteria; ruff/mypy/pytest 75 pass; smoke OK; PROGRESS 25B row + CHANGELOG stale |
| 2026-06-29 | slice/21-25b-sie-and-atlas-local | /sync-docs | Unified MongoDB Entry Points | STAGED | PROGRESS.md ✅, CHANGELOG ✅, CLAUDE ⏭, user-guide ⏭ |

**Outcome values**: `COMPLETE` · `PARTIAL` · `STAGED` · `PUSHED` · `FAILED` · `SKIPPED`

---

## Interrupt Recovery Checklist

Use this when resuming a session mid-slice:

```
[ ] Read the Skill Execution Log above — last skill run tells you where to resume
[ ] Read docs/slices/PROGRESS.md — note current slice and last known state
[ ] Git hooks installed: bash scripts/install-git-hooks.sh (once per machine)
[ ] Run quality gates to confirm no regressions:
      ./scripts/quality-gates.sh          # full CI mirror before PR
      # git push runs ./scripts/pre-push-gates.sh (--quick) when hooks installed
[ ] Check git status — any uncommitted changes?
[ ] Read the current slice spec in docs/slices/SLICE-XX-*.md
[ ] Resume from the last incomplete acceptance criterion
[ ] Verify after every change before moving to the next criterion
```
