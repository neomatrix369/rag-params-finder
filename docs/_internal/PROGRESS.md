# rag-params-finder — Build Progress

**Last Updated**: 2026-05-05
**Current**: Slices 1–5, 7 ✅ COMPLETE (verified end-to-end) | Next: Slice 6 📋 PLANNED (other chunkers)

---

## Quick Status

| Slice | Status | Time Target | Notes |
|-------|--------|-------------|-------|
| 1 — Skateboard | ✅ COMPLETE | ~75 min | End-to-end pipeline verified |
| 2 — Rerank | ✅ COMPLETE | ~10 min | Voyage + local reranking |
| 3 — Sweep expansion | ✅ COMPLETE | ~15 min | Cartesian product of runs ⭐ CORE FEATURE |
| 4 — Live status + polling | ✅ COMPLETE | ~15 min | Phase tracking, CLI --watch, detail screen |
| 5 — Multiple queries from persona JSON | ✅ COMPLETE | ~10 min | Loop over persona questions |
| 6 — Additional chunkers | 📋 PLANNED | ~30 min | fixed, token, sentence, semantic (stubs exist) |
| 7 — Free/local embedding + reranking | ✅ COMPLETE | ~15 min | sentence-transformers, no API key needed |

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
| Sequential runs (not parallel) | `parallelism: 1` default; parallel execution deferred to avoid complexity |
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

## Deferred

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
| 6 — Additional chunkers | Implement fixed, token, sentence, semantic (stubs already exist) | Should | ~30 min |
| 8 — SPARSE/HYBRID retrieval | BM25 + hybrid weighted search via Atlas FTS | Should | ~25 min |
| 9 — Search Explorer dashboard | Best-params card, ranked configs, per-query results view | Should | ~30 min |
| 10 — Run recovery | Auto-retry interrupted runs on server boot; `rag-params-finder recover` CLI command | Could | ~30 min |
| 11 — Dashboard-triggered runs | Submit experiments from the React UI, not just CLI | Could | ~45 min |
| 12 — SSE live updates | Replace 2 s polling with Server-Sent Events | Could | ~20 min |
| 13 — Experiment cleanup CLI | `rag-params-finder cleanup --older-than 30d` | Could | ~15 min |
| 14 — Docker Compose | One-command local setup | Won't (now) | ~30 min |
| 15 — CI/CD | GitHub Actions: ruff, mypy, pytest, npm lint/build | Should | ~20 min |

---

## Interrupt Recovery Checklist

Use this when resuming a session mid-slice:

```
[ ] Read docs/_internal/PROGRESS.md — note current slice and last known state
[ ] Run quality gates to confirm no regressions:
      backend: uv run ruff check . && uv run mypy server/ cli/ && uv run pytest
      frontend: npm run typecheck && npm run build
[ ] Check git status — any uncommitted changes?
[ ] Read the current slice spec in docs/slices/SLICE-XX-*.md
[ ] Resume from the last incomplete acceptance criterion
[ ] Verify after every change before moving to the next criterion
```
