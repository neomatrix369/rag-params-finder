# rag-params-finder — Build Progress

**Last Updated**: 2026-05-23 (Kimchi embedding provider + dashboard polling intervals + thread-pool architecture docs)
**Current**: Slices 1–9 ✅ COMPLETE | Vector DB stats + collapsible rows + boot reconciliation ✅ COMPLETE | Pause/resume + expanded Voyage catalog ✅ COMPLETE | Voyage sweep UX polish ✅ COMPLETE | Search index preflight + indexes CLI ✅ COMPLETE | Dashboard polling + API responsiveness ✅ COMPLETE | Kimchi embedding provider ✅ COMPLETE | Next: Slice 10 📋 PLANNED (failed-run recovery retry) · Slice 11 📋 PLANNED (Search Explorer enhancements) · Slice 16 📋 PLANNED (honor `parallelism`)

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
| — — Kimchi embedding provider | ✅ COMPLETE | ~2 h | CAST OpenAI-compatible embeddings; runtime dimensions; 4-model example sweep; focused pytest suite |
| 10 — Run recovery (retry) | 📋 PLANNED | ~1–2 h | Retry FAILED `(± INTERRUPTED)` runs in-place; boot **reconciliation** done; pause/resume covers not-yet-started combos; **retry** not yet — see [`SLICE-10-RUN-RECOVERY.md`](../slices/SLICE-10-RUN-RECOVERY.md) |
| 11 — Search Explorer enhancements | 📋 PLANNED | ~1 h | Better visualization, export results, query filtering improvements |
| 16 — Parallel sweep execution | 📋 PLANNED | ~2–4 h | Bounded concurrent `_run_single`; see [`SLICE-16-PARALLEL-SWEEP-RUNS.md`](../slices/SLICE-16-PARALLEL-SWEEP-RUNS.md) |

**Legend**: 📋 PLANNED | 🔨 IN PROGRESS | ✅ COMPLETE

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
- docs/PROGRESS.md, docs/ARCHITECTURE.md, docs/slices/SLICE-01-SKATEBOARD.md

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
| Sequential runs (not parallel) | `parallelism` stored on experiments but orchestrator ignores it pending [Slice 16](../slices/SLICE-16-PARALLEL-SWEEP-RUNS.md) |
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
- [x] All pre-commit hooks pass (ruff, mypy, tsc, build)
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

## Kimchi Embedding Provider ✅

**Status**: ✅ COMPLETE | **Started**: 2026-05-13 | **Completed**: 2026-05-20 | **Target**: ~2 h

### Goal
Add Kimchi (CAST.ai OpenAI-compatible) as a third embedding provider with runtime-detected dimensions and a focused example sweep.

### What Changed
- **NEW**: `server/core/kimchi_embedder.py` — OpenAI-compatible `/v1/embeddings`; CAST payload shape; full `provider/model` IDs passed through
- **EDIT**: `server/core/model_registry.py` — Kimchi catalog with `dimensions: None` + `contextualized` flags
- **EDIT**: `server/core/embedder.py`, `server/core/retriever.py`, `server/db/indexes.py` — routing + dynamic `vector_index_<dimension>`
- **NEW**: `configs/example-kimchi.yaml` — 4 active OpenAI-family models; additional IDs parked until account verification
- **NEW**: `tests/test_kimchi_provider.py` — validation, payload, runtime index selection, db-stats dimension sampling
- **EDIT**: `server/api/experiments_shared.py` — sample stored chunk embeddings when registry `dimensions` is `None` (Kimchi vector DB stats)
- **EDIT**: user + contributor docs — Kimchi setup in `getting-started.md`, `cloud-setup.md`, `configuration.md`, `troubleshooting.md`; slice spec [`SLICE-16-KIMCHI-PROVIDER.md`](../slices/SLICE-16-KIMCHI-PROVIDER.md)

