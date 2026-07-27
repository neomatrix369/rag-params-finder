# Slice 45: Module Theme Separation

> Scenario: Brownfield + Growing Requirement (Flow D) | MoSCoW: Could

**Target time:** ~4–6 h (phased by hotspot; do not do all five in one commit)
**Status:** 📋 PLANNED
**Depends on:** Slice 44 taxonomy Should artifacts **IMPLEMENTED** — [`module-theme-map.md`](../../contributor-guide/module-theme-map.md) present with B/F/F tags; canvas published; this stub present. *(Slice 44 coverage Must need not be COMPLETE.)*
**Non-blocking:** Structural hygiene — does not gate PCTO / migration Must slices.

**Origin:** Spun from Slice 44 Should audit on 2026-07-27 (DECISIONS #135). Slice 44 publishes proposals only; **this slice owns filesystem moves and import rewrites**.

---

## Goal

Execute ranked folder separations so Behavior / Feature / Function themes live in dedicated directories (fewest elements that reveal intent — Simple Design). Preserve public API / CLI / HTTP contracts; change **internal** import paths only.

---

## MoSCoW

| Priority | Item |
|----------|------|
| **Must** | Move `server/core/` into thematic subpackages with stable re-exports or updated imports; tests green |
| **Must** | Move `server/db/` into `ports/` + `mongo/` + `postgres/` (or equivalent); factory still resolves backends |
| **Should** | Reorganize `tests/` to mirror packages or `unit/` + existing `contract/` / `helpers/` |
| **Should** | Split `frontend/src/components/` into `screens/` / `chrome/` / `experiment/` / `stats/` |
| **Could** | Split `scripts/` into `ci/` / `docker/` / `release/` / `security/` (+ keep `lib/`); update gate script paths |
| **Won't** | Rename public CLI commands, HTTP routes, or config YAML keys; delete Mongo or Postgres backends; whole-repo monorepo reshape |

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

### 4. `frontend/src/components/` (Should)

| Destination | Modules |
|-------------|---------|
| `components/screens/` | `ExperimentsScreen`, `ExperimentDetailScreen`, `SearchExplorerScreen` (+ tests) |
| `components/chrome/` | `DashboardShell`, `AppPageChrome`, `CollapsibleCard`, `PollingIndicator`, `LoadingFeedbackPanel` |
| `components/experiment/` | `ExperimentControlButtons`, `ExperimentProgressCard`, `ConfirmDeleteModal`, `experimentDetailProgress` |
| `components/stats/` | `VectorDbStatsPanel`, `ExperimentVectorDbStatsCard` |

Update `App.tsx` imports; move each `*.test.tsx` **with** its module (same folder).

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
```

---

## Before-Checks [GATE]

- [ ] Confirm [`module-theme-map.md`](../../contributor-guide/module-theme-map.md) lists five hotspots (**IMPLEMENTED** taxonomy §3)
- [ ] Slice 44 theme map + this stub reviewed; Reuse Analysis table accepted
- [ ] Branch `slice/45-module-theme-separation` created
- [ ] Baseline `./scripts/quality-gates.sh` green before first move
- [ ] Run blast-radius `rg` commands above; record caller list in PR body
- [ ] Audit CLI import points (`cli/indexes_cmd.py`, `cli/main.py`, …) for the hotspot being moved
- [ ] Choose phase 1 hotspot (`server/core/` recommended)
- [ ] If a hotspot needs >200 import rewrites, split further (e.g. `core/embedding/` then `core/pipeline/`)

---

## After-Checks [GATE]

- [ ] At least Must items for chosen phase(s) landed with green gates
- [ ] `module-theme-map.md` updated to IMPLEMENTED paths (or note SUPERSEDED proposals)
- [ ] CLAUDE.md Key Files paths updated
- [ ] CHANGELOG Unreleased — internal layout note
- [ ] If re-exports used: CHANGELOG Deprecated + Decision Log row with version window + removal trigger
- [ ] `docs/plan/gate-evidence/slice-45.json` written
- [ ] Mutation: waive unless non-trivial logic added; Decision Log row
- [ ] Optional smoke: `./scripts/quality-gates.sh` + `rag-params-finder version` / healthz `storage_mode` unchanged

---

## Execution order (recommended)

1. `server/core/` (highest cognitive load)
2. `server/db/`
3. `tests/` mirror (after import paths stable)
4. `frontend/src/components/`
5. `scripts/` (last — many path references in hooks/docs)

One hotspot per PR when possible.

---

## Gate Status

📋 PLANNED

## Remediation pass (2026-07-27)

Applied nw-solution-architect HIGH + nw-documentarist medium findings (DECISIONS #137): Reuse Analysis, re-export lifecycle, blast-radius `rg`, quantified GWT, frontend colocation GWT, CLI Before-Checks, taxonomy IMPLEMENTED pre-condition, keep-at-`core/` wording.

**Superseding architect verdict: APPROVED** for phased execution after this pass.

## Related

- [`module-theme-map.md`](../../contributor-guide/module-theme-map.md)
- [`SLICE-44-FRONTEND-COVERAGE-GATE.md`](SLICE-44-FRONTEND-COVERAGE-GATE.md) §3
- DECISIONS #135, #137

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
