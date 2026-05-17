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
3. **React Dashboard** (observer) — read-only visualization of experiments and results

The CLI and Dashboard are intentionally thin. All business logic lives in the server.

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
│   ├── main.py              # FastAPI app entry; lifespan ensures DB indexes
│   ├── settings.py          # Centralized pydantic-settings config
│   ├── api/
│   │   ├── experiments.py   # experiments CRUD, results/explore, cancel
│   │   └── runs.py          # GET /runs/{id}/status
│   ├── core/
│   │   ├── orchestrator.py  # run_sweep() + run_single() pipeline
│   │   ├── pdf_parser.py    # pypdf text extraction
│   │   ├── query_loader.py  # persona JSON → Query dataclass list
│   │   ├── model_registry.py  # embedding + reranking model catalog
│   │   ├── embedder.py      # Voyage embedding client
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
│       └── indexes.py       # collection + index creation helpers
├── cli/
│   ├── main.py              # Typer app (run, cancel, version)
│   ├── config_loader.py     # YAML parser + model registry validation
│   └── api_client.py        # HTTP client to server
└── frontend/src/
    ├── App.tsx              # root component (screen routing)
    ├── components/
    │   ├── DashboardShell.tsx          # shared dashboard shell (header, nav)
    │   ├── AppPageChrome.tsx           # shared page chrome wrapper
    │   ├── LoadingFeedbackPanel.tsx    # progress panel (byte-level progress, activity feed)
    │   ├── PollingIndicator.tsx        # subtle "Syncing..." indicator during polls
    │   ├── ExperimentsScreen.tsx       # list view (polling every 2s, paginated)
    │   ├── ExperimentDetailScreen.tsx  # detail view (runs table, phase dots, metrics, paginated)
    │   └── SearchExplorerScreen.tsx    # results analysis (ranked configs, per-query, paginated)
    ├── services/
    │   ├── apiClient.ts       # fetch wrapper (all server API calls)
    │   └── fetchWithProgress.ts  # streamed fetch with byte-level progress tracking
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
- `voyage` → `server/core/embedder.py` → Voyage AI API (1024-dim)

**Reranking provider** (`retrieval.rerank_provider`):
- `local` → `server/core/local_reranker.py` → CrossEncoder `cross-encoder/ms-marco-MiniLM-L-6-v2`
- `voyage` → `server/core/reranker.py` → Voyage AI rerank API

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

---

## 🔮 Future Enhancements

| Enhancement | Notes |
|---|---|
| Run recovery (failed / interrupted runs) | Planned as [Slice 10 — Run Recovery](../slices/SLICE-10-RUN-RECOVERY.md): `recover` CLI + API; per-`run_id` artifact scrub; **`RECOVER_ON_BOOT`** = **INTERRUPTED** only |
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
