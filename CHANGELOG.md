# Changelog

All notable changes to **rag-params-finder** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**For contributors**: Update this file **during development**, not at release time. Add entries under `## [Unreleased]` as you work. When creating a release, `./scripts/release.sh` will prompt you to move items to the new version section.

---

## [Unreleased]

### Added

- **Contributor docs:** Optional `code-review-graph` MCP guidance in [Development Guide](docs/contributor-guide/development.md) and README Contributing section (not required for end users)
- **Agent docs:** Graph-first exploration workflow in [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md)
- **Slice 20 toolchain hardening** — unified `./scripts/quality-gates.sh` mirroring CI; `check_integrity.py`, `pip-audit.sh`
- **CI:** scoped 80% coverage gate, ESLint, bandit SAST, pip-audit, gitleaks secrets scan job
- **Repo hygiene:** `.gitleaks.toml`, `.nvmrc`, `.editorconfig`, `.gitattributes`, Dependabot
- **Frontend:** ESLint + `eslint-plugin-security` wired in CI and pre-commit

### Changed

- Upgraded urllib3, starlette, idna, langchain-core via uv dependency overrides
- Pre-commit: gitleaks config, frontend lint hook, bandit hook

---

## [0.11.0] - 2026-05-23

### Added

- **Weighted averaging metric** (`query_avg_score`) for query-level fairness — prevents queries with many results from dominating average scores
- **Tiebreaker explanation UI** when multiple configs achieve same max score — shows why one config was ranked #1
- **Configurable tiebreaker** via `TIEBREAKER_METRIC` env var (default: `query_avg`, legacy: `chunk_avg`)
- Detailed results tab with **chunk size/overlap badges** — map individual results back to hyperparameter configs
- **Query text display** in detailed results — see which query each result answered
- **Sweep dimensions collapsible panel** with Cartesian product calculation (e.g., "1 model × 5 methods × 3 sizes × 2 overlaps = 30 configs")

### Changed

- Backend sorting now uses **4-level tiebreaker** (max_score DESC, query_avg_score DESC, chunk_size ASC, overlap ASC)
- Config ranking uses **weighted query_avg_score** by default instead of unweighted chunk average
- Hyperparameters and Detailed Results tabs now have **clear explanatory headers**

### Fixed

- Confusing UI when multiple configs achieved same max score with no explanation why one was "best"
- Detailed Results tab didn't show chunk size/overlap → couldn't map results back to configs
- Missing query text in Detailed Results → couldn't tell which query each result answered

---

## [0.10.0] - 2026-05-23

### Added

- **Unified retriever configuration format** (`retrievers` list) — cleaner sweep expansion
- **Auto-migration** from old `retrieval.methods` format to new `retrievers` format
- Support for **multiple rerankers** in sweep (each as separate dimension, not chained)

### Changed

- Each entry in `retrievers` list is **one sweep dimension** (one retriever per run, not a pipeline)
- Dense/sparse/hybrid + rerankers now treated uniformly in sweep expansion
- Maintained **backward-compatible DB fields** (`retrieval_method`, `retrieval_provider`, `retrieval_model`)

---

## [0.9.1] - 2026-05-23

### Added

- **Option A scoped logging** across server, CLI, and dashboard (`[rag-params-finder] [Scope] ...` format)
- **Elapsed + ETA display** on experiment progress card (linear projection from completed runs)
- **Timezone-aware UTC timestamps** (PyMongo `tz_aware=True`) — fixes browser elapsed/duration misparse
- **`started_at` timestamp** set on first run (excludes queue time from duration and ETA)
- **Atlas cluster tier specs** in vector DB stats (tier, provider, region via `resolve_tier_specs()`)

### Changed

- Duration stat shows "—" while running or paused (was incorrectly calculated during execution)
- Single control button location in header (removed duplicate pause/resume/cancel from banners)

---

## [0.9.0] - 2026-05-23

### Added

- **Search index preflight validation** before sweep starts — HTTP 422 on submit if indexes insufficient
- **`search_index_plan`** module — derives required indexes from config and assesses M0 quota capacity
- **`search_index_guard`** module — cluster snapshot + `ensure_indexes` retry with mismatch detection
- **`indexes list` CLI command** — shows known vs unknown indexes cluster-wide
- **`indexes reset` CLI command** — drop unknown indexes or rebuild chunks indexes (`--all` flag)
- **M0 3-index cluster quota guard** — prevents sweeps from exceeding free-tier limits
- **17 pytest scenarios** for search index planning, capacity assessment, and preflight guards

### Changed

- Experiments fail fast **before embedding** if required indexes are missing (saves API calls and time)

---

## [0.8.1] - 2026-05-20

