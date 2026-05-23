# Architecture

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?logo=pydantic&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB_Atlas-47A248?logo=mongodb&logoColor=white)
![React](https://img.shields.io/badge/React_19-61DAFB?logo=react&logoColor=white)
![Vite](https://img.shields.io/badge/Vite_6-646CFF?logo=vite&logoColor=white)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-embeddings_%26_reranking-FF6B6B)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-FF9D00?logo=huggingface&logoColor=white)

System design, data flow, module structure, and design decisions for `rag-params-finder`.

---

## 🏗️ System Overview

`rag-params-finder` is a **two-process system** for RAG parameter sweep experimentation:

1. **Python CLI** (thin client) — submits experiment configs to the server
2. **FastAPI Server** (engine) — orchestrates the full pipeline end-to-end
3. **React Dashboard** — visualization, sweep controls (pause/resume/cancel/delete), and results exploration

The CLI submits configs; the Dashboard observes progress and controls active sweeps. All pipeline business logic lives in the server.

---

## 🔀 Data Flow

```
CLI (submit YAML)
      │
      │  POST /experiments
      ▼
FastAPI Server
      │
      │  BackgroundTask per experiment
      ▼
┌──────────────────────────────────────────┐
│  Pipeline (one run per config combination)│
│                                          │
│  PDF/TXT/MD/CSV → Chunk → Embed          │
│       → Atlas write → Query → Rerank     │
│       → Store results                    │
└──────────────┬───────────────────────────┘
               │
               ▼
         MongoDB Atlas
         ┌────────────┐
         │ chunks     │  ← embeddings + vector index
         │ experiments│
         │ run_status │  ← phase tracking
         │ results    │
         └────────────┘
               │
               │  polling (every 2s)
               ▼
       React Dashboard
```

---

## 🧱 Technology Stack

### Backend (Server + CLI)

| Library | Purpose |
|---|---|
| FastAPI | REST API server |
| Python 3.12 | Language runtime |
| Voyage AI SDK | Embeddings + reranking (hosted) |
| sentence-transformers | Local embeddings + reranking (offline) |
| MongoDB Atlas / PyMongo | Vector storage + search |
| LangChain text splitters | Recursive, fixed, token chunking |
| NLTK | Sentence chunking |
| tiktoken | Token-based chunking |
| pypdf | PDF text extraction |
| Typer | CLI framework |
| Rich | CLI output formatting |
| pydantic-settings | Centralized settings from `.env` |

### Frontend (Dashboard)

| Library | Purpose |
|---|---|
| React 19 | UI framework |
| TypeScript 5.8 | Type safety |
| Vite 6 | Build tool |
| Tailwind CSS | Styling (locally installed, not CDN) |

---

## 📁 Module Map

```
rag-params-finder/
├── server/
│   ├── main.py              # FastAPI app entry; lifespan: indexes + orphan reconciliation
│   ├── settings.py          # Centralized pydantic-settings config
│   ├── api/
│   │   ├── experiments.py   # CRUD, explore, db-stats, pause, resume, cancel, delete
│   │   ├── experiments_shared.py  # Mongo helpers incl. db-stats aggregation
│   │   └── runs.py          # GET /runs/{id}/status
│   ├── core/
│   │   ├── orchestrator.py  # run_sweep(), resume_sweep(), run_single() pipeline; index preflight
│   │   ├── executors.py     # SWEEP_EXECUTOR + HEAVY_READ_EXECUTOR (isolate long work from API pool)
│   │   ├── search_index_plan.py  # required indexes from config; capacity assessment (pure)
│   │   ├── search_index_guard.py # cluster snapshot + ensure retry; SearchIndexMismatchError
│   │   ├── startup_reconciliation.py  # fix stale running experiments on boot
│   │   ├── atlas_storage.py # Atlas Admin API quota + dbStats footprint
│   │   ├── pdf_parser.py    # pypdf text extraction
│   │   ├── query_loader.py  # persona JSON → Query dataclass list
│   │   ├── model_registry.py  # embedding + reranking model catalog
│   │   ├── embedder.py      # Voyage embed(); voyage-context-3 → contextualized_embed + segment split
│   │   ├── local_embedder.py  # sentence-transformers embedding (lazy-load, cached)
│   │   ├── reranker.py      # Voyage reranking client
│   │   ├── local_reranker.py  # CrossEncoder reranking (lazy-load, cached)
│   │   ├── retriever.py     # Atlas Vector Search (dense/sparse/hybrid)
│   │   ├── results_analyzer.py  # aggregates scores, min-max normalization
│   │   └── chunkers/
│   │       ├── recursive.py # LangChain RecursiveCharacterTextSplitter
│   │       ├── fixed.py     # fixed-size character windows
│   │       ├── token.py     # tiktoken-based
│   │       ├── sentence.py  # NLTK sentence tokenizer
│   │       └── semantic.py  # embedding-similarity sentence grouping
│   ├── models/
│   │   ├── enums.py         # ChunkingMethod, RetrievalMethod, Phase
│   │   ├── config.py        # Pydantic experiment config + provider validators
│   │   ├── status.py        # RunStatus model
│   │   └── results.py       # QueryResult, SearchResult, Chunk
│   └── db/
│       ├── atlas.py         # MongoDB connection singleton
│       └── indexes.py       # collection + search index creation; list_cluster_search_indexes()
├── cli/
│   ├── main.py              # Typer app (run, cancel, pause, resume, delete, indexes, version)
│   ├── indexes_cmd.py       # indexes list | reset subcommands
│   ├── config_loader.py     # YAML parser + model registry validation
│   └── api_client.py        # HTTP client to server
├── tests/
│   ├── test_search_index_plan.py   # index requirement + capacity scenarios
│   └── test_search_index_guard.py  # preflight guard (mocked I/O)
└── frontend/src/
    ├── App.tsx              # root component (screen routing)
    ├── components/
    │   ├── DashboardShell.tsx          # shared dashboard shell (header, nav)
    │   ├── AppPageChrome.tsx           # shared page chrome wrapper
    │   ├── LoadingFeedbackPanel.tsx    # network loading progress (byte-level, activity feed)
    │   ├── ExperimentProgressCard.tsx  # experiment progress card (circular indicator, reusable)
    │   ├── PollingIndicator.tsx        # subtle "Syncing..." indicator during polls
    │   ├── ConfirmDeleteModal.tsx      # delete confirmation modal with experiment details
    │   ├── ExperimentControlButtons.tsx  # pause / resume / cancel on detail screen
    │   ├── CollapsibleCard.tsx         # reusable collapsible section (localStorage state)
    │   ├── VectorDbStatsPanel.tsx      # cluster-grouped storage stats (experiments list)
    │   ├── ExperimentVectorDbStatsCard.tsx  # per-experiment db-stats on detail screen
    │   ├── ExperimentsScreen.tsx       # list view (collapsible rows, vector DB stats, delete)
    │   ├── ExperimentDetailScreen.tsx  # overview metrics, outcome banners, runs table
    │   └── SearchExplorerScreen.tsx    # results analysis (ranked configs, per-query, paginated)
    ├── services/
    │   ├── apiClient.ts       # fetch wrapper (all server API calls)
    │   └── fetchWithProgress.ts  # streamed fetch with byte-level progress tracking
    ├── utils/
    │   ├── experimentStatus.ts   # terminal/running helpers + summarizeExperimentRuns()
    │   └── experimentDbStats.ts  # db-stats response normalizers
    └── types/index.ts         # hand-mirrored TypeScript types from Python models
```

---

## ⚙️ Pipeline Phases

Each run progresses through phases tracked in the `run_status` collection:

| Phase | What happens |
|---|---|
| `QUEUED` | Run created, waiting to start |
| `PARSING` | Source files (PDF/TXT/MD/CSV) → plain text |
| `CHUNKING` | Text → chunks (per the configured method and params) |
| `EMBEDDING` | Chunks → embedding vectors (Voyage API or local model) |
| `STORING` | Write chunks + embeddings to Atlas |
| `QUERYING` | Execute all test queries against the vector index |
| `RERANKING` | Cross-encoder reranks top-K initial results to top-K final |
| `COMPLETE` / `FAILED` / `INTERRUPTED` | Terminal state |

---

## 🤖 Provider System

Two independent provider settings in each experiment config:

**Embedding provider** (`embedding.provider`):
- `local` → `server/core/local_embedder.py` → sentence-transformers `all-MiniLM-L6-v2` (384-dim)
- `voyage` → `server/core/embedder.py` → Voyage AI API (1024-dim); `voyage-context-3` uses `contextualized_embed()` with per-document segment splitting (32K-token window)

**Retrieval configuration** (`retrieval.retrievers`):
- Unified list of retrievers (traditional search + rerankers)
- Traditional: `{type: dense|sparse|hybrid}` — no provider/model needed
- Rerankers: `{type: reranker|cross_encoder, provider: local|voyage, model: ...}`
  - `provider: local` → `server/core/local_reranker.py` → CrossEncoder `cross-encoder/ms-marco-MiniLM-L-6-v2`
  - `provider: voyage` → `server/core/reranker.py` → Voyage AI rerank API
- Old format (`methods` + `rerank_provider`/`rerank_model`) auto-migrates to `retrievers` via Pydantic validator

Provider flows explicitly through `RunParams` → `orchestrator` → embedder/reranker. The `model_registry.py` validates that model names match the declared provider at config load time.

---

## 🗄️ MongoDB Atlas Collections

| Collection | Purpose | Key Indexes |
|---|---|---|
| `chunks` | Text chunks + embeddings | Vector index on `embedding` (384 or 1024-dim cosine) + filter fields |
| `experiments` | Experiment metadata + sweep config | `created_at`, `status` |
| `run_status` | Per-run phase tracking | `experiment_id`, `phase` |
| `results` | Per-query top-K results | `experiment_id`, `query_id` |

**Critical**: always filter vector search by `embedding_model` — vectors from different models have incompatible geometry and must never be mixed in the same search.

---

## 📐 Design Decisions

See `docs/adr/` for Architecture Decision Records:

- [ADR-001](../adr/ADR-001-two-process-architecture.md): Why CLI + Server (two-process architecture)
- [ADR-002](../adr/ADR-002-voyage-and-local-providers.md): Why dual embedding/reranking providers
- [ADR-003](../adr/ADR-003-mongodb-atlas-vector-store.md): Why MongoDB Atlas over Pinecone/Weaviate

**Key design choices not covered by ADRs**:

| Decision | Rationale |
|---|---|
| FastAPI `BackgroundTasks` (not Celery) | No queue infrastructure needed while sweep runs execute sequentially *(see [`SLICE-16`](../slices/SLICE-16-PARALLEL-SWEEP-RUNS.md) for honoring `parallelism > 1` and optional Celery path)* |
| Hand-mirrored TypeScript types | No codegen tooling (typeshare/quicktype); 5 types + 3 enums is manageable manually |
| Separate vector indexes per dimension | Atlas requires exact `numDimensions` — `vector_index_1024` (Voyage) and `vector_index_384` (local) coexist on the same collection |
| Lazy-load + cache for local models | First run downloads from HuggingFace; subsequent runs instant — avoids blocking server startup |
| `numpy<2` pinned | torch compiled against NumPy 1.x ABI; NumPy 2.x causes `_ARRAY_API not found` crashes |
| Shared `DashboardShell` + `AppPageChrome` components | Unified header, navigation, and page layout across all screens — consistent UX, easier maintenance |
| `fetchWithProgress` for streamed downloads | ReadableStream byte-level progress → visible loading bars; better UX than spinner for large payloads |
| Pagination on all screens | Prevents DOM overload and cognitive fatigue; default 10 items per page (experiments/runs), 5 per page (configs) |
| Dual loading indicators (panel + polling badge) | Initial load → full progress panel; background polls → subtle "Syncing..." badge; clear state transitions |
| Two progress patterns (network vs experiment) | `LoadingFeedbackPanel` for network/API loads (byte-level); `ExperimentProgressCard` for experiment execution (run completion); distinct concerns, reusable components |
| Cascade delete with confirmation | DELETE endpoint scrubs all collections (experiments, run_status, chunks, results); `ConfirmDeleteModal` shows experiment details + deletion statistics; prevents deletion of running experiments |
| Boot orphan reconciliation | `BackgroundTasks` sweeps die on process exit; startup marks in-flight runs `interrupted` and sets terminal experiment status — separate from Slice 10 retry |
| Pause / resume sweeps | Cooperative halt via `_SweepControl` threading events; `resume_sweep()` skips completed parameter signatures; status `paused` is non-terminal |
| Vector DB stats API + dashboard | `GET /experiments/vector-db-stats` and `/{id}/db-stats`; estimated storage from chunk counts + model dimensions; optional Atlas quota bar with tier/provider/region via `resolve_tier_specs()` |
| Timezone-aware UTC timestamps | PyMongo `tz_aware=True`; all writes use `datetime.now(timezone.utc)` so JSON includes `Z` and browser elapsed/duration math is correct |
| `started_at` on first run | Duration and ETA exclude queue time between submission and first pipeline phase |
| Search index preflight | `required_search_indexes(config)` + cluster snapshot; fail before runs if missing/quota exhausted; HTTP 422 on submit |
| Atlas index CLI | `indexes list` / `indexes reset` for M0 3-index cluster-wide quota troubleshooting |
| Option A scoped logging | `[rag-params-finder] [Scope] operation — details` in server (`scope_log.py`) and dashboard dev console (`devLog.ts`) |
| Dedicated thread pools (`executors.py`) | Sweeps and heavy Mongo aggregations no longer compete with lightweight `GET /experiments` on the default executor |
| Batched vector-db-stats queries | Three aggregation pipelines replace per-experiment N+1 round-trips on the experiments list |
| Decoupled dashboard polling | List 2 s / vector DB stats 60 s / Search Explorer 15 s while running — each with appropriate fetch timeouts in `frontend/src/constants.ts` |
| Search Explorer poll indicator timing | `PollingIndicator` showDelay + minVisibleMs reduce badge flicker on 15 s explore polls |

---

## 🔮 Future Enhancements

| Enhancement | Notes |
|---|---|
| Run recovery (retry failed / interrupted runs) | **Reconciliation on boot** ✅ — status fix only. **Retry** planned as [Slice 10](../slices/SLICE-10-RUN-RECOVERY.md): `recover` CLI + API; **`RECOVER_ON_BOOT`** = retry **INTERRUPTED** only |
| SSE live updates | Replace 2-second polling with Server-Sent Events |
| Parallel sweep (`execution.parallelism` > 1) | Planned as [Slice 16 — Parallel Sweep Runs](../slices/SLICE-16-PARALLEL-SWEEP-RUNS.md); bounded in-process pool first; **Celery + Redis** when multi-process fairness or isolation is needed |
| Dashboard-triggered runs | Submit experiments from the React UI, not just CLI |
| Experiment cleanup CLI | `rag-params-finder cleanup --older-than 30d` |
| Docker Compose | One-command local setup |

---

## 👉 See Also

- [Extending the System](extending.md) — add new models, chunkers, or endpoints
- [Development Guide](development.md) — dev loop, quality gates, slice playbook
- [ADR-001](../adr/ADR-001-two-process-architecture.md) · [ADR-002](../adr/ADR-002-voyage-and-local-providers.md) · [ADR-003](../adr/ADR-003-mongodb-atlas-vector-store.md) — detailed rationale for key decisions
