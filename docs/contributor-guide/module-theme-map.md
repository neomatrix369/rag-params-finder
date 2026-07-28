# Module theme map

> Behavior | Feature | Function taxonomy for `rag-params-finder`.
> Taxonomy from Slice 44 Should audit (2026-07-27). **All five ranked hotspot folder moves are IMPLEMENTED** on Slice 45 (thin compatibility shims remain at old `scripts/*.sh` paths for one minor). Spec: [`SLICE-45-MODULE-THEME-SEPARATION.md`](../plan/slices/07-quality-craft/SLICE-45-MODULE-THEME-SEPARATION.md).
> Optional IDE canvas name: `project-structure-taxonomy.canvas.tsx` (not required in-repo).

## Theme labels

| Level | Meaning | Examples |
|-------|---------|----------|
| **Behavior** | Runtime / lifecycle concern | pipeline phases, preflight guards, storage mode, polling |
| **Feature** | Product capability | experiments CRUD, sweep, embed/rerank providers, Search Explorer screens |
| **Function** | Layer / utility / ops | ports/factory, models, utils, quality-gates scripts, types |

Apply tags at **repo → package → folder** level (not every file).

---

## Repo-level map

| Area | Dominant tags | Notes |
|------|---------------|-------|
| `server/api/` | Feature | Experiments lifecycle + ranked sweep HTTP surface (optional later: `experiments/` vs `sweep/`) |
| `server/core/` | Behavior + Feature (+ Function) | Theme packages **IMPLEMENTED**; flat `*.py` are mostly shims + keep-at-core ingest/catalog/ops |
| `server/db/` | Behavior + Function (ports) | `ports/` + `mongo/` + `postgres/` **IMPLEMENTED**; flat shims at old paths |
| `server/models/` | Function | Domain schemas — coherent, no split proposed |
| `server/utils/` | Function | Cross-cutting logging/metadata — coherent |
| `cli/` | Feature + Function | Small Typer app — optional later `commands/` |
| `frontend/src/components/` | Feature + Function | **IMPLEMENTED** — `screens/`, `chrome/`, `experiment/`, `stats/`, `explore/` |
| `frontend/src/hooks/` | Behavior \| Feature | Detail hydrate/poll controller (`useExperimentDetail`) |
| `frontend/src/test/helpers/` | Function | Shared Vitest builders (Slice 45 Should) |
| `frontend/src/services/` | Function + Behavior | HTTP / progress fetch |
| `frontend/src/utils/` | Function | Status / labels / feed / completionReason |
| `frontend/src/types/` | Function | TS mirrors of Python models |
| `tests/` | Behavior + Feature | Mirror layout **IMPLEMENTED**; root keeps `conftest.py`, `contract/`, `helpers/` |
| `scripts/` | Function (ops) | **IMPLEMENTED** — `ci/`, `docker/`, `release/`, `security/` (+ `lib/`); flat shims at old paths |
| `configs/` | Feature | Already split `mongodb/` vs `supabase/` |
| `docs/` | Function (+ Feature in `plan/`) | Knowledge + roadmap |
| `docker/` | Function | Image build assets |
| Root lifecycle | Behavior + Function | `start-services.sh`, compose, packaging |

**Low priority / no split proposed:** `server/models/`, `server/utils/`, `cli/`, `configs/{mongodb,supabase}/`, `core/chunkers/` + ingest loaders / catalog / Aim+Atlas (keep at `core/` root).

---

## Hotspot ranking (separation status)

| Rank | Location | Status | Proposed / landed folders |
|------|----------|--------|---------------------------|
| 1 | `server/core/` | **IMPLEMENTED** (Slice 45) | `pipeline/`, `embedding/`, `rerank/`, `retrieval/`, `guards/` (+ keep `chunkers/`) |
| 2 | `tests/` | **IMPLEMENTED** (Slice 45) | Mirror `tests/server`, `tests/cli`, `tests/scripts` + `contract/` / `helpers/` |
| 3 | `server/db/` | **IMPLEMENTED** (Slice 45) | `ports/`, `mongo/`, `postgres/` |
| 4 | `frontend/src/components/` | **IMPLEMENTED** (Slice 45) | `screens/`, `chrome/`, `experiment/`, `stats/` (+ `explore/`) |
| 5 | `scripts/` | **IMPLEMENTED** (Slice 45) | `ci/`, `docker/`, `release/`, `security/` (+ keep `lib/`) |

Mild (optional later): `server/api/` → `experiments/` vs `sweep/`.

---

## `server/core/` theme groups