### Added

- **39 pytest regression tests** total
- Embedder dispatch tests (local vs Voyage routing)
- Retriever index selection tests (`get_index_name` by dimension)
- Model registry validation tests (provider/model cross-checks)
- Database stats aggregation tests (cluster grouping, experiment footprint)
- Kimchi adapter tests (CAST payload format, runtime dimensions)

---

## [0.8.0] - 2026-05-13 to 2026-05-20

### Added

- **Kimchi embedding provider** (CAST OpenAI-compatible embeddings via `/v1/embeddings`)
- **Runtime dimension detection** for Kimchi models (no hardcoded dimensions)
- **Kimchi model registry entries** with `contextualized` flag for routing
- **4-model Kimchi example config** demonstrating provider-agnostic sweep

---

## [0.7.1] - 2026-05-19

### Added

- **Dedicated thread pools** (`SWEEP_EXECUTOR`, `HEAVY_READ_EXECUTOR`) to prevent API blocking during sweeps
- **Decoupled dashboard poll intervals**: list 2s, vector DB stats 60s, Search Explorer 15s (constants in `frontend/src/constants.ts`)
- **Batched db-stats aggregations** to reduce MongoDB query load
- **PollingIndicator anti-jitter** (`showDelayMs=600`, `minVisibleMs=1000`) — sync badge no longer flickers on fast polls

### Changed

- Experiment list loads within **seconds** during active sweeps (was blocked by db-stats aggregations)
- Vector DB stats may lag but **do not block** the list API

---

## [0.7.0] - 2026-05-19

### Added

- **Vector DB stats dashboard** with cluster-grouped storage metrics (chunks count, storage MB, cluster quota)
- **Atlas storage quota via Admin API** (`resolve_tier_specs()` + optional `MONGODB_STORAGE_LIMIT_MB` override)
- **Experiment pause/resume control** (`_SweepControl` threading events, cooperative sweep halt)
- **Boot reconciliation for orphaned runs** — marks stale `running` experiments as `partial` or `complete` on server restart
- **Voyage model catalog expansion** — 12 models total (voyage-4 series, domain models, voyage-3 legacy)
- **voyage-context-3 contextualized embedding API** — 32K token window with automatic segment splitting
- **Collapsible UI panels** with `localStorage` persistence (vector DB stats, experiment rows)

### Changed

- `resume_sweep()` skips **already-completed param signatures** (resumes from next incomplete combination)
- Experiment status `paused` is **non-terminal** (dashboard polls continue until resumed or cancelled)

---

## [0.6.0] - 2026-05-19

### Added

- **Experiment deletion with confirmation** (CLI + dashboard)
- **CLI `delete` command** with `--force` flag to skip interactive prompt
- **Dashboard ConfirmDeleteModal** with experiment details and deletion warning
- **Cascade cleanup** across all collections (experiments, run_status, chunks, results)
- **Deletion statistics display** (documents deleted per collection)

### Changed

- **Running experiments cannot be deleted** — API returns 400 error (must cancel first)
- Delete button **disabled for running experiments** with tooltip explanation

---

## [0.5.0] - 2026-05-17

### Added

- **LoadingFeedbackPanel** with **byte-level progress tracking** via ReadableStream
- **Pagination** to experiments list (10 items/page)
- **Pagination** to runs table (10 runs/page)
- **Pagination** to configs table (5/page)
- **PollingIndicator** for background syncs (subtle "Syncing..." badge)
- **DashboardShell** + **AppPageChrome** unified layout (shared header/nav/title/back-button across screens)
- **ExperimentProgressCard** reusable component (circular progress with default/compact variants)
- **Activity feed** in LoadingFeedbackPanel (fetch milestones: start → headers → chunks → complete)

### Changed

- Full progress panel for **initial loads**; subtle polling badge for **background refreshes**
- Polling indicator only shows **after first load completes** (`initialLoadDone` flag per screen)

---

## [0.4.1] - 2026-05-05

### Added

- **Architecture Decision Records** (ADRs) in `docs/adr/` (two-process architecture, dual providers, MongoDB Atlas choice)
- **Slice specifications** in `docs/slices/` (detailed acceptance criteria, verification steps)
- **Pre-commit hooks** (ruff, mypy, prettier) via `.pre-commit-config.yaml`
- **Comprehensive badges** across README and docs (build status, coverage, license, Python/Node versions)
- **Quality gates baseline documentation** (lint, type check, test counts, bundle size)

---

## [0.4.0] - 2026-05-17

### Added