### Key Design Decisions
| Decision | Why |
|---|---|
| Prefixed model IDs (`openai/text-embedding-3-large`) | Avoid collisions across upstream families behind one gateway |
| Runtime dimensions | Catalog spans multiple embedding sizes; Atlas index must match actual vectors |
| Embeddings-only (`rerank_model: null`) | No invented Kimchi rerank semantics |
| Park unverified models in YAML | Registry lists many IDs; example sweep only runs models confirmed on the CAST account |
| Sample chunk embedding for db-stats | Registry has no fixed dimension; storage estimates need one stored vector per model |

### Acceptance Criteria
- [x] `embedding.provider: kimchi` validates; secrets in `.env` only
- [x] `example-kimchi.yaml` runs 24 combos (4 models × 6 chunk param sets × dense)
- [x] Vector DB stats work for Kimchi experiments (no crash on `dimensions: None`)
- [x] `uv run pytest` — Kimchi-focused tests pass

---

## Dashboard Polling + API Responsiveness ✅

**Status**: ✅ COMPLETE | **Started**: 2026-05-19 | **Completed**: 2026-05-23 | **Target**: ~1 h

### Goal
Keep the dashboard responsive during active sweeps and expensive Mongo aggregations; document per-screen poll intervals.

### What Changed
- **NEW**: `server/core/executors.py` — `SWEEP_EXECUTOR` + `HEAVY_READ_EXECUTOR` thread pools
- **EDIT**: `server/api/experiments.py` — sweeps and db-stats on dedicated pools; batched vector-db-stats aggregations
- **EDIT**: `server/api/experiments_shared.py` — batched aggregations for vector-db-stats (3 pipeline queries vs per-experiment N+1)
- **EDIT**: `frontend/src/constants.ts` — `EXPERIMENTS_POLL_MS` (2 s), `VECTOR_DB_STATS_POLL_MS` (60 s), `EXPLORE_POLL_MS` (15 s); fetch timeouts 30 s / 90 s
- **EDIT**: `frontend/src/components/ExperimentsScreen.tsx` — decoupled list vs stats polling
- **EDIT**: `frontend/src/components/SearchExplorerScreen.tsx` — 15 s explore poll while experiment running
- **EDIT**: `frontend/src/components/PollingIndicator.tsx` — `showDelayMs` / `minVisibleMs` to reduce sync-badge flicker
- **EDIT**: `frontend/src/services/fetchWithProgress.ts`, `VectorDbStatsPanel.tsx` — decoupled list vs stats loading
- **EDIT**: `docs/user-guide/dashboard-guide.md`, `docs/contributor-guide/architecture.md`

### Acceptance Criteria
- [x] Experiment list loads within a few seconds during an active sweep
- [x] Vector DB stats may lag but do not block the list
- [x] Search Explorer refreshes every 15 s while sweep is running
- [x] Dashboard guide polling table matches `constants.ts`
- [x] Hung polls abort instead of leaving the UI stuck indefinitely
- [x] Troubleshooting documents starved-API and timeout behavior

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

- Parallel sweep concurrency *(Slice 16 — [`docs/slices/SLICE-16-PARALLEL-SWEEP-RUNS.md`](../slices/SLICE-16-PARALLEL-SWEEP-RUNS.md))*
- All SHOULD/COULD slices
- Error handling (basic only in Slice 1)
- Logging structure (prints for now)
- Type safety everywhere (pragmatic shortcuts OK)

---

## Decision Log

