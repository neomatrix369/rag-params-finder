# SLICE 51 — Elasticsearch Operability, CI, Docs & ADR-006 (closeout)

**MoSCoW:** MUST
**Target time:** ~11–15 h (largest ES slice — feature closeout; may ship as 2 PRs: **51a** operability/surfaces, **51b** CI/docs/ADR — one branch)
**Status:** 📋 PLANNED
**Depends on:** 50 (ES adapter core)
**Branch:** `slice/51-elasticsearch-operability-ci-docs-adr`
**Feature:** Elasticsearch vector-store adapter (ADR-006)

> **Merge note (2026-09-24, DECISIONS #218):** fuses the former Slices 51 (operability) + 52 (CI/docs/ADR). Elasticsearch is genuinely simpler than Postgres (no schema-DDL slice, no cloud/local-parity slice — D5 makes pairing a flag), so its closeout collapses to one slice. Optional 2-PR split (51a surfaces / 51b CI+docs+ADR) keeps each PR reviewable without re-fragmenting the plan. Pasted spec's "Slice 50 + 51".

---

## Context

Makes the ES store operable, proven, and documented end-to-end from a clean clone: Docker profile + scripts + `GET /api/stores` + configs + registry-driven FE labels (E2E journey stages 5–8, 10, 14), the nightly ES integration job, the full 15-stage user journey in docs with a **registry-driven docs-parity gate** (the docs equivalent of the contract suite), and `ADR-006`. "Done" = a fresh reader goes from "which backend?" to results-in-dashboard to teardown using docs + scripts alone, for ES exactly as for Mongo/Postgres.

- **Depends-on outputs:** ES adapter `stats()`, `labels()`, `capabilities()`, `search()` from Slice 50; the registry from Slice 49 (drive scripts, health-check, docs-parity, and `/api/stores` from the manifest — ES is one entry, not four edits).
- **Invariants pointer:** `docs/plan/invariants.md` — local ES pairs with a run-state store (D5, default `postgres-local`, flag convenience not a constraint); Basic-licence single-node, security off, `127.0.0.1`; 1 GB heap; dashboard read-only; cross-backend comparability (same YAML, only the vector store changed, comparable dense scores on Mongo/Postgres/ES).

## Non-goals

- New retrieval features or sweep axes; server-side fusion; Elastic Cloud setup automation; frontend store-*selection* UI.
- Changing the default store (stays `mongodb`).
- New per-store branches in scripts — ES must be **one manifest entry**, not four script `case` edits.

## Output contract

**Operability / surfaces (was Slice 51):**
- `docker-compose.yml` profile `elasticsearch-local` (pinned 9.5.x, single-node, `xpack.security.enabled=false`, `xpack.license.self_generated.type=basic`, `-Xms1g -Xmx1g`, named volume, `/_cluster/health` healthcheck, `127.0.0.1` binding, `required: false` in `server.depends_on`).
- `start-services.sh --elasticsearch-local | --elasticsearch-cloud` + `elasticsearch start|stop|reset|status`; `scripts/lib/compose.sh` gains `RAG_LOCAL_ELASTICSEARCH_URL_HOST/_DOCKER` + container/volume constants; local mode also starts the run-state store (D5 default `postgres-local`).
- `configs/elasticsearch/*.yaml` — same 9 basenames as `configs/mongodb/`, `database_provider: elasticsearch`, prerequisite header comment (incl. run-state store).
- `GET /api/stores` — registry + capabilities + labels + active store, secrets redacted; CLI `indexes list` routes through it (fixes the ADR-001 thin-client leak for all stores).
- Frontend labels from adapter `labels()` (Index/Host) replacing `isMongoProvider()` — no new per-store branch; no quota bar for ES.
- `stats()` via `_count`/`_stats`; quota fields `None`.
- **Drift fixes:** `configs/supabase/*.yaml` `database_provider: supabase → postgres` (9 files); `stop-services.sh` iterates all registered local profiles; `health-check.sh` `elasticsearch=ok` check driven by the manifest.

**CI / docs / ADR (was Slice 52):**
- Nightly `elasticsearch-integration` service-container job running store + vector contract suites with the ES retrieval coverage gate (added to `nightly.yml`, not PR `ci.yml`).
- `docs/user-guide/elasticsearch-setup.md` structured like `postgres-setup.md` (11 sections: choose deployment → env vars → Path A local Docker → Path B bring-your-own → index lifecycle → before a sweep → smoke sweep → switching → **sizing** (float32 on disk + HNSW graph memory, 1 GB heap — from Slice 50 data-eng note) → troubleshooting → diagnostics cheat sheet).
- Journey docs: `QUICKSTART.md` Path E + verify line; `getting-started.md`; `configuration.md` (Engine × Location rows `elasticsearch-local`/`-cloud` + env-asymmetry note); `cli-reference.md` (`/healthz` + `GET /api/stores`); `dashboard-guide.md`; `troubleshooting.md` (ES: memory/`vm.max_map_count`, 401/TLS, **403 licence non-compliant**, refresh zero-hits, quantized preflight, dims mismatch, 422); switching rows in `mongodb-setup.md` + `postgres-setup.md`; `.env.example` ES block; `README.md`; `docs/README.md`.
- **Registry-driven docs-parity check** (generalises `tests/server/models/test_config_examples.py`): for every registered provider asserts setup-guide existence + required headings, config-dir basename parity, and mentions in `.env.example`/`README`/`QUICKSTART`/`docs/README`/`troubleshooting` + `start-services.sh --help`. Wired into PR CI.
- `docs/adr/ADR-006-elasticsearch-vector-store.md` (vector-only role, unquantized HNSW, client-side RRF licence rationale, refresh semantics; alternatives note — OpenSearch/Vespa/pgvector/Atlas — answering the architect's "why ES" without expanding code scope).
- `extending.md` updated to the registry flow **and** to require the full 15-stage journey for any new store.

## Reuse ledger (reuse-first — don't reinvent the wheel)

This closeout is almost entirely *extending existing operator surfaces and doc templates* — ES becomes one manifest entry, one config dir, one setup guide, one ADR, one CI job, each mirroring a proven Mongo/Postgres counterpart. The docs-parity gate **generalises an existing test** rather than adding a new one.

| Need | Existing code to reuse/extend | Action |
|---|---|---|
| Compose helpers + local/cloud URI constants | `scripts/lib/compose.sh` (`mongodb`/`postgres` subcommands + constants) | **Extend** — add ES constants + `elasticsearch` subcommand in the same shape |
| Four-flag storage-mode resolver | `scripts/lib/storage_mode.sh` | **Extend** for the ES + run-state pairing |
| `--<db>-local/cloud` + `<db> start/stop/reset/status` | `start-services.sh` Mongo/Postgres branches | **Mirror** the existing pattern (no new bespoke path) |
| Teardown | `stop-services.sh` (currently Atlas-only) | **Fix + generalise** to iterate all registered local profiles |
| Dual-container health probe | `scripts/docker/health-check.sh` | **Extend** — manifest-driven ES probe |
| Stats assembly | `server/db/ports/stats_common.py` | **Reuse** — backend-agnostic; ES fills `_count`/`_stats`, quota `None` |
| Config-name parity test | `tests/server/models/test_config_examples.py` | **Generalise** into the registry-driven docs-parity check (reuse, not a second test) |
| Frontend labels | `frontend/src/utils/storageLabels.ts` (`isMongoProvider()` switch) | **Replace** the switch with adapter `labels()` — removes a branch, reuses the component |
| Setup-guide structure | `docs/user-guide/postgres-setup.md` (11-section template) | **Mirror** for `elasticsearch-setup.md` |
| QUICKSTART path | `QUICKSTART.md` Path D (Postgres) | **Mirror** as Path E |
| ADR template | `docs/adr/ADR-004-postgresql-pgvector-vector-store.md` | **Mirror** for `ADR-006` |
| Nightly integration job | `.github/workflows/nightly.yml` mongo/postgres service-container jobs | **Mirror** as `elasticsearch-integration` |
| Comparison shape | Slice 38 `slice-38-quality-comparison.md` (top-3 overlap) | **Reuse** the comparison method for cross-backend evidence |
| **Net-new (only)** | `elasticsearch-local` compose profile, `GET /api/stores` endpoint, `configs/elasticsearch/*` (9 files), `elasticsearch-setup.md` + `ADR-006` prose | Write new — the ES-specific surfaces and prose |

---

## Spec (GWT)

```
# ── Operability ──────────────────────────────────────────────────────────
Scenario: Clean-clone stage 5→8 works as written
  Given a fresh clone with the [elasticsearch] extra installed
  When ./start-services.sh --elasticsearch-local runs
  Then ES + the run-state store + server + dashboard come up "healthy" — defined as:
    /healthz returns 200 with vector store reachable (ES _cluster/health green|yellow),
    run-state store connected, and resolve_storage_mode() reporting elasticsearch + the paired run-state store
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
    And /healthz surfaces the vector-store failure (server does not claim ready)

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

Scenario: Supabase configs no longer trip the deprecation warning
  Given configs/supabase/*.yaml
  When each loads
  Then database_provider is postgres (no Slice 37 supabase-alias warning)

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

Scenario: Nightly ES integration job is green (skipped ≠ green)
  Given the elasticsearch-integration service-container job
  When nightly.yml runs
  Then store + vector contract suites pass against a live ES 9.5.x
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
- [ ] Every GWT clause has ≥1 test; `GET /api/stores` redaction test + docs-parity red-path test present.
- [ ] Config-name + docs-parity checks extended to `configs/elasticsearch/` and green in PR CI.
- [ ] Nightly ES job conclusion recorded (skipped ≠ green).
- [ ] **Journey gate:** stage-5→8 commands run from a clean clone as written; 15-stage read-through completes; transcripts in gate evidence.
- [ ] Cross-backend comparability evidence (Mongo/Postgres/ES, same YAML) recorded.
- [ ] Coverage floors (BE + FE) hold; complexity `enforcing`.
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
📋 PLANNED — depends on Slice 50; AT authoring (`nw-distill`) before 🔨 IN PROGRESS. Optional 51a/51b PR split decided at execution start.
