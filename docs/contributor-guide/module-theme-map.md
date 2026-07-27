# Module theme map

> Behavior | Feature | Function taxonomy for `rag-params-finder`.
> Planning SSOT from Slice 44 Should audit (2026-07-27). **No filesystem moves** in Slice 44 — execution proposals live in [`SLICE-45-MODULE-THEME-SEPARATION.md`](../plan/slices/SLICE-45-MODULE-THEME-SEPARATION.md).
> Interactive view: workspace canvas `project-structure-taxonomy.canvas.tsx`.

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
| `server/api/` | Feature | Experiments lifecycle + ranked sweep HTTP surface |
| `server/core/` | Behavior + Feature (+ Function guards) | **Hotspot** — flat mix; see below |
| `server/db/` | Behavior + Function (ports) | **Hotspot** — ports + Mongo + Postgres co-located |
| `server/models/` | Function | Domain schemas — coherent, no split proposed |
| `server/utils/` | Function | Cross-cutting logging/metadata — coherent |
| `cli/` | Feature + Function | Small Typer app — optional later `commands/` |
| `frontend/src/components/` | Feature + Function | **Hotspot** — screens + chrome + stats |
| `frontend/src/services/` | Function + Behavior | HTTP / progress fetch |
| `frontend/src/utils/` | Function | Status / labels helpers |
| `frontend/src/types/` | Function | TS mirrors of Python models |
| `tests/` | Behavior + Feature | **Hotspot** — ~36 top-level `test_*.py` |
| `scripts/` | Function (ops) | **Hotspot** — CI / docker / release / security mixed |
| `configs/` | Feature | Already split `mongodb/` vs `supabase/` |
| `docs/` | Function (+ Feature in `plan/`) | Knowledge + roadmap |
| `docker/` | Function | Image build assets |
| Root lifecycle | Behavior + Function | `start-services.sh`, compose, packaging |

**Low priority / no split proposed:** `server/models/`, `server/utils/`, `cli/`, `configs/{mongodb,supabase}/`, `core/chunkers/` (already cohesive).

---

## Hotspot ranking (needs separation)

| Rank | Location | Approx files | Why | Proposed folders |
|------|----------|--------------|-----|------------------|
| 1 | `server/core/` | 24 | Pipeline + providers + retrieval + guards + ops flat | `pipeline/`, `embedding/`, `rerank/`, `retrieval/`, `guards/` (+ keep `chunkers/`) |
| 2 | `tests/` | 36 top-level | Almost no thematic folders | Mirror packages **or** `unit/` + existing `contract/` / `helpers/` |
| 3 | `server/db/` | 14 + `schema.sql` | Ports + Mongo + Postgres co-located | `ports/`, `mongo/`, `postgres/` |
| 4 | `frontend/src/components/` | 16 | Screens + chrome + experiment + stats + tests | `screens/`, `chrome/`, `experiment/`, `stats/` |
| 5 | `scripts/` | 16 + `lib/` | Quality + docker + release + security | `ci/`, `docker/`, `release/`, `security/` (+ keep `lib/`) |

Mild (optional later): `server/api/` → `experiments/` vs `sweep/`.

---

## `server/core/` theme groups

| Theme group | Files | Tags |
|-------------|-------|------|
| Pipeline orchestration | `orchestrator.py`, `executors.py`, `experiment_control.py`, `startup_reconciliation.py` | Behavior \| Feature |
| Ingest | `data_loader.py`, `query_loader.py`, `chunkers/*` | Feature |
| Embedding providers | `embedder.py`, `local_embedder.py`, `sie_embedder.py`, `embedder_factory.py`, `rate_limiter.py` | Feature \| Function |
| Rerank | `reranker.py`, `local_reranker.py` | Feature |
| Retrieval | `retriever_mongo.py`, `retriever_postgres.py` | Feature \| Behavior |
| Preflight guards | `search_index_plan.py`, `search_index_guard.py`, `sie_guard.py`, `config_backend_guard.py`, `health_check.py` | Behavior \| Function |
| Catalog / analysis | `model_registry.py`, `results_analyzer.py` | Function \| Feature |
| Observability / ops | `aim_logger.py`, `atlas_storage.py` | Function \| Feature |

---

## `server/db/` theme groups

| Theme group | Files | Tags |
|-------------|-------|------|
| Ports / factory | `storage.py`, `retriever_backend.py`, `store_factory.py`, `stats_common.py` | Function |
| Mongo | `atlas.py`, `mongodb_uri.py`, `mongo_store.py`, `mongo_stats.py`, `indexes.py` | Behavior \| Feature |
| Postgres | `postgres.py`, `postgres_uri.py`, `postgres_store.py`, `postgres_stats.py`, `postgres_docs.py`, `schema.sql` | Behavior \| Feature |

---

## `frontend/src/components/` theme groups

| Theme | Files | Tags |
|-------|-------|------|
| Screens | `ExperimentsScreen.tsx`, `ExperimentDetailScreen.tsx`, `SearchExplorerScreen.tsx` (+ `*.test.tsx`) | Feature |
| Chrome / shell | `DashboardShell.tsx`, `AppPageChrome.tsx`, `CollapsibleCard.tsx`, `PollingIndicator.tsx`, `LoadingFeedbackPanel.tsx` | Function |
| Experiment controls | `ExperimentControlButtons.tsx`, `ExperimentProgressCard.tsx`, `ConfirmDeleteModal.tsx`, `experimentDetailProgress.ts` | Feature \| Behavior |
| Vector DB stats | `VectorDbStatsPanel.tsx`, `ExperimentVectorDbStatsCard.tsx` | Feature |

---

## `scripts/` theme groups

| Theme | Files | Tags |
|-------|-------|------|
| Quality / CI | `quality-gates.sh`, `pre-push-gates.sh`, `repo-lint.sh`, `check_integrity.py`, `install-git-hooks.sh`, `pip-audit.sh` | Function |
| Security | `security-scan.sh` | Function |
| Docker / runtime | `health-check.sh`, `docker-build-context.sh`, `docker-cleanup.sh`, `wait-experiment.sh`, `aim-ui.sh` | Behavior \| Function |
| Release / GitHub | `release.sh`, `bump_version.py`, `create_github_releases.sh`, `push_tags_incrementally.sh` | Function |
| Shared lib | `lib/compose.sh`, `lib/storage_mode.sh` | Function |

---

## `tests/` grouping hint

Prefer either:

1. **Mirror packages** — `tests/server/core/`, `tests/server/db/`, `tests/cli/`, `tests/api/` (keeps import mental model), or
2. **Tier folders** — keep `contract/` + `helpers/`; add `unit/` for top-level suites currently flat.

Existing: `tests/contract/`, `tests/helpers/`.

---

## Related

- Module tree detail: [`architecture.md`](architecture.md) → Module Map
- Slice 44 (taxonomy Should + coverage Must): [`SLICE-44-FRONTEND-COVERAGE-GATE.md`](../plan/slices/SLICE-44-FRONTEND-COVERAGE-GATE.md)
- Slice 45 (execute moves): [`SLICE-45-MODULE-THEME-SEPARATION.md`](../plan/slices/SLICE-45-MODULE-THEME-SEPARATION.md)
- DECISIONS #135 — audit+proposal in 44; moves deferred to 45