| Theme group | Files | Tags |
|-------------|-------|------|
| Pipeline orchestration | `pipeline/orchestrator.py`, `pipeline/executors.py`, `pipeline/experiment_control.py`, `pipeline/startup_reconciliation.py`, `pipeline/search.py`, `pipeline/signatures.py` | Behavior \| Feature — **IMPLEMENTED** (shims at `server.core.<name>`) |
| Ingest | `data_loader.py`, `query_loader.py`, `chunkers/*` | Feature — keep at `core/` |
| Embedding providers | `embedding/embedder.py`, `embedding/local_embedder.py`, `embedding/sie_embedder.py`, `embedding/embedder_factory.py`, `embedding/rate_limiter.py` | Feature \| Function — **IMPLEMENTED** |
| Rerank | `rerank/reranker.py`, `rerank/local_reranker.py` | Feature — **IMPLEMENTED** |
| Retrieval | `retrieval/retriever_mongo.py`, `retrieval/retriever_postgres.py` | Feature \| Behavior — **IMPLEMENTED** |
| Preflight guards | `guards/search_index_plan.py`, `guards/search_index_guard.py`, `guards/sie_guard.py`, `guards/config_backend_guard.py`, `guards/health_check.py` | Behavior \| Function — **IMPLEMENTED** |
| Catalog / analysis | `model_registry.py`, `results_analyzer.py` | Function \| Feature — keep at `core/` |
| Observability / ops | `aim_logger.py`, `atlas_storage.py` | Function \| Feature — keep at `core/` |

---

## `server/db/` theme groups

| Theme group | Files | Tags |
|-------------|-------|------|
| Ports / factory | `ports/storage.py`, `ports/retriever_backend.py`, `ports/store_factory.py`, `ports/stats_common.py` | Function — **IMPLEMENTED** (shims at `server.db.<name>`) |
| Mongo | `mongo/atlas.py`, `mongo/mongodb_uri.py`, `mongo/mongo_store.py`, `mongo/mongo_stats.py`, `mongo/indexes.py` | Behavior \| Feature — **IMPLEMENTED** |
| Postgres | `postgres/postgres.py`, `postgres/postgres_uri.py`, `postgres/postgres_store.py`, `postgres/postgres_stats.py`, `postgres/postgres_docs.py`, `postgres/schema.sql` | Behavior \| Feature — **IMPLEMENTED** |

---

## `frontend/src/components/` theme groups

| Theme | Paths | Tags |
|-------|-------|------|
| Screens | `screens/ExperimentsScreen.tsx`, `screens/ExperimentDetailScreen.tsx`, `screens/SearchExplorerScreen.tsx` (+ co-located `*.test.tsx`) | Feature — **IMPLEMENTED** |
| Chrome / shell | `chrome/DashboardShell.tsx`, `AppPageChrome.tsx`, `CollapsibleCard.tsx`, `PollingIndicator.tsx`, `LoadingFeedbackPanel.tsx`, `Pagination.tsx` | Function — **IMPLEMENTED** |
| Experiment controls | `experiment/ExperimentControlButtons.tsx`, `ExperimentProgressCard.tsx`, `ConfirmDeleteModal.tsx`, `experimentDetailProgress.ts`, `experiment/experimentDetail/*` | Feature \| Behavior — **IMPLEMENTED** |
| Explore panels | `explore/ExplorePanels.tsx`, `explore/formatChunkDimensions.ts` | Feature — **IMPLEMENTED** |
| Vector DB stats | `stats/VectorDbStatsPanel.tsx`, `stats/ExperimentVectorDbStatsCard.tsx`, `stats/StatTile.tsx` | Feature \| Function — **IMPLEMENTED** |
| Shared test helpers | `frontend/src/test/helpers/{experiments,vectorDbStats,explore,experimentDetail}.ts` | Function — **IMPLEMENTED** |

---

## `scripts/` theme groups

| Theme | Paths | Tags |
|-------|-------|------|
| Quality / CI | `ci/quality-gates.sh`, `ci/pre-push-gates.sh`, `ci/repo-lint.sh`, `ci/check_integrity.py`, `ci/check_backend_coverage_floors.py`, `ci/install-git-hooks.sh`, `ci/pip-audit.sh` | Function — **IMPLEMENTED** (shims at `scripts/<name>`) |
| Security | `security/security-scan.sh` | Function — **IMPLEMENTED** |
| Docker / runtime | `docker/health-check.sh`, `docker/docker-build-context.sh`, `docker/docker-cleanup.sh`, `docker/wait-experiment.sh`, `docker/aim-ui.sh` | Behavior \| Function — **IMPLEMENTED** |
| Release / GitHub | `release/release.sh`, `release/bump_version.py`, `release/create_github_releases.sh`, `release/push_tags_incrementally.sh` | Function — **IMPLEMENTED** |
| Shared lib | `lib/compose.sh`, `lib/storage_mode.sh` | Function — keep |

---

## `tests/` grouping

**IMPLEMENTED** (Slice 45): mirror layout under `tests/server/{core,db,api,models}/`, `tests/cli/`, `tests/scripts/` plus kept `contract/` + `helpers/`. Slice 16 mega-suite split into `tests/server/core/pipeline/` (+ `helpers/pipeline_sweep.py`). Root retains `conftest.py` only (no flat `test_*.py` suites).

---

## Related

- Module tree detail: [`architecture.md`](architecture.md) → Module Map
- Slice 44 (taxonomy Should + coverage Must): [`SLICE-44-FRONTEND-COVERAGE-GATE.md`](../plan/slices/07-quality-craft/SLICE-44-FRONTEND-COVERAGE-GATE.md)
- Slice 45 (execute moves + FE/BE craft): [`SLICE-45-MODULE-THEME-SEPARATION.md`](../plan/slices/07-quality-craft/SLICE-45-MODULE-THEME-SEPARATION.md)
- DECISIONS #135 — audit+proposal in 44; moves owned by 45