- **Fixed chunker** (character-window slicing with configurable overlap)
- **Token chunker** (LangChain `TokenTextSplitter` with cl100k_base encoding)
- **Sentence chunker** (NLTK `sent_tokenize` with character-budget grouping)
- **Semantic chunker** (sentence-transformers cosine similarity grouping; chunk_size as hard cap, overlap ignored)
- **Sparse retrieval** (Atlas BM25 via `$search`)
- **Hybrid retrieval** (RRF merge with k=60, combines dense + sparse)
- **5 example configs** covering all features (all chunkers, all retrievers, local + Voyage)
- **Atlas Full Text Search index setup docs** in `CLAUDE.local.md`

### Changed

- `search()` dispatcher conditionally embeds query (only for dense/hybrid, not sparse)
- Semantic chunker always uses `all-MiniLM-L6-v2` (provider-agnostic, keeps chunking independent of embedding config)

---

## [0.3.0] - 2026-05-02

### Added

- **Local embedding** with sentence-transformers (`all-MiniLM-L6-v2`, 384-dim, ~23MB)
- **Local reranking** with CrossEncoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`, ~23MB)
- **Explicit provider routing** (`provider` field in YAML config drives end-to-end dispatch)
- **Separate vector indexes per dimension** (`vector_index_1024` for Voyage, `vector_index_384` for local)
- **No API key required** for local provider (fully offline embedding + reranking)
- **Model registry** (`server/core/model_registry.py`) — unified catalog for embedding + reranker models
- **Pydantic validators** cross-check model names match declared provider (fast-fail at config parse time)

### Changed

- Provider flows through `RunParams` → orchestrator → embedder/reranker (explicit routing, no runtime lookups)

---

## [0.2.0] - 2026-05-02

### Added

- **Reranking** with Voyage `rerank-2.5-lite` (refines dense search: top-20 candidates → top-5 final)
- **Cartesian product sweep expansion** (N models × M methods × P sizes × Q overlaps → N×M×P×Q runs)
- **Live status tracking** with phase indicators (QUEUED → PARSING → CHUNKING → EMBEDDING → STORING → QUERYING → RERANKING → COMPLETE)
- **Multiple queries from persona JSON** files (loop over all questions per run, store `persona_id` and `focus`)
- **CLI `--watch` flag** for live progress (Rich Live table polling runs every 2s)
- **ExperimentDetailScreen** with drill-down (phase dots, run table, polling until terminal status)

### Changed

- `run_sweep()` + `run_single()` split (sweep management vs pipeline execution, Single Responsibility)
- `on_error: continue/stop` allows partial completion without losing all results
- Experiment status `partial` distinguishes "some failed" from "all failed" or "all complete"

---

## [0.1.0] - 2026-05-02

### Added

- **End-to-end RAG parameter sweep pipeline** (parse PDF → chunk → embed → store → query → search → results)
- **Voyage AI voyage-3.5-lite embedding** (1024-dim, $0.06/1M tokens)
- **Recursive text chunker** (LangChain `RecursiveCharacterTextSplitter`)
- **DENSE vector search** with MongoDB Atlas (cosine similarity)
- **FastAPI server** with `/experiments` endpoints (POST submit, GET list, GET by ID)
- **React dashboard** with experiments list (status badges, run counts, clickable rows)
- **CLI submission** via `rag-params-finder run --config <yaml>`
- **BackgroundTasks** for async sweep execution (no Celery required for MVP)

---

## [0.0.1] - 2026-04-15

### Added

- **Project skeleton** and initial architecture
- **MongoDB Atlas vector search integration** (PyMongo client, collection helpers)
- **Basic experiment orchestration pipeline** (PDF parser, chunker dispatcher, orchestrator stub)
- **CLI submission framework** (Typer app, config loader, API client)

---

[Unreleased]: https://github.com/neomatrix369/rag-params-finder/compare/v0.11.0...HEAD
[0.11.0]: https://github.com/neomatrix369/rag-params-finder/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/neomatrix369/rag-params-finder/compare/v0.9.1...v0.10.0
[0.9.1]: https://github.com/neomatrix369/rag-params-finder/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/neomatrix369/rag-params-finder/compare/v0.8.1...v0.9.0
[0.8.1]: https://github.com/neomatrix369/rag-params-finder/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/neomatrix369/rag-params-finder/compare/v0.7.1...v0.8.0
[0.7.1]: https://github.com/neomatrix369/rag-params-finder/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/neomatrix369/rag-params-finder/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/neomatrix369/rag-params-finder/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/neomatrix369/rag-params-finder/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/neomatrix369/rag-params-finder/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/neomatrix369/rag-params-finder/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/neomatrix369/rag-params-finder/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/neomatrix369/rag-params-finder/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/neomatrix369/rag-params-finder/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/neomatrix369/rag-params-finder/releases/tag/v0.0.1
