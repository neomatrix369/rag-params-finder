# Brief — Adapter Review + Redis Evaluation (v2)

> **Source material, not a slice spec.** Owner-supplied investigation prompt (v2, 2026-09-24). Kept verbatim below for traceability — Slice 52 executes its research steps.
> **Executable specs:** [52](slices/05-storage/SLICE-52-REDIS-EVALUATION-SPIKE.md) · [53](slices/05-storage/SLICE-53-REDIS-VECTOR-STORE-ADAPTER.md) · [54](slices/08-embedding-providers/SLICE-54-CACHE-BACKEND-PORT-REDIS.md). Where this brief and a slice spec disagree, **the slice spec wins**.
> **Decisions:** [DECISIONS #220–#229](DECISIONS.md). **Builds on:** Elasticsearch track 49 → 50 → 51 (#213–#219) and DoubleWord 48A embedding cache (#194, #201).

## Reconciliation against `main` @ `dcdbd6f` + branch `docs/elasticsearch-slice-plan` @ `0ad56b4` (2026-09-24)

| Prompt assumes | Repo reality | Resolution |
|---|---|---|
| ES Slices **48** (port split) · **49** (core) · **50** (operability) · **51** (CI/docs/ADR) | 48A–48D = DoubleWord (merged, #187/#188). ES = **49** port split · **50** core · **51** closeout (old 51+52 merged, #218) | Map prompt "48"→**49**, "49"→**50**, "50"+"51"→**51**. Redis slices start at **52** (#220) |
| ES = ADR-005, Redis = **ADR-006** | ADR-005 = DoubleWord, ADR-006 = Elasticsearch (#214) | Redis = **ADR-007** (#221) |
| ES = QUICKSTART Path E, Redis = Path F | Path D = Postgres (live); Path E = ES (planned, Slice 51) | Redis = **Path F** — unchanged |
| Verified on `main` @ `76d19b3` | `main` @ `dcdbd6f` (PRs #187–#190 landed) | Re-derive file refs at slice start (`/divergence-check`) |
| Step 0 / 0B: full adapter review of Mongo + Postgres + target design | **Done in the ES planning:** Slice 49 carries the port/registry/capabilities/`VECTOR_STORE_BACKEND` target design + four-place branching evidence; Slice 51 carries `GET /api/stores`, drift fixes, `stop-services.sh` generalisation | Slice 52 **reuses** that review and adds only the **Redis column + delta** (#222). No second audit |
| Step 0C: 15-stage journey audit + docs-parity check design | Slice 51 owns the 15-stage journey docs and the **registry-driven docs-parity gate** (generalised `test_config_examples.py`) | Redis journey = **pass the Slice 51 gate unchanged**; 52 fills the Redis matrix column (#222) |
| Branch B embedding cache (key = provider + model + text hash) | **48A S3** plans `server/core/embedding/embedding_cache.py`: content-addressed `cache_key(text, provider, model, dim, instruction, role)`, `get_many`/`put_many`, SQLite WAL, shared across sweeps | Redis is an **alternative backend behind the same key function** (Slice 54, Could). No second cache (#225) |
| Branch B job queue (RQ / arq / Celery / Huey) | `executors.py` `SWEEP_EXECUTOR` (1 worker) + `experiment_control.py` `threading.Event` pause/cancel + 48A detached asyncio watcher + `startup_reconciliation`. **Slice 16** already lists "Celery + Redis" as Approach B and re-affirmed threads | **Won't** now — folded into Slice 16 Approach B; flip trigger = Slice 16 picks B or multi-worker uvicorn (#226) |
| Branch B rate limiting | `server/core/embedding/rate_limiter.py` (`RateLimiter`, `call_with_retry`) + SIE in-process semaphore; Slice 16 deferred cluster-scoped limiting | **Won't** — same flip trigger as the queue (#226) |
| Semantic / LLM cache (LangCache) | No LLM generation calls in `server/` or `cli/` (grep 2026-09-24: 0 hits) — retrieval + rerank only | **Won't** — nothing to cache (#226) |
| CI speed-ups via Redis | CI is GitHub Actions; uv/npm/HF-model caches are the native fit | **Won't** for Redis; 52 records the honest comparison (#226) |
| `CacheBackend` / `JobQueue` / `RateLimiter` ports with non-Redis defaults | Only the cache has two real implementations (SQLite + Redis) | Only `CacheBackend` is planned (Could). No `JobQueue` / `RateLimiter` ports — YAGNI + Rule of 3 (#225) |
| "Supabase is the `postgres` adapter + hosted URI" | Matches repo (Slice 37; `database_provider: supabase` = alias) | No change |
| D1–D5 are fixed inputs | Accepted for ES (#215) | Redis **adopts D1–D5**. Redis-specific additions (memory-bound preflight, eviction policy, persistence, native `FT.HYBRID`) are **capabilities / preflight values**, not new guard branches — listed as HITL in Slice 52 (#223) |
| Two artifacts (Markdown report + single-file HTML guide) | Internal audit docs live in `docs/_internal/` | `docs/_internal/REDIS-EVALUATION.md` + `docs/_internal/redis-evaluation.html` (#222) |

### Redis-specific pressure on D1–D5 (to confirm in Slice 52 — not silently decided)

| Decision | Redis pressure | Planned stance |
|---|---|---|
| D1 vector-only | Redis *could* hold run state (JSON), but durability/eviction make it a poor system of record | **Keep** — `can_host_run_state=False`; `STORAGE_BACKEND=redis` rejected |
| D2 YAML asserts vector store | None | **Keep** — `redis` joins `DatabaseProvider` |
| D3 client-side RRF k=60 | Redis 8.x may ship native `FT.HYBRID` (*hypothesis — verify in 52*) | **Keep** client-side `rrf_fuse()` for comparability; native hybrid = optional capability flag, off by default |
| D4 one index, per-dim fields | *Hypothesis — verify in 52 R3 PoC (Redis 8 **and** valkey-search):* one index accepts multiple `VECTOR` fields, and a document missing a field is simply unindexed for that field | **Keep** — `embedding_384` / `embedding_1024` on HASH keys |
| D5 `--redis-local` also starts run-state store | None | **Keep** — pairs with `postgres-local` by default |
| *(new)* Memory-bound store | Vectors + HNSW graph live in RAM; `maxmemory` + eviction can silently drop vectors | Capacity preflight + `maxmemory-policy` check as adapter preflight (**HITL** in 52) |
| *(new)* Persistence | *Hypothesis — verify in 52 R3 PoC (restart with and without AOF, on Redis 8 and Valkey):* restart without AOF/RDB persistence loses the vectors and index | Compose profile enables AOF; documented in `redis-setup.md` |

---

## Original prompt (v2, verbatim)

## Prompt — rag-params-finder: Adapter Review + Redis Evaluation (v2)

> **v2 changes vs v1 (2026-09-24):** repo facts corrected from the Step 0 audit. New **Step 0C** covers the end-to-end setup-to-use journey across 15 stages, plus a docs-parity check. The Elasticsearch adapter plan's design decisions (Slices 48–51, D1–D5) are now fixed inputs the Redis plan must align with. The acceptance criterion, checklist, touchpoint plan and RESPONSE sections are extended to cover the full user journey. Numbering conflicts are resolved: Redis uses ADR-006 and QUICKSTART Path F.
>
> *(Numbering superseded by the reconciliation table above: Redis = ADR-007, slices 52–54.)*

### CONTEXT

I maintain `rag-params-finder` (github.com/neomatrix369/rag-params-finder), a RAG
parameter-sweep tool with a FastAPI backend, a Typer CLI thin client and a read-only
React dashboard.

Vector stores in the project (verified on `main` @ 76d19b3):

- MongoDB (Atlas cloud / Atlas Local) — existing, working implementation
- Postgres/pgvector — existing, working implementation. **"Supabase" is not a separate
  adapter**: it is the `postgres` adapter pointed at a hosted `*.supabase.co` URI
  (Slice 37). YAML `database_provider: supabase` is a deprecated alias for `postgres`.
- Redis — candidate under evaluation (not implemented)

MongoDB and Postgres/Supabase are the REFERENCE IMPLEMENTATIONS: they define how a
store is added, configured, started, verified, used and documented today.

Known repo facts (from the v1 audit — re-verify, don't assume):

- Ports already exist: `StorageBackend` and `RetrieverBackend` Protocols in
  `server/db/ports/`, a lazy-import if/elif factory (`store_factory.py`), per-engine
  packages `server/db/mongo/` and `server/db/postgres/`, and a parametrised live
  `StorageBackend` contract suite (`tests/contract/`).
- The store is selected per process via `STORAGE_BACKEND` (default `mongodb`,
  DECISIONS #130). The YAML `database_provider` field is an assertion checked by a 422 guard.
- The README already documents Postgres/Supabase. Treat the code as the source of truth
  and flag drift wherever it is (pyproject description, `docs/ARCHITECTURE.md`,
  `extending.md` paths, setup guides, scripts).

**Elasticsearch adapter plan (separate workstream — do NOT audit Elasticsearch code;
there is none on `main`).** Its adapter-design decisions are FIXED INPUTS that the Redis
plan must reuse, not re-decide:

- **Slice 48:** `VectorStoreAdapter` / capabilities port split; static registry manifest
  replacing hard-coded store lists; backend branching moved out of guards and `main.py`.
- **Slice 49:** Elasticsearch adapter core against a registry-parametrised contract suite.
- **Slice 50:** compose profile, `start-services.sh` subcommand, `configs/<store>/`,
  `GET /api/stores`, frontend labels from the registry.
- **Slice 51:** nightly CI job, full docs set (setup guide, QUICKSTART **Path E**,
  switching/troubleshooting/sizing), **ADR-005**, a registry-driven docs-parity CI check,
  and fixes for the existing doc drift.
- **D1:** newer engines are vector-only; experiments/runs/results stay on a run-state store
  (Mongo or Postgres). `VECTOR_STORE_BACKEND` selects the vector store and defaults to
  `STORAGE_BACKEND`.
- **D2:** YAML `database_provider` asserts against the vector store.
- **D3:** hybrid retrieval is client-side RRF (k=60) for cross-store comparability.
- **D4:** one index with per-dimension vector fields (`embedding_384`, `embedding_1024`).
- **D5:** `--<store>-local` also starts a local run-state store (default `postgres-local`).

If a Redis-specific reason argues against any of these, say so explicitly and list it in
"Open questions". Don't silently diverge.

Design principle: every vector store — and every piece of swappable supporting
infrastructure — must sit behind the ADAPTER PATTERN, so switching implementations is
a configuration change, not a code change. **That includes the user journey:** a store is
not "added" until a user can discover it, set it up, configure it, start it, verify it, run
a sweep on it, observe results, switch away from it, troubleshoot it and tear it down,
using the docs and tooling alone.

This prompt covers two linked pieces of work:

1. An adapter design review and target design for vector stores and supporting
   infrastructure, based on MongoDB and Postgres/Supabase, reconciled with the
   Elasticsearch plan above.
2. A Redis evaluation in TWO roles, assessed as separate branches:
   - Branch A — Redis as a VECTOR STORE (vector-only adapter under D1), judged on how
     easily it fits the build, test, CI, deployment AND end-to-end user journey.
   - Branch B — Redis as SUPPORTING INFRASTRUCTURE for the non-functional side
     (caching, job queues, rate limiting, build/CI speed-ups), each behind its own adapter.

This is a PLANNING and INVESTIGATION exercise only — do not implement anything,
including refactors or doc edits. Illustrative code/config/doc snippets are welcome and
must be marked as illustrative.

Hard constraint — cost: every Redis option must be free to use right now ($0, no card).

1. PREFERRED: self-hosted open source (Docker locally, in CI, on my own infrastructure).
2. ACCEPTABLE: managed free tiers — document concrete limits (memory, connections,
   throughput, bandwidth, idle expiry/deletion, regions, card requirement, vector/FT
   support) and whether they are compatible with sweep-scale workloads.

Self-hosted wins ties. Paid tiers may be noted as an upgrade path only.

### OBJECTIVE

(a) Assess how well MongoDB and Postgres/Supabase follow the adapter pattern — in code
AND in the end-to-end user journey — and specify a target design (reconciled with
Slices 48–51 / D1–D5) that makes stores switchable by config.
(b) Produce a researched, evidence-backed recommendation of which Redis offerings suit
rag-params-finder in each branch, planned as new adapters with a complete user journey.

Redis evaluation criteria and weighting:

- GATE (pass/fail): free to use today. Failures are listed with reasons and not ranked.
- Weighted: Developer adoption & outreach 50% · Non-functional fit 30% (build, test, CI,
  deploy, ops, adapter fit, **ease of documenting and operating the e2e journey**) ·
  Documentation quality 20%.
- Tie-breaker: self-hosted over managed free tier.

Step 0 — Map the vector-store integration surface (do this FIRST).
Read `main` (prefer raw.githubusercontent.com) and trace how MongoDB and Postgres are
ADDED (deps, adapters, ports, factory), CONFIGURED (env, settings, config files,
secrets, URIs, index params), ENABLED (flags, profiles, defaults, fallbacks) and
SURFACED (backend routes/services/sweep orchestration, frontend, CLI, build & deploy
— Dockerfiles, compose, scripts, workflows — tests, docs). Also map existing caching,
queueing and rate-limiting code for Branch B.
Output: "Integration surface map" (layer → files → what it does → how each store is
wired) and a "Store parity matrix" (rows = every layer + every e2e journey stage from
Step 0C + "conforms to target design"; columns = MongoDB, Postgres/Supabase, Redis
planned; ✅/◐/✗/n/a with file-path evidence; for each Mongo/Postgres difference,
say whether it is intentional or an inconsistency). Anything you can't locate is a
Coverage Gap.

Step 0B — Adapter pattern: design review and target design.
Review the existing ports, factory and contract suite: consistency, design-health
problems with file paths (store identity leaking outside the factory, closed store
lists, UI/CLI hard-coding, CLI bypassing the server, inconsistent errors, asymmetric
tests, mandatory drivers). Rate: good / needs alignment / needs refactor.
Target design (reuse Slice 48–51 where it already specifies something): the
`VectorStoreAdapter` lifecycle derived from real call sites; capability model; typed
per-adapter config with a discriminated union; registry/factory (static manifest, lazy
import); switching precedence (CLI flag > env > config file > default) with
`STORAGE_BACKEND` vs `VECTOR_STORE_BACKEND` semantics; `GET /api/stores` driving the
UI and CLI; shared error hierarchy; optional install extras; registry-parametrised
contract tests; Branch B `CacheBackend` / `JobQueue` / `RateLimiter` adapters with
non-Redis defaults.
Acceptance criterion: adding a store = adapter module + registration + config schema +
green contract tests + **a complete e2e journey passing the docs-parity check**, with
ZERO changes to routes, sweep logic, UI components or CLI commands (infra and docs
additions are allowed).
Migration plan: ordered steps, mapped onto Slices 48–51, naming anything those slices
don't cover. Produce an "Adding a vector store adapter" checklist that includes code,
infra/scripts, configs, CI, e2e docs and the docs-parity check.

Step 0C — End-to-end setup-to-use journey (NEW in v2).
Audit how a user sets up and then uses each reference store through the platform,
across these 15 stages, with file/line evidence:
1 discover & choose · 2 cloud account/prerequisites · 3 install · 4 configure env ·
5 start the stack (`start-services.sh` modes + subcommands, compose profiles, native
dev) · 6 indexes/schema · 7 verify (health-check script, `/healthz`, operational
checks) · 8 pick an experiment config (`configs/<store>/`, `database_provider`) ·
9 run a sweep (smoke sweep) · 10 observe in the dashboard · 11 switch backends ·
12 troubleshoot · 13 limits & sizing · 14 teardown/reset (`stop-services.sh`, volumes)
· 15 delete experiment data.
Output: a journey coverage matrix (stage × MongoDB × Postgres × Redis today × Redis
planned deliverable); drift and inconsistencies in the existing journey docs/tooling,
with fixes; a planned Redis walkthrough (commands + a sample `configs/redis/*.yaml` +
expected verification output, mocked where needed); a draft `redis-setup.md` outline
mirroring `postgres-setup.md`; and a docs-parity check design that generalises the
existing `tests/server/models/test_config_examples.py` and reuses Slice 51's check.
State plainly whether the Redis plan covers all 15 stages.

Step 1 — Redis candidate set. Verify current offerings from official sources (don't
trust prior knowledge; the Redis product line has changed): Redis Open Source 8.x +
Query Engine; Vector Sets; Redis Stack (status); Redis Cloud free tier; RedisVL;
`langchain-redis` / LlamaIndex Redis; LangCache; RQ, arq, Celery, Huey; Valkey +
valkey-search (label as not Redis Inc.); other Redis-compatible managed free tiers
(e.g. Upstash, Aiven for Valkey). For each: branch, hosting model, adapter
implemented, free-gate result. Drop discontinued options and say why.

Step 2 — Adoption & outreach evidence (50%): GitHub (stars, contributors, 12-month
cadence, open:closed issues, time to first response), PyPI downloads + trend, Docker
Hub pulls, community activity, vendor outreach (RAG guides, courses, samples, how
recent they are), ecosystem pull. Cite every number with source + retrieval date;
missing metrics are Coverage Gaps; flag conflicting signals.

Step 3A — Branch A (vector-only under D1): adapter fit and capabilities vs Mongo/Postgres;
behaviour under D3/D4 (client-side RRF k=60, one index with per-dimension fields) and any
Redis-native alternatives (`FT.HYBRID`, per-config indexes) as extra capabilities; score
normalisation to the `(1+cos)/2` convention; local dev (compose, image, startup,
healthcheck) vs Mongo/Postgres; CI (service container, testcontainers, isolation);
deployment targets (self-hosted Docker, HF Spaces, Modal, managed free tier; what
Supabase and Cloudflare cannot host); sweep-scale memory/persistence; licensing
(RSALv2/SSPLv1/AGPLv3 vs BSD); self-hosted ↔ managed switching must be config-only;
**effort to deliver the full 15-stage journey**.

Step 3B — Branch B, anchored to real code paths: embedding cache (key = provider + model +
text hash), semantic/LLM cache (only if LLM calls exist), job queue (vs the current
in-process executors and pause/cancel events), rate limiting, CI speed-ups (be honest if
GitHub Actions cache or an on-disk cache is better). For each: adapter, default
implementation, attach point, benefit, ops complexity, self-hosted vs managed, verdict.

Step 4 — Documentation review per candidate (Python quickstart, deploy/ops docs,
free-tier limits in one place, RAG/benchmark examples), rated 1–5 with links.

Step 5 — Scoring & recommendation: per-branch weighted tables + equal-weight
sensitivity check (say what drives any change); primary pick, fallback and conditions
that would flip them; call out any high-adoption blocker. Combined deployment (one vs
several Redis instances; eviction/persistence as adapter config). A Redis touchpoint plan
that follows the checklist, fills the Redis parity column, covers **all 15 journey
stages** and states whether the zero-changes criterion is met. Sequencing relative to
Elasticsearch Slices 48–51 (propose Redis slice numbers after 51), with Redis using
**ADR-006** and **QUICKSTART Path F**.

### STYLE

Technical, evidence-first, comparison-driven. Tables for comparisons, prose for trade-offs.
Snippets are illustrative and marked as such. Where live access or auth is unavailable,
use documentation-derived mocked examples tagged `"__mocked": true` and
`"__source": "<doc URL>"`.

### TONE

Direct and pragmatic, for a solo builder deciding what to refactor and prototype next.
Flag uncertainty explicitly.

### AUDIENCE

An AI/ML engineer and solo builder fluent in RAG, vector search, FastAPI, Docker, CI and
design patterns.

### RESPONSE

Two parallel artifacts:

1. Markdown report: Executive summary (adapter health, e2e journey verdict, both Redis
   branch picks, sequencing vs Slices 48–51) → Integration surface map → Store parity
   matrix (incl. e2e rows) → Adapter design review → Target adapter design → Migration
   plan (mapped to Slices 48–51) → "Adding a vector store adapter" checklist → README/docs
   drift → **End-to-end setup-to-use journey (Step 0C)** → Redis candidate set → Adoption
   & outreach → Free-tier limits → Branch A → Branch B → Documentation review → Scoring +
   sensitivity → Combined deployment → Redis touchpoint plan → Sequencing (incl.
   alignment with the Elasticsearch plan) → Illustrative snippets (Protocol + capabilities,
   config union, registry, provider-switching configs, contract test, compose, Actions
   service block, RedisVL adapter sketch, CacheBackend/JobQueue sketches, sample
   `configs/redis/*.yaml`) → Coverage Gaps → Open questions → Sources (URL + date).
2. A self-contained single-file interactive HTML guide mirroring the report: sidebar nav;
   inline-SVG adapter architecture diagram; interactive parity matrix (click a cell for
   evidence); config-switching demo; **journey stepper for the 15 stages**; expandable
   candidate cards with branch and hosting filters; scoring table with adjustable weights
   (default 50/30/20); syntax-highlighted code; light/dark; mobile-safe; no external
   dependencies.

Rules:

- Unresolvable assumptions go in "Open questions" — never resolve them silently.
- No implementation, refactors, doc edits or PRs against the repo.
- Reuse over reinvention: extend existing abstractions and the Slice 48–51 plan.
- Verify product names, status and free-tier limits from official sources.
