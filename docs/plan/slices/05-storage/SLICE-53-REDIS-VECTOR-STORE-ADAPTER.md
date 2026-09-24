# SLICE 53 — Redis Vector Store: Adapter + Full Journey (Branch A)

**MoSCoW:** SHOULD *(proposed; promoted to Must on a Slice 52 Branch A **GO** — owner, #227)*
**Target time:** ~9–12 h, one branch, may ship as 2 PRs: **53a** adapter core (~5–6 h) · **53b** operability + CI + docs + ADR-007 Accepted (~4–6 h)
**Status:** 📋 PLANNED
**Depends on:** **51** (registry, capabilities, `VECTOR_STORE_BACKEND`, `rrf_fuse()`, `GET /api/stores`, registry-driven FE labels, generalised `stop-services.sh`, docs-parity gate, all on `main`) · **52** (Branch A GO + client/image choice)
**Branch:** `slice/53-redis-vector-store-adapter`
**Feature:** Redis as a vector-only store (D1) — ADR-007

> **Fusion note (#224):** the Elasticsearch track needed three slices (49 seam → 50 core → 51 closeout) because it *built* the generic machinery. Redis is the **fourth** store and the first to arrive after that machinery exists, so core + journey fit in **one** slice. The optional 53a/53b PR split (same pattern as #218) keeps each PR reviewable. If Redis needs more than one slice, Slices 49–51 missed their acceptance criterion, and that is itself a finding (see the zero-changes gate).

---

## Context

Add Redis (Query Engine, per Slice 52's choice of Redis 8 or Valkey + valkey-search) as a **vector-only** store behind the Slice 49 `VectorStoreAdapter` registry, with dense / sparse / hybrid parity and the complete 15-stage user journey. Switching to Redis is a config change: `VECTOR_STORE_BACKEND=redis` + `REDIS_URL`. Self-hosted ↔ managed is a URL change only (`redis://` ↔ `rediss://`).

- **Depends-on outputs:** Slice 49 protocol + registry + `VECTOR_STORE_BACKEND` · Slice 50 `rrf_fuse()` shared fusion + `(1+cos)/2` parity pattern + `[elasticsearch]` extra pattern + registry-parametrised contract fixture · Slice 51 `GET /api/stores`, FE labels from `labels()`, `stop-services.sh` iterating registered profiles, docs-parity gate, nightly service-container job pattern · Slice 52 client choice (`redis-py` vs RedisVL), image + licence choice, measured bytes-per-vector, D1–D5 stance.
- **Invariants pointer:** `docs/plan/invariants.md`. Mandatory `embedding_model` filter (incompatible vectors never mixed). Default store stays `mongodb` (#130). D1–D5 (#215).

## Non-goals

- Redis as run-state store (`STORAGE_BACKEND=redis` stays rejected, D1).
- Native `FT.HYBRID` as the default hybrid path. It may be exposed as an opt-in capability only if 52 recommends it and the owner accepts; client-side `rrf_fuse()` stays the comparable default (D3).
- Redis Vector Sets (`VADD`/`VSIM`) as the backing structure, unless 52 selects them.
- Branch B uses (cache / queue / rate limit) → Slice 54 / Slice 16.
- Any change to `server/api/`, `server/core/pipeline/`, `frontend/src/components/`, `cli/main.py` or `cli/indexes_cmd.py` (zero-changes criterion). If one proves necessary, stop and route it back to 49/51 as a defect.
- Paid managed tiers.
- Per-query latency / tracing instrumentation of Redis I/O (e.g. Aim spans) beyond `/healthz` and stats — a post-ship enhancement.
- Encryption at rest for the local profile (single-user dev container on `127.0.0.1`); managed-endpoint guidance stays in `redis-setup.md`.

## Output contract

- **Baseline:** `curl -s localhost:8001/api/stores | jq '.stores[].provider'` lists `mongodb`, `postgres`, `elasticsearch` and no `redis`; `git grep -il redis server/` → no hits.
- `VECTOR_STORE_BACKEND=redis` + `REDIS_URL` runs any `configs/redis/example-*.yaml` sweep end-to-end. The dashboard shows Redis labels, sourced from `labels()`.
- `GET /api/stores` lists `redis` with `capabilities.can_host_run_state=false`, `supported_dims={384,1024}`, `retrieval_methods=[dense,sparse,hybrid]`, secrets redacted.
- The registry-parametrised contract suite passes for `redis` with **no edit to the suite itself** (only the fixture param list grows).
- The docs-parity gate passes for `redis` with **no edit to the gate**.
- `git diff main...HEAD --stat -- server/api server/core/pipeline frontend/src/components cli/main.py cli/indexes_cmd.py` → **empty**.

## Reuse ledger (reuse-first — don't reinvent the wheel)

Reuse-first order: **reuse → extend → extract → write new (last)**. This slice aims to be ≥80% reuse: Redis-specific I/O is the only net-new code.

| Need | Existing code to reuse/extend | Action |
|---|---|---|
| Store selection | `server/db/ports/registry.py` static manifest (Slice 49) | **Reuse** — add one entry `"redis": "server.db.redis.redis_store:RedisVectorStore"` |
| Adapter surface | `VectorStoreAdapter` + `VectorCapabilities` — `server/db/ports/vector_store.py` (49) | **Implement** — no new methods |
| Search contract | `RetrieverBackend.search` — `server/db/ports/retriever_backend.py` | **Reuse** — Redis composes it; returns existing `SearchResult` (`server/models/results.py`) |
| Hybrid fusion k=60 | `rrf_fuse()` extracted in Slice 50 from `retriever_mongo._RRF_K` | **Reuse** — no second fusion loop |
| Dense score scale | `(1+cos)/2` in `retriever_postgres.py` (parity-asserted in 50) | **Reuse** the convention: Redis COSINE distance `d = 1 − cos` → `score = 1 − d/2`; assert parity with the shared helper/test |
| Candidate over-fetch | `_CANDIDATES_MULTIPLIER = 2` — `retriever_postgres.py` | **Reuse** → KNN `k = top_k × 2` / `EF_RUNTIME` |
| 3-filter isolation | `embedding_model` / `experiment_id` / `run_id` filters (Mongo `$vectorSearch`, Postgres `WHERE`, ES `knn.filter`) | **Reuse** the same filter set as TAG pre-filters |
| Per-dim fields (D4) | `VECTOR_COLUMNS` (pgvector) / ES `embedding_384`/`embedding_1024` (50) | **Mirror** — two `VECTOR` fields on one index |
| Package layout | `server/db/elasticsearch/` split (config / URI / mapping / ensure / preflight / upsert / delete) from 50 | **Mirror** as `server/db/redis/` (schema instead of mapping) |
| Vector-only preflight skeleton | ES preflight (50) + `search_index_plan.py` capabilities-driven planning (49) | **Extract** the shared vector-only preflight steps if ≥~30 lines would repeat. Redis is the 3rd preflight implementation (Rule of 3, lens #14) |
| Capacity assessment | `search_index_plan.py` capacity assessment + `atlas_storage.py` quota shape (`limit_mb`, TTL cache) | **Reuse** the assessment shape. Redis supplies `maxmemory` / `used_memory` + 52's bytes-per-vector |
| Stats | `server/db/ports/stats_common.py` | **Reuse** — Redis fills counts from `FT.INFO` + `INFO memory`; quota = `maxmemory` or `None` |
| URI mode detection | `mongodb_uri.py` / `postgres_uri.py` `*_storage_mode()` pattern | **Mirror** → `redis_uri.py`: `redis-local` \| `redis-cloud` (TLS only for `rediss://`) |
| Optional driver | `[elasticsearch]` extra + lazy import (50) | **Mirror** `[redis]` extra; `pip install -e .` without it still runs the non-Redis suites |
| Live contract suite | `tests/contract/test_storage_backend_contract.py` + `tests/helpers/storage_live.py` (registry-parametrised in 49/50) | **Reuse** — add `redis` to the param set |
| Compose + scripts | `scripts/lib/compose.sh`, `scripts/lib/storage_mode.sh` (bash 3.2-safe, see memory note), `start-services.sh`, `stop-services.sh` (generalised in 51), `scripts/docker/health-check.sh` | **Extend** — `redis` subcommand, constants, `--redis-local/--redis-cloud`; D5 pairs `postgres-local` |
| `GET /api/stores`, FE labels, CLI `indexes list` | Slice 51 (registry-driven) | **Reuse — zero code** |
| Secret redaction in `/api/stores` | Slice 51's redaction of connection URIs (its `/api/stores` redaction test) | **Reuse** — `REDIS_URL` goes through the same redaction; add a `redis://user:pass@host` / `rediss://` case to that test |
| Teardown + container health | `stop-services.sh` and `scripts/docker/health-check.sh` made registry-driven in Slice 51 | **Reuse — zero Redis-specific edits expected**; verified as a Before-Check, and any gap is a Slice 51 defect |
| bash 3.2 array safety | `tests/server/db/test_storage_mode_resolve.py::test_sourced_libs_use_bash32_safe_array_expansion` | **Reuse** — the static guard test covers the new `redis-*` tokens unchanged |
| Docs-parity + config-name parity | Slice 51 gate generalising `tests/server/models/test_config_examples.py` | **Reuse — zero code**; add `configs/redis/*` so it passes |
| Nightly integration job | `nightly.yml` `elasticsearch-integration` (51) | **Mirror** → `redis-integration` service container |
| Setup guide / QUICKSTART / ADR | `postgres-setup.md` / `elasticsearch-setup.md`; QUICKSTART Path D/E; `ADR-006` | **Mirror** → `redis-setup.md`, **Path F**, `ADR-007` (Proposed in 52 → Accepted here) |
| Cross-backend comparison | Slice 38 top-3 overlap method (reused in 51) | **Reuse** — same YAML on 4 stores |
| **Net-new (only)** | `server/db/redis/` I/O (schema, `FT.CREATE`, pipelined `HSET`, `FT.SEARCH` KNN + BM25, delete-by-experiment, Redis preflight checks: Query Engine present, `maxmemory-policy`, capacity), `redis-local` compose profile, `configs/redis/*`, `redis-setup.md` + ADR-007 prose, `[redis]` extra | Write new — the Redis-specific I/O and prose |

---

## Slice Workflow Bundle

- Slice name: `slice-53-redis-vector-store-adapter`
- Branch: `slice/53-redis-vector-store-adapter`
- **T0 (≤20 min):** dependency health for the chosen client (`redis` / `redisvl`) via `pip-audit` + OSV; log tool + version + result in DECISIONS (lens #13). Fresh harness-scout `detect_confirm`.
- Files (expected):
  - **53a — core:** `server/db/redis/{__init__,config,redis_uri,schema,ensure,preflight,upsert,search,delete,stats,redis_store}.py` — **new**; `server/db/ports/registry.py` — **edit** (+1 entry); `server/settings.py` — **edit** (`redis` ∈ `_KNOWN_VECTOR_STORE_BACKENDS`; `REDIS_URL`); `server/models/config.py` — **edit** (`redis` in `DatabaseProvider`; config schema, allowed by the criterion); `pyproject.toml` — **edit** (`[redis]` extra, **shared** with Slice 54's cache backend: no separate `[redis-cache]` extra); tests (RED first): `tests/server/db/redis/test_*.py` (mocked client), contract fixture param.
    - *Illustrative* HASH layout (final layout taken from the 52 PoC appendix): key `rpf:chunk:{experiment_id}:{run_id}:{chunk_id}`; fields `text` (TEXT), `embedding_model` / `experiment_id` / `run_id` / `chunking_method` (TAG), `chunk_size` / `overlap` (NUMERIC), `embedding_384` or `embedding_1024` (VECTOR HNSW FLOAT32 COSINE — only the matching one is set). Vector keys are written **without a TTL**.
  - **53b — journey:** `docker-compose.yml` (`redis-local` profile: image from 52; command `--appendonly yes --maxmemory <from 52 sizing> --maxmemory-policy noeviction` — `volatile-lru` only if the owner picks Slice 54 option (a); bound to `127.0.0.1`; healthcheck `redis-cli ping` **and** `redis-cli FT._LIST`; named volume); `scripts/lib/compose.sh` (Redis URL/container/volume constants + `redis` subcommand) and `start-services.sh` — **edit**; `scripts/lib/storage_mode.sh` — **edit**: `redis-local` / `redis-cloud` tokens set the **vector** store only and pair a run-state store (D5 default `postgres-local`, overridable), and a run-state selection of `redis` fails with the same vector-store-only message as the settings validator; `configs/redis/example-*.yaml` (same basenames as the other store dirs); `.github/workflows/nightly.yml` — **edit**: `redis-integration` job mirroring `elasticsearch-integration` — service container (image from 52), health options running `redis-cli ping`, env `VECTOR_STORE_BACKEND=redis` + `REDIS_URL` + a Postgres service for run state, runs `tests/contract` with the `redis` param and the Redis retrieval suite under `-m integration`; a skipped job counts as not green; `.env.example`; docs: `docs/user-guide/redis-setup.md` (**new**, including AUTH / ACL for local vs cloud and backup & recovery: AOF vs RDB, manual `BGSAVE`), `QUICKSTART.md` Path F, `getting-started.md`, `configuration.md` (Engine × Location rows `redis-local`/`-cloud`), `cli-reference.md`, `dashboard-guide.md`, `troubleshooting.md` (Query Engine missing, `OOM command not allowed`, eviction policy, AOF off → empty after restart, TLS `rediss://`, dims mismatch 422), switching rows in `mongodb-setup.md` / `postgres-setup.md` / `elasticsearch-setup.md`, `README.md`, `docs/README.md`, `extending.md` (checklist items learned); `docs/adr/ADR-007-redis.md` → **Accepted**.
- Exit criteria: all GWT green; contract + docs-parity pass unchanged; zero-changes diff guard empty; nightly `redis-integration` conclusion recorded; clean-clone journey transcript.
- Commit pattern: `feat(storage): Redis vector-store adapter (dense/sparse/hybrid, vector-only)` · `feat(ops): redis-local profile + journey docs + ADR-007 Accepted`

---

## Spec (GWT)

```gherkin
Feature: Redis is a config-selectable vector-only store with full retrieval parity

  # ── 53a core ────────────────────────────────────────────────────────────
  Scenario: Redis is selected by configuration alone
    Given STORAGE_BACKEND=postgres, VECTOR_STORE_BACKEND=redis and REDIS_URL set
    When the server starts
    Then vectors are written to and searched in Redis
      And experiments, runs and results stay in Postgres
      And no Redis client module is imported when VECTOR_STORE_BACKEND is not redis

  Scenario: Redis is rejected as the run-state store
    Given STORAGE_BACKEND=redis
    When settings validate
    Then a clear error names redis as vector-store-only and suggests mongodb or postgres

  Scenario Outline: Retrieval parity for every method
    Given chunks for embedding_model <model> stored in Redis and in Postgres from the same YAML
    When a <method> query runs with top_k=5
    Then Redis returns SearchResult objects on the same score scale
      And scores are "comparable" as Slice 51 defines it: top-3 rank overlap with Postgres recorded numerically on the fixed small corpus (Slice 38 comparison shape; equivalence, not byte-identical)
    Examples:
      | model            | method |
      | all-MiniLM-L6-v2 | dense  |
      | all-MiniLM-L6-v2 | sparse |
      | all-MiniLM-L6-v2 | hybrid |
      | voyage-3.5-lite  | dense  |

  Scenario: Hybrid uses the shared fusion helper
    Given dense and sparse candidate lists from Redis
    When hybrid results are produced
    Then they come from rrf_fuse() with k=60 and no Redis-local fusion code exists

  Scenario: Vectors from different models never mix
    Given chunks from two embedding models, two experiments and two runs in one index
    When any query runs for one (embedding_model, experiment_id, run_id)
    Then every hit carries exactly those three values

  Scenario: A selective filter returns every matching chunk, up to top_k
    Given only 10 chunks match (embedding_model, experiment_id, run_id)
    When a dense query runs with top_k=20
    Then all 10 matching chunks are returned and none from other runs

  Scenario: Vector keys never expire
    Given chunks written by the Redis adapter
    When their TTL is inspected
    Then every vector key reports no expiry (TTL -1)

  Scenario: Unsupported dimensions fail at preflight, not mid-sweep
    Given a config requesting a 30522-dim sparse SPLADE embedding
    When the experiment is submitted with VECTOR_STORE_BACKEND=redis
    Then HTTP 422 names the dims mismatch using capabilities.supported_dims

  Scenario: A Redis without the Query Engine is rejected with remediation
    Given REDIS_URL points at a server where FT._LIST is an unknown command
    When preflight runs
    Then HTTP 422 explains that the Query Engine (or valkey-search) is required and links redis-setup.md

  Scenario: An evicting Redis is rejected before any vector is written
    Given maxmemory-policy is allkeys-lru on the target server
    When preflight runs
    Then HTTP 422 explains that vectors could be silently evicted and names the accepted policies

  Scenario: A sweep that would exceed maxmemory is rejected before embedding
    Given maxmemory leaves room for fewer vectors than the sweep plans
    When the experiment is submitted
    Then HTTP 422 reports the planned vs available memory using the shared capacity-assessment shape

  Scenario: Deleting an experiment removes all of its Redis data
    Given an experiment with chunks in Redis
    When DELETE /experiments/{id} runs
    Then no key tagged with that experiment_id remains and other experiments are untouched

  Scenario: Redis being unreachable fails fast and clearly
    Given REDIS_URL points at a closed port
    When /healthz is called
    Then it reports the vector store unreachable with the redis-local/redis-cloud mode and a remediation hint

  # ── 53b journey ─────────────────────────────────────────────────────────
  Scenario: Clean-clone stages 5 to 8 work as written
    Given a fresh clone and only QUICKSTART.md Path F
    When ./start-services.sh --redis-local runs
    Then Redis and postgres-local start healthy
      And /healthz returns 200 with both stores reachable
      And GET /api/stores lists redis with secrets redacted

  Scenario: Credentials in REDIS_URL never leave the server
    Given REDIS_URL=rediss://user:s3cret@host:6380
    When GET /api/stores and /healthz are called and the server logs are read
    Then the password appears in none of them

  Scenario: --redis-local pairs Redis with a run-state store
    Given ./start-services.sh --redis-local with no STORAGE_BACKEND set
    When the stack starts
    Then Redis holds vectors and postgres-local holds experiments, runs and results
      And selecting redis as the run-state store is refused with the vector-store-only message

  Scenario: A paused and resumed sweep keeps using the same Redis vectors
    Given a Redis-backed sweep paused after some runs completed
    When it is resumed
    Then completed runs are not re-embedded and remaining runs query the same index

  Scenario: Vectors survive a Redis restart
    Given the redis-local profile with AOF enabled and a completed experiment
    When ./start-services.sh redis stop and then start run
    Then the experiment's results page and Search Explorer still return hits

  Scenario: Docs-parity passes for redis with no change to the gate
    Given the registry now lists mongodb, postgres, elasticsearch and redis
    When the docs-parity check runs in PR CI
    Then it passes for redis and the check's own source has no diff

  Scenario: Switching between self-hosted and managed Redis is config-only
    Given a working redis-local sweep
    When REDIS_URL changes to a rediss:// managed endpoint
    Then the same YAML runs with no code or YAML change

  Scenario: Adding Redis changed no routes, sweep logic, UI components or CLI commands
    Given the slice branch
    When git diff main...HEAD --stat runs over server/api, server/core/pipeline, frontend/src/components, cli/main.py and cli/indexes_cmd.py
    Then it prints nothing

  Scenario: Teardown and reset leave no Redis data behind
    Given redis-local running with data
    When ./start-services.sh redis reset runs
    Then the container and its named volume are removed and stop-services.sh needed no Redis-specific edit
```

*(PBT / parametrize handoff for `nw-distill`: parametrize parity over the `(model, method)` table and the 3-filter isolation over random `(model, experiment, run)` triples, and run zero-changes and docs-parity over all registered stores. Step-definition pass pending before 🔨, same precedent as #216.)*

---

## Before-Checks [GATE]

- [ ] Slice 51 ✅ COMPLETE on `main` (registry, `rrf_fuse()`, `/api/stores`, docs-parity, nightly pattern).
- [ ] Slice 52 GO for Branch A recorded in DECISIONS, with image, licence and client choice.
- [ ] T0 dependency audit logged (lens #13).
- [ ] Slice 51 gate evidence shows `stop-services.sh` and `scripts/docker/health-check.sh` iterate the registered local profiles. If they still hard-code stores, stop and route the gap to Slice 51 (plan-self-healer); don't patch it here.
- [ ] Compose sizing: `--maxmemory` value taken from 52's measured bytes-per-vector; eviction policy fixed by the owner's 52/54 combined-deployment decision.
- [ ] Contract + docs-parity suites green on `main` for the three existing stores (baseline).
- [ ] harness-scout `detect_confirm` at slice start (external service + infra multi-file + CI + docs).

## After-Checks [GATE]

- [ ] Specification coverage: every GWT scenario ↔ ≥1 named test or transcript; all preflight red paths (Query Engine missing, eviction policy, capacity, dims, unreachable) covered.
- [ ] Branch coverage: Redis retrieval + preflight modules ≥95% (matches the ES/Postgres retrieval floor); combined backend floors (#142) hold.
- [ ] Complexity evidence: policy `enforcing` (xenon E/C/C via `./scripts/ci/quality-gates.sh`); local `bash scripts/ci/complexity-report.sh` → `.reports/complexity/pr-body.md`; new modules do not raise the average rank.
- [ ] Contract suite: the registry-parametrised StorageBackend / VectorStoreAdapter suite passes with the `redis` param and its test file has **no diff** (only the fixture's param list grows).
- [ ] `pip install -e .` (no `[redis]` extra) imports the server and runs non-Redis suites (lazy import holds).
- [ ] Mutation on Redis preflight + score conversion: survival budget met or waiver logged.
- [ ] Zero-changes diff guard empty (or each violation routed to 49/51 via plan-self-healer, not patched here).
- [ ] Nightly `redis-integration` conclusion recorded (skipped ≠ green).
- [ ] Journey gate: stage 5→8 clean-clone transcript + 15-stage read-through; cross-backend comparability (4 stores, same YAML).
- [ ] Doc audit YES: all journey docs + ADR-007 Accepted; `/sync-docs` footprint clean.
- [ ] `docs/plan/gate-evidence/slice-53.json` with `coverage_pct`, `branch_pct`, `coverage_target`, `complexity_tool`, `complexity_ceiling`, `complexity_passed` + journey/comparability transcripts.

---

### Closing Gates

- [ ] `nw-at-completeness-check` — AT completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline review (slice close gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data-flow review (gate #9, parallel): vector-only boundary, dual-store health, memory/eviction/persistence failure modes, no store-string branching
- [ ] `nw-platform-architect-reviewer` — compose profile (AOF, binding, healthcheck, volume), nightly service container, D5 pairing
- [ ] `nw-documentarist-reviewer` — `redis-setup.md` + Path F + troubleshooting parity with the other stores
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)

## Gate Status

📋 PLANNED — blocked on 51 ✅ + 52 GO. Then the `nw-distill` step-definition pass before 🔨 IN PROGRESS.
