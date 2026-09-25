# SLICE 51 — Elasticsearch Operability, CI, Docs & ADR-006 (closeout)

**MoSCoW:** MUST
**Target time:** ~11–15 h (largest ES slice — feature closeout; may ship as 2 PRs: **51a** operability/surfaces, **51b** CI/docs/ADR — one branch)
**Status:** 📋 PLANNED
**Depends on:** 50 (ES adapter core) · 49A/49B (registry, two-store `/healthz`, pairing rule (ii))
**Branch:** `slice/51-elasticsearch-operability-ci-docs-adr`
**Feature:** Elasticsearch vector-store adapter (ADR-006)

> **Merge note (2026-09-24, DECISIONS #218):** fuses the former Slices 51 (operability) + 52 (CI/docs/ADR). Elasticsearch is genuinely simpler than Postgres (no schema-DDL slice, no cloud/local-parity slice — D5 makes pairing a flag), so its closeout collapses to one slice. Optional 2-PR split (51a surfaces / 51b CI+docs+ADR) keeps each PR reviewable without re-fragmenting the plan. Pasted spec's "Slice 50 + 51".
>
> **Amendment (2026-09-25, DECISIONS #240–#249):** the round-3 desk-check found gaps that would break the local Docker path and the docs journey:
> - the server image installed no extras, so it had no ES client;
> - compose never passed the new settings to the server;
> - "manifest-driven scripts" had no shell-readable manifest;
> - the 15-stage journey was never written down;
> - `invariants.md` had none of the rules this slice pointed to;
> - no backend had a teardown section.
>
> Owner decisions applied here: Dockerfile build ARG `EXTRAS` (#243), `scripts/lib/stores.tsv` + parity test (#244), one nightly matrix job (#248). Two-store `/healthz` semantics come from 49B (#247).

---

## Context

Makes the ES store operable, proven, and documented end-to-end from a clean clone: Docker profile + scripts + `GET /api/stores` + configs + registry-driven FE labels (E2E journey stages 5–8, 10, 14), the nightly ES integration job, the full 15-stage user journey in docs with a **registry-driven docs-parity gate** (the docs equivalent of the contract suite), and `ADR-006`. "Done" = a fresh reader goes from "which backend?" to results-in-dashboard to teardown using docs + scripts alone, for ES exactly as for Mongo/Postgres.

- **Depends-on outputs:** ES adapter `stats()`, `labels()`, `capabilities()`, `search()` from Slice 50; the registry from Slice 49 (drive scripts, health-check, docs-parity, and `/api/stores` from the manifest — ES is one entry, not four edits).
- **Invariants pointer:** `docs/plan/invariants.md` § Vector store / split-store — local ES pairs with a run-state store (D5, default `postgres-local`; any pairing must satisfy rule (ii), #241); Basic-licence single-node, security off, `127.0.0.1`; 1 GB heap; dashboard read-only; cross-backend comparability (same YAML, only the vector store changed, comparable dense scores on Mongo/Postgres/ES).

## Non-goals

- New retrieval features or sweep axes; server-side fusion; Elastic Cloud setup automation; frontend store-*selection* UI.
- Changing the default store (stays `mongodb`).
- New per-store branches in scripts — ES must be **one manifest entry**, not four script `case` edits.

## Output contract

**Operability / surfaces (was Slice 51):**
- `docker-compose.yml` profile `elasticsearch-local` (pinned 9.5.x, single-node, `xpack.security.enabled=false`, `xpack.license.self_generated.type=basic`, `-Xms1g -Xmx1g`, named volume, `/_cluster/health` healthcheck, `127.0.0.1` binding, `required: false` in `server.depends_on`).
- `start-services.sh --elasticsearch-local | --elasticsearch-cloud` + `elasticsearch start|stop|reset|status`; `scripts/lib/compose.sh` gains `RAG_LOCAL_ELASTICSEARCH_URL_HOST/_DOCKER` + container/volume constants; local mode also starts the run-state store (D5 default `postgres-local`).
- **Server image extras (#243):** `docker/server.Dockerfile:26` takes `ARG EXTRAS=""` and runs `uv sync --frozen --no-install-project ${EXTRAS:+--extra $EXTRAS}`; the `elasticsearch-local` / `-cloud` modes build with `EXTRAS=elasticsearch`. Default image unchanged in size.
- **Compose env pass-through:** the `server` service `environment:` passes `VECTOR_STORE_BACKEND: ${VECTOR_STORE_BACKEND:-}` (empty → defaults to `STORAGE_BACKEND` in settings), `ELASTICSEARCH_URL: ${RAG_SERVER_ELASTICSEARCH_URL:-${ELASTICSEARCH_URL:-}}` and `ELASTICSEARCH_API_KEY: ${ELASTICSEARCH_API_KEY:-}`. This follows the existing `RAG_SERVER_*` pattern (`docker-compose.yml:22,29`): `start-services.sh --elasticsearch-local` sets `RAG_SERVER_ELASTICSEARCH_URL` to the Docker-network URL, while cloud reads `ELASTICSEARCH_URL` from `.env`. Secrets come from `.env`, never the compose file.
- **Storage-mode resolver:** `scripts/lib/storage_mode.sh` gains the `elasticsearch-local` / `elasticsearch-cloud` tokens. They export `VECTOR_STORE_BACKEND=elasticsearch` and pair a run-state store (D5 default `postgres-local`, overridable by `STORAGE_BACKEND`). Choosing `elasticsearch` as the run-state store fails with the same vector-store-only message as the settings validator. The user sets no environment variables by hand for the local path.
- **Store manifest for scripts (#244):** `scripts/lib/stores.tsv` — one row per store: provider · compose profile · `--<x>-local` flag · health URL · required env vars · `can_host_run_state`. `start-services.sh`, `stop-services.sh` and `scripts/docker/health-check.sh` read it (bash 3.2-safe loops, guarded array expansion). A parity test asserts its providers equal `known_vector_stores()` from the Python registry.
- `configs/elasticsearch/*.yaml` — same 9 basenames as `configs/mongodb/`, `database_provider: elasticsearch`, prerequisite header comment (incl. run-state store).
- `GET /api/stores` — registry + capabilities + labels + active store, secrets redacted; CLI `indexes list` routes through it (fixes the ADR-001 thin-client leak for all stores).
- Frontend labels from adapter `labels()` (Index/Host) replacing `isMongoProvider()` — no new per-store branch; no quota bar for ES.
- `stats()` via `_count`/`_stats`; quota fields `None`.
- **Drift fixes:** (the `configs/supabase/*.yaml` provider label, the Mongo-only `/health` example and the Atlas-only `indexes reset` advice in `dashboard-guide.md` were fixed on 2026-09-25, DECISIONS #251) `stop-services.sh` iterates every `stores.tsv` local profile (today it handles Atlas only, via a deprecated env var, `stop-services.sh:16-21`); `health-check.sh` reads `/healthz` `stores{}` and reports each store from the manifest.
- **Orphan-vector reconciler:** if 49B deferred it (CF row), it lands here (Should, #246).

**CI / docs / ADR (was Slice 52):**
- **One nightly matrix job (#248):** `vector-store-integration` in `nightly.yml`, matrix over `{mongodb, postgres, elasticsearch}` (Redis joins in 53), each leg running the store + vector contract suites and the 49B split-store acceptance test where the store is vector-only. `RAG_REQUIRE_<STORE>=1` makes an unreachable store fail; a skipped leg fails the job (skipped ≠ green). The existing per-store live jobs fold into it.
- `docs/user-guide/elasticsearch-setup.md` structured like `postgres-setup.md` (11 sections: choose deployment → env vars → Path A local Docker → Path B bring-your-own → index lifecycle → before a sweep → smoke sweep → switching → **sizing** (float32 on disk + HNSW graph memory, 1 GB heap — from Slice 50 data-eng note) → troubleshooting → diagnostics cheat sheet).
- Journey docs: `QUICKSTART.md` Path E + verify line; `getting-started.md`; `configuration.md` (Engine × Location rows `elasticsearch-local`/`-cloud`, `VECTOR_STORE_BACKEND`, pairing rule (ii), env-asymmetry note); `cli-reference.md` (`/healthz` two-store shape replacing the Mongo-only example at line 216, `GET /api/stores`, **an `elasticsearch` row in the `indexes` table at lines 134-137**); `dashboard-guide.md` (ES row in the preflight-failed remediation); `troubleshooting.md` (ES: memory/`vm.max_map_count`, 401/TLS, **403 licence non-compliant**, refresh zero-hits, quantized preflight, dims mismatch, 422; env-var table gains ES rows); switching rows in `mongodb-setup.md` + `postgres-setup.md`; start-flag lists in `local-environment.md`, `development.md`, `AGENTS.md`, `CLAUDE.md`; `.env.example` ES block; `README.md`; `docs/README.md`.
- **Documentation homes (Diataxis):**
  - *Reference* — the **15-stage user journey** as a table in `extending.md` (stage · user action · command/surface · doc that covers it · test that proves it), so "full journey" is checkable.
  - *How-to* — "Add a vector store" checklist in `extending.md` (~15 items: registry entry, `VectorStore` composite, capabilities, settings + env, extra, Dockerfile `EXTRAS`, compose profile + env, `stores.tsv` row, configs dir, setup guide, QUICKSTART path, nightly matrix leg, split-store AT param, docs-parity pass, ADR).
  - *Explanation* — `architecture.md`: ports/adapters (C4 component) view and the split-store data flow from 49A/49B, extended with ES; the Mongo-only data-flow diagram gains the other stores.
  - *Tutorial* — `QUICKSTART.md` gains a **Teardown** section for every backend (stop, reset volumes), not just ES.
  - Each new section opens with one sentence saying what it is for and when to use it, so its role is clear in place.
- **Registry-driven docs-parity check** (generalises `tests/server/models/test_config_examples.py`): for every registered provider asserts setup-guide existence with **all 11 required sections**, that its relative links resolve, config-dir basename parity, and mentions in `.env.example`/`README`/`QUICKSTART` (path + teardown)/`docs/README`/`troubleshooting`/`cli-reference` `indexes` table + `start-services.sh --help` + a `stores.tsv` row. Wired into PR CI. A heading-only check would pass with empty sections, so the content rule is explicit: each required section must contain at least one non-empty paragraph, list or code block under its heading, and must not be only a placeholder (`TODO`, `TBD`, `Coming soon`).
- `docs/adr/ADR-006-elasticsearch-vector-store.md` (vector-only role, unquantized HNSW, client-side RRF licence rationale, refresh semantics; alternatives note — OpenSearch/Vespa/pgvector/Atlas — answering the architect's "why ES" without expanding code scope).
- `extending.md` updated to the registry flow **and** to require the full 15-stage journey for any new store (journey table + checklist above).
- `docs/plan/invariants.md` § Vector store / split-store rows verified against the shipped code (D5 pairing default, local-profile constraints).

## Reuse ledger (reuse-first — don't reinvent the wheel)

This closeout is almost entirely *extending existing operator surfaces and doc templates* — ES becomes one manifest entry, one config dir, one setup guide, one ADR, one CI job, each mirroring a proven Mongo/Postgres counterpart. The docs-parity gate **generalises an existing test** rather than adding a new one.

| Need | Existing code to reuse/extend | Action |
|---|---|---|
| Compose helpers + local/cloud URI constants | `scripts/lib/compose.sh` (`mongodb`/`postgres` subcommands + constants) | **Extend** — add ES constants + `elasticsearch` subcommand in the same shape |
| Four-flag storage-mode resolver | `scripts/lib/storage_mode.sh` | **Extend** — `elasticsearch-local/-cloud` tokens export `VECTOR_STORE_BACKEND` + pair a run-state store |
| `--<db>-local/cloud` + `<db> start/stop/reset/status` | `start-services.sh` Mongo/Postgres branches | **Extract** the per-store branches into a loop over `scripts/lib/stores.tsv` (#244); ES is a row, not a new `case` branch |
| Teardown | `stop-services.sh` (currently Atlas-only) | **Fix + generalise** to iterate every `stores.tsv` local profile |
| Dual-container health probe | `scripts/docker/health-check.sh` | **Extend** — reads `/healthz` `stores{}` + `stores.tsv` |
| bash 3.2 array safety | `tests/server/db/test_storage_mode_resolve.py::test_sourced_libs_use_bash32_safe_array_expansion` | **Reuse** — covers the new manifest loops |
| Server image | `docker/server.Dockerfile:26` | **Extend** with `ARG EXTRAS` (#243) |
| Stats assembly | `server/db/ports/stats_common.py` | **Reuse** — backend-agnostic; ES fills `_count`/`_stats`, quota `None` |
| Config-name parity test | `tests/server/models/test_config_examples.py` | **Generalise** into the registry-driven docs-parity check (reuse, not a second test) |
| Frontend labels | `frontend/src/utils/storageLabels.ts` (`isMongoProvider()` switch) | **Replace** the switch with adapter `labels()` — removes a branch, reuses the component |
| Setup-guide structure | `docs/user-guide/postgres-setup.md` (11-section template) | **Mirror** for `elasticsearch-setup.md` |
| QUICKSTART path | `QUICKSTART.md` Path D (Postgres) | **Mirror** as Path E |
| ADR template | `docs/adr/ADR-004-postgresql-pgvector-vector-store.md` | **Mirror** for `ADR-006` |
| Nightly integration job | `.github/workflows/nightly.yml` mongo/postgres service-container jobs | **Fold** into one `vector-store-integration` matrix job (#248); ES is a matrix leg |
| Comparison shape | Slice 38 `slice-38-quality-comparison.md` (top-3 overlap) | **Reuse** the comparison method for cross-backend evidence |
| **Net-new (only)** | `elasticsearch-local` compose profile, `GET /api/stores` endpoint, `configs/elasticsearch/*` (9 files), `scripts/lib/stores.tsv` + parity test, `elasticsearch-setup.md` + `ADR-006` prose, journey table + checklist, QUICKSTART teardown | Write new — the ES-specific surfaces and prose |

---

## Spec (GWT)

```
# ── Operability ──────────────────────────────────────────────────────────
Scenario: Clean-clone stage 5→8 works as written
  Given a fresh clone with the [elasticsearch] extra installed
  When ./start-services.sh --elasticsearch-local runs
  Then no environment variable was set by hand, and ES + the run-state store + server + dashboard come up "healthy" — defined as:
    /healthz returns 200 with stores.vector.ok and stores.run_state.ok true
    (ES _cluster/health green|yellow), storage_mode = elasticsearch-local and
    run_state_mode = postgres-local
    And the server image contains the elasticsearch client (built with EXTRAS=elasticsearch)
    And rag-params-finder indexes list shows the rpf-chunks mapping summary
    And configs/elasticsearch/example-local.yaml submits without a config-engine 422
    (transcript recorded in gate-evidence/slice-51.json)

Scenario: Compose profile is correctly constrained
  Given the elasticsearch-local profile
  When the ES container starts
  Then security is disabled, licence is basic (not trial), heap is -Xms1g -Xmx1g,
    the port binds 127.0.0.1 only, the healthcheck hits /_cluster/health,
    and server.depends_on marks it required: false

Scenario: ES unreachable at startup degrades clearly (not silently)
  Given --elasticsearch-local where the ES container fails to become healthy
  When the stack starts
  Then health-check.sh reports elasticsearch != ok with a remediation hint
    And /healthz returns 503 with stores.vector.ok = false (the server stays up so the
    Docker healthcheck reports it; it becomes healthy once ES is — #250)

Scenario: Script manifest matches the Python registry
  Given scripts/lib/stores.tsv and known_vector_stores()
  When the manifest parity test runs
  Then both list the same providers
    And start/stop/health-check scripts contain no per-store case branch

Scenario: GET /api/stores reports the registry with secrets redacted
  When GET /api/stores is called
  Then it lists each registered store, its capabilities, labels, and the active store
    And no API key, password, or full URI appears in the response

Scenario: CLI indexes list uses the API (thin-client leak fixed)
  Given the CLI no longer imports server internals
  When rag-params-finder indexes list runs against an ES backend
  Then it renders the mapping summary from GET /api/stores

Scenario: Frontend labels come from the adapter, not a Mongo switch
  Given VECTOR_STORE_BACKEND=elasticsearch
  When the dashboard renders store labels
  Then it shows Index/Host from labels() and no quota bar
    And storageLabels.ts has no elasticsearch-specific branch

Scenario: config name parity enforced for elasticsearch
  Given configs/elasticsearch/
  When the parity test runs
  Then it has the same YAML basenames as configs/mongodb/
    And each database_provider normalises to elasticsearch

Scenario: Teardown iterates all local profiles
  Given postgres-local and elasticsearch-local were started
  When stop-services.sh runs
  Then every registered local profile is brought down (no orphan container)

# ── CI / docs / ADR ──────────────────────────────────────────────────────
Scenario: Docs-parity check passes for every registered store
  Given the store registry (mongodb, postgres, elasticsearch)
  When the registry-driven docs-parity check runs
  Then each provider has a <provider>-setup.md with the required headings
    And its config dir basenames match configs/mongodb/
    And it is mentioned in .env.example, README, QUICKSTART, docs/README, troubleshooting
    And start-services.sh --help lists --<provider>-local and a <provider> subcommand

Scenario: Docs-parity check fails on a missing file or heading
  Given a registered provider whose setup guide is absent or missing a required heading
  When the docs-parity check runs
  Then it fails and names the missing file/heading (docs equivalent of a red contract test)

Scenario: Nightly vector-store matrix is green (skipped ≠ green)
  Given the vector-store-integration matrix job with an elasticsearch leg
  When nightly.yml runs
  Then store + vector contract suites and the split-store acceptance test pass against a live ES 9.5.x
    And a skipped or unreachable leg fails the job
    And gate-evidence/slice-51.json records the job conclusion + run URL

Scenario: Same YAML runs on all three stores with comparable scores
  Given one experiment YAML with only the vector store changed
  When it runs a full sweep on Mongo, Postgres, and ES
  Then dense scores are "comparable" — top-3 rank overlap recorded numerically
    on the fixed small corpus (Slice 38 comparison shape; equivalence, not byte-identical)
    And results are visible in the dashboard with correct ES labels (Index/Host)

Scenario: A fresh reader completes all 15 journey stages from docs alone
  Given only QUICKSTART.md Path E + elasticsearch-setup.md (no tribal knowledge)
  When a reader follows them
  Then they reach results-in-dashboard and teardown for ES
    (recorded in gate-evidence/slice-51.json)

Scenario: ADR-006 is Accepted and distinct from ADR-005
  Given ADR-006 covers vector-only role, unquantized HNSW, client-side RRF, refresh
  When the ADR index is read
  Then ADR-006 is the Elasticsearch ADR and ADR-005 remains the DoubleWord ADR
```

*(**PBT/parametrize handoff for `nw-distill`:** config-parity + docs-parity over all registered stores {mongodb, postgres, elasticsearch}; run-state pairing over {mongodb-local, postgres-local}; cross-backend comparability over the example-`*.yaml` set. "Healthy"/"comparable" are defined inline above so they are testable.)*

---

## Before-Checks [GATE]
- [ ] Slice 50 ✅ COMPLETE (ES adapter with `stats`/`labels`/`capabilities`/`search`).
- [ ] Docker Desktop ≥4 GB available; live ES 9.5.x reachable for the nightly service container.
- [ ] harness-scout `detect_confirm` at slice start (multi-file infra + script + FE + CI + docs — high blast radius).

## After-Checks [GATE]
- [ ] Specification coverage: every GWT clause has ≥1 test (BDD/GWT-first); `GET /api/stores` redaction test + docs-parity red-path test present.
- [ ] Config-name + docs-parity checks extended to `configs/elasticsearch/` and green in PR CI.
- [ ] Nightly ES job conclusion recorded (skipped ≠ green).
- [ ] **Journey gate:** stage-5→8 commands run from a clean clone as written; 15-stage read-through completes; transcripts in gate evidence.
- [ ] Cross-backend comparability evidence (Mongo/Postgres/ES, same YAML) recorded.
- [ ] Coverage floors (BE + FE) hold.
- [ ] Complexity evidence: policy `enforcing` (xenon E/C/C on `server/`/`cli/` via `./scripts/ci/quality-gates.sh`); local `bash scripts/ci/complexity-report.sh` → `.reports/complexity/pr-body.md`; FE complexity per the ESLint rules in the same report; new modules do not raise the average rank.
- [ ] Doc audit YES: all E2E-journey docs updated; `/sync-docs` footprint clean.
- [ ] `docs/plan/gate-evidence/slice-51.json` with coverage/complexity fields + clean-clone + journey + comparability transcripts.

### Closing Gates
- [ ] `nw-at-completeness-check` — AT completeness audit (gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline (gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data-flow review (gate #9, parallel): `/api/stores` contract + registry-driven scripts/docs-parity (no new SPOF/per-store branch)
- [ ] `nw-platform-architect-reviewer` — compose profile, healthcheck/binding/heap/teardown + nightly service-container job + docs-parity CI wiring
- [ ] `nw-documentarist-reviewer` — DIVIO/Diataxis currency for `elasticsearch-setup.md` + journey docs
- [ ] `nw-researcher-reviewer` — ES facts in ADR-006 (unquantized HNSW, Basic-licence RRF, refresh, alternatives) evidence-backed
- [ ] `nw-gate-evidence-validator` — 9 conditions pass
- [ ] `/verify-slice` — verdict COMPLETE

## Gate Status
📋 PLANNED — depends on Slice 50; amended 2026-09-25 (DECISIONS #240–#249); AT authoring (`nw-distill`) before 🔨 IN PROGRESS. Optional 51a/51b PR split decided at execution start.
