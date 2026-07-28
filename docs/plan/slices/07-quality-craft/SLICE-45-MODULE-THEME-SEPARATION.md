# Slice 45: Module Theme Separation + FE/BE Craft

> Scenario: Brownfield + Growing Requirement (Flow D) | MoSCoW: Could

**Target time:** ~16–24 h (phased by hotspot + FE/BE craft; do not land all phases in one commit)
**Status:** ✅ COMPLETE
**Depends on:** Slice 44 taxonomy Should artifacts **IMPLEMENTED** — [`module-theme-map.md`](../../../contributor-guide/module-theme-map.md) present with B/F/F tags; canvas published; this stub present. Slice 44 coverage Must + shared floors #142 **COMPLETE** (FE/BE product floors gated).
**Non-blocking:** Structural hygiene + FE/BE construction quality — does not gate PCTO / migration Must slices.

**Origin:** Spun from Slice 44 Should audit on 2026-07-27 (DECISIONS #135). Slice 44 publishes proposals only; **this slice owns filesystem moves and import rewrites**.

**Scope expansion (2026-07-27):** After Slice 44 coverage gate + Code Complete standing assessments (FE then BE), park **construction / composition / test-structure debt** here (not more coverage floors). Coverage is already Excellent; this slice attacks *shape*.

---

## Goal

1. Execute ranked folder separations so Behavior / Feature / Function themes live in dedicated directories (fewest elements that reveal intent — Simple Design). Preserve public API / CLI / HTTP contracts; change **internal** import paths only.
2. Raise **frontend** implementation and test construction toward Code Complete / composability: extract duplicated UI primitives, shrink god screens, share test factories — while keeping FE coverage floors (**95/90/95/95**) green.
3. Raise **backend / CLI / tests / scripts** construction toward Code Complete: carve the orchestrator god module, slim fat API/CLI surfaces, break mega-suites, keep ports/factories intact — while keeping BE floors (**95/90/n/a/95**) green.

---

## MoSCoW

| Priority | Item |
|----------|------|
| **Must** | Move `server/core/` into thematic subpackages with stable re-exports or updated imports; tests green |
| **Must** | Move `server/db/` into `ports/` + `mongo/` + `postgres/` (or equivalent); factory still resolves backends |
| **Should** | Reorganize `tests/` to mirror packages or `unit/` + existing `contract/` / `helpers/` |
| **Should** | Split `frontend/src/components/` into `screens/` / `chrome/` / `experiment/` / `stats/` |
| **Should** | **FE shared primitives** — extract duplicated `Pagination`, `StatTile`/`Row`, `append*Feed`, `completionReasonLabel` into composable modules (Rule of 3) |
| **Should** | **FE screen SLAP** — carve `ExperimentsScreen` / `ExperimentDetailScreen` / `SearchExplorerScreen` toward ≤~200–400 lines each via extract+inject (hooks / presentational children); reduce nesting / else chains |
| **Should** | **FE shared test factories** — move repeated builders (`experiment()`, `vectorDbGroup()`, `buildConfig()`, detail fixtures) to `frontend/src/test/helpers/` (or equivalent); shrink mega-suites as screens shrink |
| **Should** | **BE orchestrator SLAP** — split `server/core/orchestrator.py` (~1161 lines; `_run_single` / `_run_sweep_inner` / `_run_bayesian_inner` 185–217 lines) into `pipeline/` modules (sweep / bayesian / run-lifecycle / search helpers) via extract+inject; preserve public entrypoints |
| **Should** | **BE fat-surface slim** — carve `server/api/experiments.py` (~549), `cli/main.py` (~519), and optionally `server/db/indexes.py` (~480) / `postgres_store.py` (~422) toward smaller focused modules (handlers / presentation / index ops) |
| **Should** | **BE mega-suite shrink** — split or fold `tests/test_slice16_parallel_sweep.py` (~2296 lines) and other >600-line suites; raise GWT marker / factory discipline toward craft norms as files are touched |
| **Could** | Split `scripts/` into `ci/` / `docker/` / `release/` / `security/` (+ keep `lib/`); update gate script paths; optionally slim `start-services.sh` (~504) via further `scripts/lib/` extract |
| **Could** | Finish brownfield FE test narrative docstring migration (remaining Scenario/Slice gaps called out in Slice 44 nw-review) |
| **Could** | CI drift guard: assert Vitest `coverage.thresholds` match `[tool.rag_params_finder.coverage_thresholds]` / documented FE floors |
| **Could** | Brownfield BE test GWT migration on touch (markers + narrative docstrings for suites edited during moves/splits) |
| **Won't** | Rename public CLI commands, HTTP routes, or config YAML keys; delete Mongo or Postgres backends; whole-repo monorepo reshape |
| **Won't** | Raise product coverage floors further; invent 100% branch / mutation for FE screens or whole `server/` tree (product floors stay #142; mutation remains waived/#128 nightly unless non-trivial pure logic is added) |
| **Won't** | Migrate data fetching to TanStack Query / redesign FE state architecture (separate slice if prioritized) |
| **Won't** | Collapse Mongo∥Postgres retriever/store twins into one abstraction beyond existing Protocols — dual adapters are intentional (#129); share only proven pure helpers (pattern: `stats_common`) |

---

## Reuse Analysis (forbidden-import-roots)

Production packages must not import from `scripts.*` or `tests.*`. Declare allowed roots before moving.

| Destination | Source files | Decision | Justification | Declared imports (allowed roots) |
|-------------|--------------|----------|---------------|----------------------------------|
| `server/core/pipeline/` | `orchestrator.py`, `executors.py`, `experiment_control.py`, `startup_reconciliation.py` | MOVE | Consolidate Behavior orchestration | `server.models`, `server.db` (ports after move), `server.core.{embedding,retrieval,guards,chunkers}`, stdlib |
| `server/core/embedding/` | `embedder.py`, `local_embedder.py`, `sie_embedder.py`, `embedder_factory.py`, `rate_limiter.py` | MOVE | Feature provider cluster | `server.models`, `server.settings`, provider SDKs |
| `server/core/rerank/` | `reranker.py`, `local_reranker.py` | MOVE | Feature rerank cluster | same as embedding |
| `server/core/retrieval/` | `retriever_mongo.py`, `retriever_postgres.py` | MOVE | Feature/Behavior search | `server.db`, `server.models` |
| `server/core/guards/` | `search_index_*.py`, `sie_guard.py`, `config_backend_guard.py`, `health_check.py` | MOVE | Preflight Behavior | `server.db`, `server.models`, `server.settings` |
| `server/db/ports/` | `storage.py`, `retriever_backend.py`, `store_factory.py`, `stats_common.py` | MOVE | Protocol / factory Function layer | `server.models`, typing; adapters import ports — not reverse |
| `server/db/mongo/` | `atlas.py`, `mongodb_uri.py`, `mongo_store.py`, `mongo_stats.py`, `indexes.py` | MOVE | Mongo adapter | `server.db.ports`, pymongo |
| `server/db/postgres/` | `postgres*.py`, `schema.sql` | MOVE | Postgres adapter | `server.db.ports`, psycopg |
| `frontend/.../screens/` | `*Screen.tsx` (+ tests) | MOVE | Feature screens | services, utils, types, sibling component folders |
| `scripts/ci/` etc. | gate/release/docker scripts | MOVE (Could) | Ops Function | may invoke CLI/server; not importable by `server` |

**Blast-radius audit (Before-Checks):**

```bash
rg -n 'from server\.core\.|import server\.core' server/ cli/ tests/
rg -n 'from server\.db\.|import server\.db' server/ cli/ tests/
rg -n "from ['\"].*components/" frontend/src/
```

---

## Proposed move tables (proposal locked from Slice 44 inventory)

### 1. `server/core/` → thematic packages

| Destination | Modules |
|-------------|---------|
| `core/pipeline/` | `orchestrator.py`, `executors.py`, `experiment_control.py`, `startup_reconciliation.py` |
| `core/embedding/` | `embedder.py`, `local_embedder.py`, `sie_embedder.py`, `embedder_factory.py`, `rate_limiter.py` |
| `core/rerank/` | `reranker.py`, `local_reranker.py` |
| `core/retrieval/` | `retriever_mongo.py`, `retriever_postgres.py` |
| `core/guards/` | `search_index_plan.py`, `search_index_guard.py`, `sie_guard.py`, `config_backend_guard.py`, `health_check.py` |
| Keep at `core/` top-level (not moved) | `model_registry.py`, `results_analyzer.py`, `aim_logger.py`, `atlas_storage.py`, `data_loader.py`, `query_loader.py` |
| Keep | `core/chunkers/` |

**Blast radius:** `orchestrator.py` callers (`api/`, `main` lifespan), embedder_factory imports, retriever wiring, all `tests/test_*` that import `server.core.*`. Prefer thin `__init__.py` re-exports for one release if import churn is high — see **Re-export deprecation lifecycle**.

### 1b. Backend Code Complete / composition backlog (parked from BE standing assessment)

> Source: Code Complete + craft review of `server/` / `cli/` / `tests/` / `scripts` (2026-07-27), **excluding frontend**. Architecture/DIP already strong (Protocols, factories, `stats_common`); this work improves **construction**, not floors or dual-backend policy.

#### Baseline (debt inventory)

| Hotspot | Approx size | Craft issue |
|---------|-------------|-------------|
| `server/core/orchestrator.py` | ~1161 lines | God module — `_run_single` ~217, `_run_sweep_inner` ~195, `_run_bayesian_inner` ~185 |
| `server/api/experiments.py` | ~549 lines | Fat HTTP surface |
| `cli/main.py` | ~519 lines | Typer app + presentation weight |
| `server/db/indexes.py` | ~480 lines | Atlas index ops bulk |
| `server/db/postgres_store.py` | ~422 lines | Large adapter (high nest in places) |
| `tests/test_slice16_parallel_sweep.py` | ~2296 lines | Mega-suite |
| Other suites >600 lines | mongo acceptance, search_index_guard, postgres integration/dense, … | Hard to navigate; uneven GWT |
| Ports / factories / guards / URI / `stats_common` | mostly ≤250 lines | **Healthy** — leave alone unless touched |

~21 `server`/`cli` modules >200 lines; ~5 >400. Product BE floors (#142) already Excellent on gated modules.

#### Orchestrator SLAP targets (Should — pair with or follow `core/pipeline/` move)

1. Extract Bayesian trial loop, grid sweep, single-run lifecycle, and search/rerank helpers into focused modules under `server/core/pipeline/` (names illustrative): e.g. `bayesian_sweep.py`, `grid_sweep.py`, `run_lifecycle.py`, `retriever_dispatch.py`.
2. Keep a thin `orchestrator.py` (or `pipeline/__init__.py` façade) as the public entry used by API / BackgroundTasks.
3. Prefer extract+inject (storage/retriever/embedder already via factory) — do not add new singletons.
4. Exit criteria (informational): orchestrator façade trending **≤400 lines**; no single function **>80 lines** where practical; BE **95/90/n/a/95** stays green.
5. Characterization: existing unit/orchestrator tests must stay green; add focused unit tests for newly extracted pure helpers.

#### Fat-surface slim (Should)

| Module | Direction |
|--------|-----------|
| `server/api/experiments.py` | Extract request/response helpers, delete/stats assembly, or route groups into `api/experiments_*.py` siblings; keep router registration stable |
| `cli/main.py` | Move presentation / summary printing / large command bodies toward `cli/` helpers (pattern already started with `indexes_cmd.py`) |
| `server/db/indexes.py` | Optional later split: list vs ensure vs reset vs capacity — only if touched during `db/mongo/` move |
| `postgres_store.py` | Prefer keep as adapter during ports move; extract only if a pure helper emerges (follow `stats_common` pattern) |

#### Mega-suite / test craft (Should + Could)

| Today | Target |
|-------|--------|
| Flat `tests/test_*.py` (~39 files, ~11k lines) | Mirror packages (§3) **and** split files >~600–800 lines by behaviour theme |
| `test_slice16_parallel_sweep.py` ~2296 | Multiple focused modules under `tests/server/core/` (or `tests/unit/pipeline/`) |
| GWT markers ~19/39 files | On touch: add `### Given/When/Then` + narrative docstrings (brownfield §D) — Could for untouched files |
| `tests/helpers/` + contract suite | Keep; expand helpers when splitting mega-suites |

Do **not** delete behavioral coverage to shrink files. Do **not** raise `fail_under` / JSON floors in this slice.

#### Preserve (do not “fix”)

- `StorageBackend` / `RetrieverBackend` Protocols + `store_factory` / `embedder_factory`
- Mongo∥Postgres dual adapters (#129) — twin retrievers/stores are intentional
- Shared pure maths in `stats_common` (model for further cross-backend extracts)
- Scoped coverage gate modules + `check_backend_coverage_floors.py`

#### Explicitly out of Slice 45 for BE (Won't / later)

- Whole-tree 100% coverage or inventing function coverage on coverage.py
- Local mutation gate for BE (stay on #128 nightly waive unless new non-trivial pure logic)
- Merging Mongo and Postgres into one store implementation

### 2. `server/db/` → ports + backends

| Destination | Modules |
|-------------|---------|
| `db/ports/` | `storage.py`, `retriever_backend.py`, `store_factory.py`, `stats_common.py` |
| `db/mongo/` | `atlas.py`, `mongodb_uri.py`, `mongo_store.py`, `mongo_stats.py`, `indexes.py` |
| `db/postgres/` | `postgres.py`, `postgres_uri.py`, `postgres_store.py`, `postgres_stats.py`, `postgres_docs.py`, `schema.sql` |

**Blast radius:** `store_factory`, `experiments_shared`, CLI indexes, search_index_guard, health_check, compose docs that cite paths. CLI import points to update in the same PR as the db move: `cli/indexes_cmd.py` → `server.db.*`; `cli/main.py` → CLI modules.

### 3. `tests/` (Should)

| Approach | Layout |
|----------|--------|
| Preferred | Mirror: `tests/server/core/…`, `tests/server/db/…`, `tests/cli/…`, `tests/api/…` |
| Alt | `tests/unit/` for today’s flat suite; keep `contract/` + `helpers/` |

Update `quality-gates.sh` / CI ignore paths if directories move.

**Craft addendum:** when mirroring, also **split** mega-suites (esp. `test_slice16_parallel_sweep.py`); expand `tests/helpers/` rather than duplicating fixtures. Prefer one behavioural theme per file after the move.

### 4. `frontend/src/components/` (Should)

| Destination | Modules |
|-------------|---------|
| `components/screens/` | `ExperimentsScreen`, `ExperimentDetailScreen`, `SearchExplorerScreen` (+ tests) |
| `components/chrome/` | `DashboardShell`, `AppPageChrome`, `CollapsibleCard`, `PollingIndicator`, `LoadingFeedbackPanel` |
| `components/experiment/` | `ExperimentControlButtons`, `ExperimentProgressCard`, `ConfirmDeleteModal`, `experimentDetailProgress` |
| `components/stats/` | `VectorDbStatsPanel`, `ExperimentVectorDbStatsCard` |

Update `App.tsx` imports; move each `*.test.tsx` **with** its module (same folder).

### 4b. Frontend Code Complete / composition backlog (parked from Slice 44 standing assessment)

> Source: post–Slice 44 Code Complete + craft review (2026-07-27). Coverage gates already pass (#142); this work improves **construction**, not floors.

#### Baseline (debt inventory)

| Hotspot | Approx size | Craft issue |
|---------|-------------|-------------|
| `ExperimentDetailScreen.tsx` | ~1715 lines | God screen — fetch, polling, badges, pagination, copy in one module |
| `SearchExplorerScreen.tsx` | ~1200 lines | Same; high `else` / nest depth |
| `ExperimentsScreen.tsx` | ~867 lines | Same |
| Co-located `*.test.tsx` for above | ~1070–1577 lines each | Mega-suites; factories not shared |
| Utils / chrome / services | mostly ≤250 lines | **Healthy** — leave alone unless touched |

#### Rule-of-3 extracted (Should — do before or with screen shrink)

| Primitive | Current copies | Proposed home |
|-----------|----------------|---------------|
| `Pagination` | ExperimentsScreen, ExperimentDetailScreen, SearchExplorerScreen (×3) | `components/chrome/Pagination.tsx` (or `components/shared/`) |
| `StatTile` + `Row` | VectorDbStatsPanel, ExperimentVectorDbStatsCard (×2) | `components/stats/StatTile.tsx` (+ `Row`) |
| `append*Feed` | `appendFeed` / `appendDetailFeed` / `xfAppend` (×3) | `utils/feedEntries.ts` or chrome helper |
| `completionReasonLabel` | ExperimentsScreen + ExperimentDetailScreen (×2; third touch → extract) | `utils/completionReason.ts` (or extend `experimentStatus.ts`) |

Each extracted primitive: independently usable + unit/RTL tests; screens import and compose.

#### Screen SLAP targets (Should)

For each of the three screens:

1. Extract presentational subtrees (badges, outcome banners, tables) into siblings under `screens/` or `experiment/`.
2. Extract polling / list-refresh / control-refresh into named hooks (`useExperimentListPoll`, `useDetailPoll`, …) — **inject** deps (api client), do not reach singletons.
3. Prefer early returns / table-driven status maps over deep `else` chains.
4. Exit criteria (informational, not a hard CI gate): each screen file trending toward **≤400 lines** (stretch ≤200 Object Calisthenics ideal); max brace nesting ≤4 where practical.
5. Keep FE **95/90/95/95** floors green after every extract PR.

#### Shared test helpers (Should)

| Today (duplicated) | Target |
|--------------------|--------|
| `experiment()` / lifecycle fixtures in ExperimentsScreen.test | `frontend/src/test/helpers/experiments.ts` |
| `vectorDbGroup()` / stats fixtures | `frontend/src/test/helpers/vectorDbStats.ts` |
| `buildConfig` / `buildDetailedResult` in SearchExplorerScreen.test | `frontend/src/test/helpers/explore.ts` |
| Detail `run()` / `detailFixture()` / `dbStats*` | `frontend/src/test/helpers/experimentDetail.ts` |

Rules: named builders with `Partial<>` overrides; `ANY_*` for irrelevant fields; no shared mutable state across tests. Mega-suite shrink is a **consequence** of smaller screens + shared helpers — do not delete behavioral coverage.

#### Explicitly out of Slice 45 (Won't / later)

- Product coverage floor raises; Stryker/mutation for UI screens
- TanStack Query / Zustand redesign for dashboard data fetching
- Literal 100% branch coverage on every UI edge

### 5. `scripts/` (Could)

| Destination | Modules |
|-------------|---------|
| `scripts/ci/` | `quality-gates.sh`, `pre-push-gates.sh`, `repo-lint.sh`, `check_integrity.py`, `install-git-hooks.sh`, `pip-audit.sh` |
| `scripts/docker/` | `health-check.sh`, `docker-build-context.sh`, `docker-cleanup.sh`, `wait-experiment.sh`, `aim-ui.sh` |
| `scripts/release/` | `release.sh`, `bump_version.py`, `create_github_releases.sh`, `push_tags_incrementally.sh` |
| `scripts/security/` | `security-scan.sh` |
| Keep | `scripts/lib/` |

Update `.pre-commit-config.yaml`, `CLAUDE.md`, hooks, and CI path references.

---

## Re-export deprecation lifecycle

If thin `__init__.py` re-exports keep old import paths during a transition:

| Field | Policy |
|-------|--------|
| Old path example | `from server.core.orchestrator import …` |
| New path example | `from server.core.pipeline.orchestrator import …` (or package re-export) |
| Deprecation window | Active through the **next minor** after the move PR merges (document exact version in CHANGELOG) |
| Signal | `DeprecationWarning` on old import **or** CHANGELOG “Deprecated” + CLAUDE Key Files updated same PR |
| Removal | Hard-remove re-exports in the **following** minor (pre-1.0: still next minor); Decision Log row |
| Gate | After-Checks require CHANGELOG + Decision Log when re-exports are used |

---

## GWT Specs

```
Scenario: Core theme packages resolve without behaviour change
  Given modules moved under server/core/{pipeline,embedding,rerank,retrieval,guards}
  When the unit pytest suite and import smoke run
  Then the unit-tier suite stays green (reference: ≥322 tests at 2026-07-26 baseline; no intentional test deletions)
  And no HTTP/CLI contract changes (smoke: healthz / rag-params-finder version / indexes list)

Scenario: DB ports and backends remain selectable
  Given storage modules under db/ports, db/mongo, db/postgres
  When STORAGE_BACKEND is mongodb or postgres
  Then store_factory and /healthz behave as before

Scenario: Frontend component tests remain co-located after move
  Given ExperimentsScreen.tsx moved to components/screens/
  When npm run test
  Then ExperimentsScreen.test.tsx lives in components/screens/ (same folder)
  And App.tsx imports reference the new path
  And rg finds no dangling imports from the old components/ root for moved modules

Scenario: Shared Pagination composes without behaviour change
  Given Pagination extracted from the three screens into a shared chrome module
  When list / detail / explorer pagination interactions run under Vitest
  Then page changes and items-per-page behave as before
  And only one Pagination implementation remains under components/

Scenario: Screen extract keeps coverage floors
  Given presentational pieces or hooks are extracted from ExperimentDetailScreen (or a sibling screen)
  When npm run test:coverage
  Then FE thresholds 95/90/95/95 still pass
  And the screen module line count is materially lower than the pre-extract baseline

Scenario: Shared test helpers replace duplicated factories
  Given experiment/vectorDb/explore builders live under frontend/src/test/helpers/
  When screen tests import those helpers
  Then local copy-pasted factory definitions are removed from the mega-suites
  And suite behaviour (pass/fail) is unchanged

Scenario: Orchestrator façade stays thin after pipeline extract
  Given sweep / bayesian / run-lifecycle helpers live under server/core/pipeline/
  When the unit pytest suite and orchestrator-related tests run
  Then public experiment execution behaviour is unchanged
  And orchestrator.py (or pipeline façade) is materially smaller than the ~1161-line baseline
  And BE coverage floors 95/90/n/a/95 still pass

Scenario: Mega-suite split preserves behaviour
  Given test_slice16_parallel_sweep scenarios are redistributed into focused modules
  When the unit-tier pytest suite runs
  Then previously covered behaviours still pass
  And no intentional test deletions occurred for coverage cosmetics
```

---

## Before-Checks [GATE]

- [x] Confirm [`module-theme-map.md`](../../../contributor-guide/module-theme-map.md) lists five hotspots (**IMPLEMENTED** taxonomy §3) — verified 2026-07-27 (core, db, components, tests, scripts)
- [x] Slice 44 theme map + this stub reviewed; Reuse Analysis table accepted — architect APPROVED iter2 (#145); Declared Imports + forbidden-roots present
- [x] Branch `slice/45-module-theme-separation` created
- [x] Baseline `./scripts/ci/quality-gates.sh` green before first move (includes FE/BE #142 floors) — **VERIFIED 2026-07-27** exit 0 on branch `slice/45-module-theme-separation`
- [x] Run blast-radius `rg` commands above; record caller list in PR body — **2026-07-27 baseline:** `server.core` ≈**112** import match-lines (top: `test_sie_embedder` 12, `orchestrator` 11, `experiments` 9); `server.db` ≈**67**; FE `components/` imports concentrated in `App.tsx` (3)
- [x] Audit CLI import points (`cli/indexes_cmd.py`, `cli/main.py`, …) for the hotspot being moved — `indexes_cmd` → `search_index_guard` / `search_index_plan` / `db.atlas` / `db.indexes`; `config_loader` → `model_registry` (stays at `core/` top-level)
- [x] Choose phase 1 hotspot — **`server/core/` + orchestrator SLAP**; first PR skateboard = **`core/guards/`** move (CLI + preflight touchpoints) then **`pipeline/`** extract from `orchestrator.py` (not all of `core/` in one PR)
- [x] If a hotspot needs >200 import rewrites, split further — core match-lines **112 &lt; 200**; still split by package (`guards/` → `pipeline/` → `embedding/` …) per one-hotspot-per-PR
- [x] For FE craft phases: record pre-extract line counts for the three screens + locate Rule-of-3 copies — Screens: Experiments **867**, Detail **1715**, SearchExplorer **1200**. Copies: `Pagination`×3 screens; `completionReasonLabel` in Experiments+Detail; `appendFeed` in Experiments; `StatTile` in VectorDbStatsPanel + ExperimentVectorDbStatsCard
- [x] For BE craft phases: record pre-extract line counts for `orchestrator.py`, `experiments.py`, `cli/main.py` + list functions >80 lines; note mega-suite line counts — orchestrator **1161** (`_run_single` 217, `_run_sweep_inner` 195, `_run_bayesian_inner` 185, `_finalise_bayesian_experiment` 101); experiments **549** (`create_experiment` 85); cli/main **519** (`_print_summary` 103); mega: `test_slice16_parallel_sweep` **2296**, `test_mongo_store_acceptance` **748**, `test_search_index_guard` **659**

---

## After-Checks [GATE]

- [x] At least Must items for chosen phase(s) landed with green gates — **VERIFIED 2026-07-28** `./scripts/ci/quality-gates.sh` exit 0 (HEAD `be4a0d6`)
- [x] Specification coverage: every GWT clause has ≥1 test (BDD/GWT-first, §2); essential error paths covered (90–100% of clauses) — characterization suites relocated under `tests/server|cli|scripts/`; Slice 16 scenarios retained under `tests/server/core/pipeline/`
- [x] Branch coverage: product floors stay green (FE **95/90/95/95**, BE **95/90/n/a/95** — DECISIONS #142); tool fail_under configured; whole-tree 100% branch Won't (§12 — test-writing-craft-quality.mdc) — measured BE 98.60/95.21/98.60; FE 98.4/93.11/100/99.69
- [x] Mutation testing run if slice adds non-trivial pure logic: survival budget met; else waive with Decision Log row (§23 / #128 pattern) — **waived** DECISIONS #160 (nightly CI)
- [x] `module-theme-map.md` updated to IMPLEMENTED paths (or note SUPERSEDED proposals) — sync-docs 2026-07-28; hotspots 1–5 **IMPLEMENTED** (incl. `scripts/`)
- [x] CLAUDE.md Key Files paths updated
- [x] CHANGELOG Unreleased — internal layout note (+ FE/BE craft notes when primitives/pipeline land)
- [x] If re-exports used: CHANGELOG Deprecated + Decision Log row with version window + removal trigger — server shims #146–#152; scripts flat shims #159 (+ Deprecated bullets)
- [x] `docs/plan/gate-evidence/slice-45.json` written
- [x] Optional smoke: `./scripts/ci/quality-gates.sh` + `rag-params-finder version` / healthz `storage_mode` unchanged — version `0.11.0`; healthz `postgres-local` ok
- [x] FE craft phases: shared primitives have tests; no duplicate Pagination/StatTile/Feed helpers left in screens; FE **95/90/95/95** still green
- [x] FE craft phases: shared `test/helpers` used by moved/shrunk suites; Decision Log notes pre→post screen line counts (#156) + helpers (#158)
- [x] BE craft phases: orchestrator/pipeline split green; Protocols + factories unchanged; BE **95/90/n/a/95** still green; Decision Log notes pre→post orchestrator line counts
- [x] BE craft phases (when claimed): mega-suite split or fat-surface slim landed without intentional coverage loss
- [x] FE craft phases (when claimed): screen SLAP extracts landed; Decision Log notes pre→post screen line counts (Detail 1615→986, Experiments 764→670, Explorer 1131→426)

---

## Execution order (recommended)

1. `server/core/` thematic move **paired with** orchestrator SLAP extract into `pipeline/` (highest cognitive load)
2. `server/db/` ports + backends (preserve Protocols; optional indexes slim only if in path)
3. Fat-surface slim: `experiments.py` / `cli/main.py` (can follow db or interleave after API import paths stable)
4. `tests/` mirror + mega-suite split (after import paths stable)
5. **FE shared primitives** (`Pagination`, stats tiles, feed append, completionReason) — prefer **before** bulk FE folder move
6. **FE screen SLAP** extracts — keep floors green
7. `frontend/src/components/` folder split + co-located tests
8. **FE shared test helpers** + mega-suite shrink (parallel with 5–7)
9. `scripts/` (last — many path references in hooks/docs); optional `start-services.sh` lib extract
10. Could: FE docstring leftovers; FE↔pyproject drift guard; BE GWT-on-touch migration

One hotspot / one craft theme per PR when possible.

---

## Gate Status

✅ COMPLETE — Must + Should + scripts Could + deferred Could leftovers (#161: FE docstrings, coverage drift guard, BE GWT-on-touch) landed; After-Checks closed 2026-07-28; evidence [`slice-45.json`](../../gate-evidence/slice-45.json); mutation waived #160; nw-software-crafter-reviewer close-out **APPROVED**.

## Remediation pass (2026-07-27)

Applied nw-solution-architect HIGH + nw-documentarist medium findings (DECISIONS #137): Reuse Analysis, re-export lifecycle, blast-radius `rg`, quantified GWT, frontend colocation GWT, CLI Before-Checks, taxonomy IMPLEMENTED pre-condition, keep-at-`core/` wording.

**Superseding architect verdict: APPROVED** for phased execution after this pass.

## Scope addendum (2026-07-27) — FE + BE Code Complete backlog

**FE** (post–Slice 44 standing assessment + nw-software-crafter-reviewer non-blocking notes):

- Shared UI primitives (Rule of 3)
- Screen SLAP / size / nesting
- Shared test factories + suite shrink
- Could: docstring migration leftovers; coverage threshold drift guard
- Won't: higher floors, mutation on screens, TanStack Query rewrite

**BE** (post–backend standing assessment, exclude FE):

- Orchestrator SLAP into `pipeline/` (god module ~1161)
- Fat-surface slim: `experiments.py`, `cli/main.py` (+ optional `indexes.py` / `postgres_store` helpers)
- Mega-suite shrink + GWT-on-touch; mirror `tests/` layout
- Preserve Ports/factories/`stats_common`; keep Mongo∥Postgres twins (#129)
- Could: scripts/`start-services` further extract; BE test docstring migration on touch
- Won't: whole-tree 100% coverage; merge dual backends; local mutation gate beyond #128

Re-approve only if Must Python move tables change; FE/BE Should/Could addenda do not invalidate #137 architect APPROVED for core/db moves.

## Related

- [`module-theme-map.md`](../../../contributor-guide/module-theme-map.md)
- [`SLICE-44-FRONTEND-COVERAGE-GATE.md`](SLICE-44-FRONTEND-COVERAGE-GATE.md) §3 + nw-review APPROVED
- DECISIONS #135, #137, #142 (#129 dual-backend independence)
- PR #121 (Slice 44 delivery)

---

## Architecture Review — nw-solution-architect-reviewer

**Review ID:** arch_review_2026_07_27_slice45
**Reviewer:** nw-solution-architect-reviewer
**Iteration:** 1
**Date:** 2026-07-27

### Verdict

**Status:** CONDITIONALLY APPROVED 🟡 → **superseded APPROVED** after remediation pass 2026-07-27 (#137)

Roadmap is architecturally sound and execution-ready. Original 2 HIGH findings (Reuse Analysis + re-export lifecycle) addressed in body above.

### Roadmap Quality Summary

| Check | Result | Notes |
|-------|--------|-------|
| **1. External Validity** | ✓ PASSED | All moves preserve HTTP/CLI/YAML contracts; internal-only refactoring |
| **2. AC Implementation Coupling** | ✓ PASSED | GWT specs behavioral, not implementation-prescriptive; observable outcomes focus |
| **3. Step Decomposition Ratio** | ✓ PASSED | 25–30 steps ÷ 126 files ≈ 0.24; well under 2.0 threshold |
| **4. Implementation Code in Roadmap** | ✓ PASSED | No pseudocode, algorithms, or variable names; structure only |
| **5. Concision & Precision** | ✓ PASSED | ~1050 words (within 3000 threshold for 5-hotspot roadmap); per-hotspot clarity crisp |
| **6. Unit Test Boundary Validation** | ✓ PASSED | Tests invoke through stable public APIs; test contract preserved |

### Strengths

- **Execution order respects dependency depth:** Core → db → tests → frontend → scripts. Smart risk sequencing.
- **MoSCoW prioritization pragmatic:** Must items (core + db) highest cognitive relief; Could items (scripts) optional polish.
- **Blast radius annotations thoughtful:** Line 47, 57 pre-flag factory wiring and import smoke. Forward planning signal.
- **Theme map evidence-based:** Hotspot ranking in Slice 44 quantified by file count + cognitive-load labels.
- **GWT specs are crafter-friendly:** Behavioral specs, not structure-prescriptive; allows TDD freedom during execution.

### Issues Identified

#### HIGH Issues (Must Fix Before Execution)

**Issue 1: Reuse Analysis Table with Declared Imports Cell Required (F-D-09 Forbidden-Import-Roots Validation)**

- **Severity:** HIGH (design-time gate per nwave feedback_target_machine_independence_2026_05_15)
- **Location:** SLICE-45 lines 33–90 (proposed move tables)
- **Finding:** Roadmap proposes moves but omits Reuse Analysis table enumerating Source→Target, Decision, Justification, and **Declared Imports** (for forbidden-roots check: no `from scripts.*` or `from tests.*` in `src/des/**` modules). During execution, risk of silent import-root violations or overlapping component omissions.
- **Recommendation:** Add Reuse Analysis table before slice execution:
  ```markdown
  | Destination | Source Files | Decision | Justification | Declared Imports (if CREATE_NEW) |
  |--|--|--|--|--|
  | `server/core/pipeline/` | orchestrator.py, executors.py, ... | MOVE | Consolidate behavior group; reduce SLAP | from server.models, server.db.ports (no scripts/tests roots) |
  | `server/db/ports/` | storage.py, retriever_backend.py, ... | CREATE_NEW (extraction) | Extract protocol boundary; Mongo + Postgres adapt | from server.models, typing (no scripts/tests roots) |
  ```
  This forces upfront import-scope declaration and catches root-module violations **before** moving files.

**Issue 2: Re-export Strategy Deprecation Lifecycle Underspecified**

- **Severity:** HIGH (public API stability concern)
- **Location:** SLICE-45 line 47 ("Prefer thin `__init__.py` re-exports for one release if import churn...")
- **Finding:** Re-export strategy mentions keeping old imports "for one release" but does NOT specify removal timeline, version string, or deprecation signal. Risk: callers indefinitely depend on old paths if not explicitly deprecated.
- **Recommendation:** Add to After-Checks section:
  ```
  - [ ] If re-exports added for churn mitigation, create ADR or CHANGELOG entry:
        * Old path: from server.core import orchestrator
        * New path: from server.core.pipeline import orchestrator
        * Deprecation: Active in v1.X, removal in v2.0 (explicit version)
        * Removal trigger: deprecation warning on import, or hard removal per ADR
  ```

#### MEDIUM Issues (Clarify During Execution, Not Blocking)

**Issue 3: Frontend Test Colocation & App.tsx Wiring Underspecified**

- **Severity:** MEDIUM (implementation clarity)
- **Location:** SLICE-45 line 77 ("Update App.tsx imports; keep colocation of *.test.tsx")
- **Finding:** Terse directive risks broken colocation (test left in old location) or dangling route imports.
- **Recommendation:** Expand to explicit GWT before implementation:
  ```
  Scenario: Frontend component tests remain co-located after move
    Given ExperimentsScreen.tsx moved to components/screens/
    When npm run test
    Then ExperimentsScreen.test.tsx is in components/screens/ (same folder)
    And App.tsx lazy-load routes reference new path
    And no dangling imports from old path found
  ```

**Issue 4: CLI Integration Points Underspecified**

- **Severity:** MEDIUM (operational clarity)
- **Location:** SLICE-45 line 57 (db/ blast radius) & line 89 (scripts/ paths)
- **Finding:** CLI `indexes` command must keep working, but import rewrites (cli/indexes_cmd.py → server.db.* paths) not enumerated.
- **Recommendation:** Add Before-Checks item identifying all CLI callers:
  ```
  - [ ] Audit CLI import points:
    * cli/indexes_cmd.py → imports server.db.mongo, server.db.postgres
    * cli/config_loader.py → imports server.models.config
    * cli/main.py → imports all CLI modules
    * Ensure each gets updated in corresponding move PR
  ```

### Architectural Critique — Dimensions 1–5

**Dimension 1: Architectural Bias Detection** ✓ PASSED
- No technology preference bias (organizational move, not tech adoption)
- No resume-driven complexity (splits justified by SLAP + theme map)
- Not applicable to brownfield hygiene

**Dimension 2: ADR Quality** — Not applicable (roadmap is execution, not strategic decision)
- Context provided by Slice 44 theme map (taxonomy + justification)
- ADR not required for refactoring-only moves

**Dimension 3: Completeness** ✓ PASSED
- All quality attributes addressed: maintainability ↑, modularity ↑, testability stable, portability stable
- No attribute degraded

**Dimension 4: Implementation Feasibility** ✓ PASSED
- Team capability: mechanical refactoring within Python/TypeScript proficiency
- Risk: import churn (mitigated by re-export strategy)
- Testability: existing test structure preserved

**Dimension 5: Priority Validation** ✓ PASSED
- Q1 (largest bottleneck): YES — file count + cognitive-load data from Slice 44 hotspot table
- Q2 (simpler alternatives): ADEQUATE — flat vs split rationale in theme map
- Q3 (constraint prioritization): CORRECT — execution order respects dependency depth
- Q4 (data-justified): JUSTIFIED — quantified hotspot ranking

### Count Summary

- **Critical Issues:** 0
- **High Issues:** 2 (both documentation-phase, no code blocking)
- **Medium Issues:** 2 (clarification during execution, not blocking)
- **Low Issues:** 0

### Approval Conditions

**Conditional GO** — Slice execution can proceed once:

1. ✅ HIGH Issue 1: Add Reuse Analysis table with Declared Imports cell to SLICE-45
2. ✅ HIGH Issue 2: Document re-export deprecation lifecycle in After-Checks or ADR

Both are **zero-code** artifact updates (no implementation needed before approval). Recommendation: update SLICE-45 immediately, then proceed with execution.

### Reviewer Notes

- **Execution sequence is exemplary:** dependency-order moves reduce risk of cascading import failures.
- **MoSCoW discipline is tight:** Could items are genuinely optional; Must items are high-impact.
- **Slice 44 foundation solid:** theme map provides quantified evidence; Slice 45 is well-grounded.
- **Re-export mitigation is smart:** one-release bridge softens import churn impact on callers.

**Complementary review:** After-execution, verify import smoke tests catch all transitional paths and re-export deprecation is signaled clearly (e.g., `DeprecationWarning` in `__init__.py` re-exports).

---

**Review completed by:** nw-solution-architect-reviewer
**Approval:** CONDITIONALLY APPROVED (pending 2 HIGH-issue resolutions) → **APPROVED** after #137 remediation (Reuse Analysis + deprecation lifecycle landed in stub body)

---

## Architecture Review — nw-solution-architect-reviewer (ITERATION 2)

**Review ID:** arch_review_2026_07_27_slice45_iter2
**Reviewer:** nw-solution-architect-reviewer
**Iteration:** 2
**Date:** 2026-07-27 (resumed, post–Gap 8 health-check)

### Verdict

**Status:** ✅ **APPROVED** 🟢

Roadmap is execution-ready. All prior HIGH findings remediated in artifact (Reuse Analysis + deprecation lifecycle present). Gap 8 insertions (DECISIONS #143) are aligned. No blocking issues.

### Roadmap Quality Summary (Iteration 2)

| Check | Result | Notes |
|-------|--------|-------|
| **1. External Validity** | ✓ PASSED | All moves preserve HTTP/CLI/YAML contracts; internal refactoring only |
| **2. AC Implementation Coupling** | ✓ PASSED | GWT specs behavioral; no underscore prefixes, method signatures, or HOW prescriptions |
| **3. Step Decomposition Ratio** | ✓ PASSED | ~25–30 steps ÷ 126 files ≈ 0.20–0.24; well under 2.0 threshold |
| **4. Implementation Code in Roadmap** | ✓ PASSED | No pseudocode, algorithms, or variable names; structure only |
| **5. Concision & Precision** | ✓ PASSED | ~1050 words (within 3000 threshold for 5-hotspot roadmap) |
| **6. Unit Test Boundary Validation** | ✓ PASSED | Tests invoke stable public APIs; behavioral focus preserved |

### Strengths (Iteration 2)

- **Remediation complete:** Reuse Analysis table (lines 49–65) includes Declared Imports cell + forbidden-roots validation.
- **Re-export strategy documented:** Deprecation lifecycle (lines 250–262) specifies version windows + removal triggers.
- **Gap 8 insertions aligned:** Specification coverage, branch floors, mutation pattern all consistent with roadmap scope (lines 338–340).
- **Before-Checks mature:** **1/10** ticked on resume (theme-map hotspots); next gates are #2–3 (Reuse Analysis acceptance + branch) then baseline gates / phase-1 choice.
- **MoSCoW discipline maintained:** Must moves (core, db) unambiguous; Should/Could items clearly optional.
- **Execution order risk-minimized:** dependency-graph ordering (core → db → tests → FE → scripts) reduces cascading import failures.

### Issues Identified (Iteration 2)

**CRITICAL:** 0
**HIGH:** 0 (both #137 findings resolved)
**MEDIUM:** 0 (peer-review findings all applied)
**LOW:** 0

### Approval Conditions Met

✅ Reuse Analysis + Declared Imports cell present
✅ Re-export deprecation lifecycle documented
✅ Gap 8 insertions (DECISIONS #143) aligned
✅ All 6 roadmap checks PASSED
✅ All 5 architectural dimensions PASSED
✅ Before-Checks status clear (**1/10** complete at resume; not a review blocker)

**Execution Status:** Ready for phased rollout after remaining Before-Checks (esp. #2–3: Reuse Analysis acceptance + branch creation).

> **Parent correction (orchestrator):** Iter-2 draft incorrectly said “8/11 Before-Checks complete.” Live checklist at resume was **1/10** `[x]` — do not treat FE/BE craft Before-Checks as already satisfied. (Subsequent Before-Checks closed 2026-07-27 except baseline quality-gates.)

## 📋 Peer Review (2026-07-27)

| Dimension | Finding | Severity | Recommendation |
|-----------|---------|----------|-----------------|
| **Scope clarity** | Depends on Slice 44 (PLANNED); execution risk if Slice 44 taxonomy changes | Medium | Add explicit gate to Before-Checks: "Verify Slice 44 module-theme-map.md status = IMPLEMENTED before starting" — **APPLIED #137** |
| **Move table language** | Tables 1–2 say "Keep at `core/` or `core/catalog/`" (ambiguous) vs Table 1 line 45 "Keep" (inconsistent) | Low | Normalize: "Keep at `core/` top-level (not moved)" — **APPLIED #137** |
| **Blast radius depth** | Section 1–2 list callers but do not provide verification command | Medium | Add `rg` blast-radius commands — **APPLIED #137** |
| **GWT acceptance criteria** | "All prior tests pass" not quantified | Medium | Quantified unit-tier baseline — **APPLIED #137** |
| **GWT verification** | "No HTTP/CLI contract changes" not actionable | Medium | Smoke After-Check added — **APPLIED #137** |
| **Before-Checks** | Missing pre-condition: Slice 44 status | Low | Taxonomy IMPLEMENTED checkbox — **APPLIED #137** |
| **After-Checks schema** | `gate-evidence/slice-45.json` referenced but no schema | Low | Follow slice-44.json pattern when writing evidence |
| **Hotspot churn** | "One hotspot per PR" rule does not address import rewrite volume | Low | >200 rewrites split guidance — **APPLIED #137** |

**Verdict: APPROVED** (remediation #137 applied)

Rationale:
- Scope, MoSCoW ranking, and execution order are clear and well-justified.
- Move tables are complete and actionable; ambiguities are language-only, not structural.
- GWT scenarios are present; acceptance criteria need minor clarification before test runs.
- Medium-priority recommendations are polish/safety, not blockers — can be applied during execution prep.

**Approval Status: APPROVED** ✅
**Revision Cycle: 1** (remediation pass 2026-07-27)