| Date | Slice | Decision | Why |
|------|-------|----------|-----|
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
| 2026-05-17 | — | Slice 16 spec for parallel sweep runs | Formalized deferred work: bounded in-process parallelism vs Celery; honor `execution.parallelism`; specs in [`docs/slices/SLICE-16-PARALLEL-SWEEP-RUNS.md`](../slices/SLICE-16-PARALLEL-SWEEP-RUNS.md) |
| 2026-05-17 | 10 | Slice 10 spec for run recovery | In-place retry for FAILED runs (`--include-interrupted` optional); reuse `run_id`; delete stale `chunks`/`results` for that run only; config from Mongo `experiments.config`; boot recovery scoped to INTERRUPTED only; spec in [`docs/slices/SLICE-10-RUN-RECOVERY.md`](../slices/SLICE-10-RUN-RECOVERY.md) |
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
| 2026-05-13 | — | Kimchi model IDs are prefixed by upstream family | Avoid collisions across models with similar names |
| 2026-05-13 | — | Kimchi dimensions are runtime-detected | Hosted catalog spans multiple upstream embedding families |
| 2026-05-13 | — | Kimchi is embeddings-only | Avoid unsupported reranker semantics; set `rerank_model: null` |
| 2026-05-13 | — | Dynamic indexes use `vector_index_<dimension>` | Atlas indexes require exact embedding dimensionality |
| 2026-05-19 | — | Dedicated sweep + heavy-read thread pools | Default executor starved `GET /experiments` during long sweeps and db-stats aggregations |
| 2026-05-19 | — | Batched vector-db-stats aggregations | Replaced per-experiment Mongo round-trips with three dashboard-wide pipelines |
| 2026-05-20 | — | Kimchi db-stats samples stored embeddings | Registry `dimensions: None` cannot estimate storage until chunks exist |
| 2026-05-20 | — | Kimchi passes full LiteLLM model ID to CAST | Stripping the provider prefix broke routing; payload matches CAST template |
| 2026-05-20 | — | Parked Kimchi models in example YAML | Example sweep runs only account-verified models; registry retains full catalog |

---

## Blockers & Issues

| Slice | Issue | Severity | Status | Resolution |
|-------|-------|----------|--------|------------|
| - | None yet | - | - | - |

**Severity**: 🔴 Blocker | 🟡 Workaround exists | 🟢 Minor

---

## Forward Roadmap

| Slice | Goal | Priority | Est. |
|-------|------|----------|------|
| ~~6 — Additional chunkers~~ | ~~Implement fixed, token, sentence, semantic~~ | ~~Should~~ | ✅ Done |
| ~~8 — SPARSE/HYBRID retrieval~~ | ~~BM25 + hybrid RRF via Atlas FTS~~ | ~~Should~~ | ✅ Done (merged into Slice 6) |
| 9 — Search Explorer dashboard | Best-params card, ranked configs, per-query results view | Should | ~30 min |
| 10 — Run recovery | Spec: [`SLICE-10-RUN-RECOVERY.md`](../slices/SLICE-10-RUN-RECOVERY.md) — `recover` CLI + `POST /experiments/{id}/recover`; per-`run_id` scrub + retry (**FAILED** default; **INTERRUPTED** opt-in); **`RECOVER_ON_BOOT`** retries **INTERRUPTED** only *(not all FAILED)* | Could | ~1–2 h |
| 11 — Dashboard-triggered runs | Submit experiments from the React UI, not just CLI | Could | ~45 min |
| 12 — SSE live updates | Replace 2 s polling with Server-Sent Events | Could | ~20 min |
| 13 — Experiment cleanup CLI | `rag-params-finder cleanup --older-than 30d` | Could | ~15 min |
| 14 — Docker Compose | One-command local setup | Won't (now) | ~30 min |
| 15 — CI/CD | GitHub Actions: ruff, mypy, pytest, npm lint/build | Should | ~20 min |
| 16 — Parallel sweep (`parallelism` > 1) | Bounded concurrent `_run_single` (+ optional Celery upgrade path); Atlas/Voyage-rate-limit aware | Should | ~2–4 h |

---

## Interrupt Recovery Checklist

Use this when resuming a session mid-slice:

```
[ ] Read docs/_internal/PROGRESS.md — note current slice and last known state
[ ] Run quality gates to confirm no regressions:
      backend: uv run ruff check . && uv run mypy server/ cli/ && uv run pytest --tb=short -q
      frontend: npm run typecheck && npm run build
[ ] Check git status — any uncommitted changes?
[ ] Read the current slice spec in docs/slices/SLICE-XX-*.md
[ ] Resume from the last incomplete acceptance criterion
[ ] Verify after every change before moving to the next criterion
```
