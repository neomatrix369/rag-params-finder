# Slice 48B — DoubleWord Batch Mode + Shared Embedding Cache + Pre-Embed Phase + Cost Capture

**Status**: 📋 PLANNED
**Branch**: `slice/48b-doubleword-batch-preembed`
**Estimated time**: ~6–8 h in four ordered streams (T0 spike · S1 cache · S2 batch client · S3 pre-embed + resume · S4 cost)
**MoSCoW**: Must (owner decision 2026-09-24; DECISIONS #189, #193–#195)
**Source brief**: [`BRIEF-doubleword-embedder.md`](../../BRIEF-doubleword-embedder.md) §6.7, §7.1, §8, Appendix A. This spec wins where they differ.

## Problem

A chunking × embedding sweep re-embeds the same corpus once per chunk config and repeats that work across experiments. DoubleWord's batch tier is the cheapest per token, but a batch can take minutes to hours, so per-run embedding calls cannot use it. Grid **and** Bayesian (categorical) sweeps know every chunk text and query up front. One batch per embedding identity, written into a cache that every run reads, makes batch pricing usable.

## Goal

With `DOUBLEWORD_MODE=batch`, an experiment embeds all distinct DoubleWord document and query texts **once** in a pre-embed step (one batch job per identity and role). The results go into a content-addressed cache **shared across sweeps**. Every run then reads vectors from the cache, results carry token and cost fields, and a restarted server resubmitting the same config resumes the in-flight batch instead of paying twice.

## Context
> Read before any implementation. Do not rely on conversation history alone.
- **Stage objective**: batch-priced embedding for the whole declared sweep space, with persistence and resume.
- **Depends on**: **48A** ✅ (DoubleWord provider, guard, MockTransport fixture, ADR-005 Proposed). Soft: **47** (if 47 has split `_run_sweep_inner`, insert pre-embed as a phase callable; otherwise call it before `_run_sweep_inner`). Do **not** add branches inside the CC=40 function.
- **Global invariants**: → [`docs/plan/invariants.md`](../../invariants.md).
- **Codebase realities**:
  - The orchestrator is sync and threaded (`parallelism` ≤ 16). The cache must be thread-safe.
  - Bayesian (41A) samples `chunk_size`/`overlap` via `suggest_categorical` over declared lists, so the declared chunk space = the grid product of methods × sizes × overlaps × paddings (DECISIONS #193).
  - `chunk_text(text, method, size, overlap, padding)` is deterministic. Pre-embed can reproduce exactly the chunks each run will embed.
  - `Phase` is per run; pre-embed is per experiment → experiment-level progress object (#194).
  - Run/experiment docs are dicts persisted through `StorageBackend` (Postgres `doc` JSONB), so new fields need no DDL. Verify in S4.
  - Slice 10 (Run recovery, 🔨 PARTIAL) owns **automatic** resume on boot. 48B delivers resume-on-resubmit; the boot hook is appended to Slice 10's remaining scope (#195).
> The executor may diverge from the plan if new evidence warrants. Document deviations in PROGRESS.md before marking PASSED.

## Non-goals
> Out of scope for this slice. Do not implement here.
- Wiring the cache into Voyage/local/SIE embedders (Rule of 3; Could later). The cache API is provider-agnostic, but only DoubleWord uses it here.
- Automatic resume of in-flight batches on server boot (→ Slice 10 remaining scope).
- `dimensions`/`query_instruction` axes (→ 48C).
- A cache purge CLI and an eviction policy (Could; the cache is small float32 blobs).
- Pareto (quality vs cost) chart; CSV/JSONL export columns (→ Slice 28 once merged).
- `async` mode as a separate code path. Batch with `completion_window="1h"` covers it if V6 = YES.

## Output contract
> Observable shape of completion (shape only, not exact file paths).
- **Baseline**: current TRAIL/PROGRESS status, `git status`, and a Voyage-only golden result set (`configs/mongodb/example-voyage.yaml` subset) captured before edits.
- A batch-mode experiment with 3 chunk configs × 1 DoubleWord model makes **exactly 2 batch submissions** (documents, queries). All runs then embed with **zero** further DoubleWord HTTP calls.
- Re-running the same config (new experiment) makes **zero** DoubleWord calls (cross-sweep cache hit), and cost is attributed as "incurred $0".
- `GET /experiments/{id}` exposes `pre_embed: {state, provider, batches: [{batch_id, role, completed, total}], tokens, cost_incurred_usd}` while it runs and after.
- Each run result carries `embed_mode`, `embed_tokens_docs`, `embed_tokens_queries` and `embed_cost_usd` (the list-price cost of that config, independent of cache state).
- Killing the server mid-batch and resubmitting the same config → the checkpoint's `batch_id` is polled; no second upload.
- The Voyage-only golden result set is byte-identical to the baseline.
- ADR-005 moves **Proposed → Accepted** with the V3–V7 results.

## Acceptance Criteria

### T0 — Batch verification spike (Must, before S2; needs key)
- [ ] Extend `scripts/spikes/dw_embed_spike.py`: **V3** (batch on `/v1/embeddings` completes), **V4** (output line shape), **V5** (list `input` per line), **V6** (`completion_window="1h"`), **V7** (`/batches/{id}/analytics` → `total_cost`). Record in ADR-005.
- [ ] **If V3 = NO** → STOP (HITL): 48B's premise fails. Re-scope to cache + realtime pre-embed only and log it in DECISIONS.

### S1 — Content-addressed embedding cache (Must)
- [ ] `server/core/embedding/embedding_cache.py`: `cache_key(text, *, provider, model, dim, instruction, role) -> str` (sha256 over a JSON list), `get_many(keys) -> dict[key, list[float]]` and `put_many(items)`. Local **SQLite** (stdlib; no new dependency), `float32` BLOB, path from `settings.embedding_cache_path` (default `.rpf_cache/embeddings.sqlite`). Thread-safe via lock plus per-call connection or a single `check_same_thread=False` connection.
- [ ] Shared across experiments (#194). Docker: the cache path lives on a named volume in `docker-compose.yml`; `.gitignore` + `.dockerignore` cover `.rpf_cache/` and `.rpf_state/`.
- [ ] The DoubleWord embed functions (48A) read from the cache first in **both** modes. Realtime fills misses; batch mode treats a miss after pre-embed as an error (below).

### S2 — Batch client (Must)
- [ ] `server/core/embedding/doubleword_batch.py`, sync `httpx` re-expression of brief §6.7: `build_jsonl` (5 MB/line guard naming the custom_id), upload from memory (`/files`, `purpose=batch`), `create` (`endpoint=/v1/embeddings`, `completion_window` from settings), `poll` (interval from settings, default 10 s, reports `completed/total`, calls `cancel_check`), `download_vectors` (row errors + `prompt_tokens`), `download_error_file` (pre-processing rejections), `cancel_batch`.
- [ ] Checkpoint store `.rpf_state/doubleword_batches.json`, keyed by `job_key = sha256(identity + role + sorted custom_ids)`, written **before** polling and removed on success. A terminal failed/expired/cancelled checkpoint → resubmit **once**; a second failure → experiment `failed` with the batch id in the error.
- [ ] Missing ids (row errors ∪ error-file) → one retry batch of only those ids; still missing → fail loudly naming the count and the first ids. Never store a partial corpus.

### S3 — Pre-embed step (Must)
- [ ] `server/core/pipeline/pre_embed.py`: pure `collect_embed_jobs(config, source_text, queries) -> dict[identity, EmbedJob{doc_texts, query_texts}]` over the **declared** chunk space (grid product; used for both `grid` and `bayesian`, #193), limited to models whose provider is DoubleWord **and** `DOUBLEWORD_MODE=batch`. Plus an orchestration function `run_pre_embed(...)` that dedupes against the cache, runs batches and fills the cache.
- [ ] Called once per experiment **before** the run loop (grid and Bayesian entry points). Runs are not multiplied by `parallelism`. Other providers skip it entirely.
- [ ] Plan-time guard: any chunk exceeding the model context (32K tokens, estimated with the existing tokenizer helper) → 422 at submit naming the chunk config.
- [ ] Experiment-level `pre_embed` progress object persisted through `StorageBackend`. The frontend progress card shows "Pre-embedding (DoubleWord batch) n/N" while `state=running` (TS type + component test).
- [ ] Cancel during pre-embed → `cancel_batch` + experiment `cancelled`. Pause → polling suspended, batch continues server-side; resume → polling resumes on the same `batch_id`.
- [ ] Default for `DOUBLEWORD_MODE` is **HITL at slice start** (flag defaults are human-owned). Recommendation: `realtime` default (judge-friendly, no hours-long wait), with `batch` documented for cost-sensitive sweeps.

### S4 — Cost capture (Must)
- [ ] Registry entry gains `price_per_mtok: {realtime, batch}` (optional `TypedDict` field; other models omit it).
- [ ] Per run: `embed_mode`, `embed_tokens_docs`, `embed_tokens_queries`, `embed_cost_usd = tokens × price[mode] / 1e6`. Tokens come from per-text `prompt_tokens` stored in the cache row, so cache hits still report the config's list-price cost.
- [ ] Per experiment: `pre_embed.cost_incurred_usd` = analytics `total_cost` when available, else tokens × price. Analytics failure never fails the experiment.
- [ ] Fields visible in `GET /experiments/{id}` results and the detail screen run table (FE type + render test); Mongo and Postgres round-trip verified.

## GWT Scenarios (acceptance tests: author RED first)

```gherkin
Feature: Embedding cache

  Scenario Outline: Cache key changes with every vector-affecting input
    Given a baseline key for text "x", provider doubleword, model Q, dim 1024, instruction I, role query
    When only <field> changes
    Then the key differs from the baseline
    Examples: | text | provider | model | dim | instruction | role |

  Scenario: Round-trip preserves float32 vectors
    When put_many stores a 1024-dim vector and get_many reads it back
    Then the vector matches to float32 precision

  Scenario: Concurrent writers do not corrupt the cache
    Given 8 threads each put_many 50 distinct entries
    When all threads finish
    Then get_many returns all 400 entries

  Scenario: Cache hit skips the API (shared across sweeps)
    Given the cache already holds every text of experiment A
    When experiment B with the same corpus and model runs
    Then the DoubleWord MockTransport receives 0 requests
    And pre_embed.cost_incurred_usd is 0 while each run's embed_cost_usd is > 0

Feature: Batch client

  Scenario: JSONL line shape
    When build_jsonl([("k1","hello")], model Q, dimensions 1024) is called
    Then the line has custom_id k1, method POST, url /v1/embeddings and body {model Q, input "hello", dimensions 1024}

  Scenario: Oversized line is rejected before upload
    Given a text whose JSONL line exceeds 5 MB
    When build_jsonl is called
    Then a ValueError names the custom_id and no HTTP request is sent

  Scenario: Output and error files are merged
    Given an output file with 2 vectors and 1 row error, and an error file with 1 rejection
    When the batch completes
    Then 2 vectors are returned and errors hold 2 custom_ids

  Scenario: Missing ids are retried once, then fail loudly
    Given the first batch returns errors for ids [k3]
    And the retry batch also errors on k3
    When run_pre_embed executes
    Then the experiment is failed with a message naming 1 missing chunk and k3
    And no chunk rows are stored for that identity

  Scenario: Resume polls the checkpointed batch instead of resubmitting
    Given a checkpoint for job_key J with batch_id b-1 in state in_progress
    When run_pre_embed is invoked for the same job
    Then no /files upload is sent and b-1 is polled to completion

  Scenario: Expired batch resubmits once then fails
    Given the checkpointed batch b-1 is expired and the resubmitted b-2 also expires
    When run_pre_embed executes
    Then exactly 1 resubmission happens and the experiment fails naming b-2

  Scenario: Cancel during pre-embed cancels the remote batch
    Given a running batch b-1
    When the experiment is cancelled
    Then POST /batches/b-1/cancel is sent and the experiment status is cancelled

  Scenario: Pause suspends polling; resume continues the same batch
    Given a running batch b-1
    When the experiment is paused, then resumed
    Then no poll requests are sent while paused and b-1 is polled after resume

Feature: Pre-embed step

  Scenario: One batch per identity and role for a grid sweep
    Given batch mode, 3 chunk configs, 1 DoubleWord model and 4 queries
    When the experiment runs
    Then exactly 2 batch jobs are created (documents, queries)
    And all runs complete with 0 realtime embedding calls

  Scenario: Bayesian sweep pre-embeds the declared space
    Given search_strategy bayesian with n_trials 2, chunk_sizes [256,512,1024] and overlaps [0,64]
    When the experiment runs in batch mode
    Then the document batch covers the chunks of all 6 declared (size, overlap) combinations
    And every Bayesian trial's embedding is a cache hit

  Scenario: Only DoubleWord batch identities are pre-embedded
    Given a mixed config [voyage-3.5-lite, Qwen/Qwen3-Embedding-8B] in batch mode
    When the experiment runs
    Then pre-embed covers only Qwen/Qwen3-Embedding-8B and Voyage runs embed as before

  Scenario: Realtime mode skips pre-embed
    Given DOUBLEWORD_MODE realtime
    When the experiment runs
    Then pre_embed is absent and no batch endpoints are called

  Scenario: Oversized chunk is rejected at submit
    Given a chunk config that produces a chunk over 32K tokens
    When POST /experiments is called in batch mode
    Then HTTP 422 names the chunk config

  Scenario: Progress is visible while pre-embedding
    Given a running pre-embed batch reporting 40/100
    When GET /experiments/{id} is polled
    Then pre_embed.state is running and batches[0] reports completed 40 of total 100

Feature: Cost capture

  Scenario: Cost prefers analytics, falls back to tokens × price
    Given analytics returns total_cost 0.0123 for b-1
    Then pre_embed.cost_incurred_usd is 0.0123
    Given analytics fails with 500
    Then cost_incurred_usd = prompt_tokens × batch price / 1e6 and the experiment still completes

  Scenario: Run results carry embed cost fields on both backends
    Given a completed batch-mode experiment on <backend>
    When results are read back
    Then every DoubleWord run has embed_mode batch, embed_tokens_docs > 0 and embed_cost_usd > 0
    Examples: | mongodb | postgres |

  Scenario: Voyage-only golden results unchanged (regression)
    Given the Voyage-only golden config captured before edits
    When it is re-run with mocked Voyage responses
    Then the persisted result documents equal the baseline apart from timestamps and ids
```

## Before-Checks
- [ ] 48A ✅ PASSED (gate evidence + `/verify-slice` COMPLETE)
- [ ] Branch `slice/48b-doubleword-batch-preembed` from latest `main`; `git diff --stat main` empty
- [ ] `./scripts/ci/quality-gates.sh` green on main
- [ ] HITL: `DOUBLEWORD_MODE` default decided and logged in DECISIONS
- [ ] Check Slice 47 status to choose the pre-embed insertion point (Context)
- [ ] harness-scout `detect_confirm` (external async integration: re-run, don't reuse the 48A result)

## After-Checks
- [ ] `./scripts/ci/quality-gates.sh` pass
- [ ] Specification coverage: every GWT scenario above maps to ≥1 named test; all failure channels (row error, error file, expired, cancelled, analytics down, oversize) covered
- [ ] Coverage: `embedding_cache.py`, `doubleword_batch.py`, `pre_embed.py` at 100% line + branch; floors unchanged or higher
- [ ] Complexity evidence: xenon **enforcing** E/C/C (target: new modules all A/B; orchestrator ranks must not worsen) + `.reports/complexity/pr-body.md`
- [ ] Mutation testing on cache key + missing-id policy + cost attribution: ≤10% survivors or a documented waiver
- [ ] Manual (with key): `configs/mongodb/example-doubleword.yaml` in batch mode completes; a re-run is fully cached; kill + resubmit resumes the same `batch_id`
- [ ] Doc audit → YES: `doubleword-setup.md` (modes, latency, cost, cache location/volume, resume-on-resubmit), `configuration.md`, `CLAUDE.md` Key Files, `.env.example`, ADR-005 → Accepted, Slice 10 stub remaining-scope line verified
- [ ] Security audit → YES: checkpoint/cache files contain no secrets; file paths come from settings, not user input; SQLite uses parameterised queries only

## Commits
```
feat(embedding): add content-addressed embedding cache shared across sweeps
feat(embedding): add DoubleWord batch client with checkpointed resume
feat(pipeline): pre-embed declared sweep space in one batch per identity
feat(results): capture embedding tokens and cost per run and per experiment
docs(doubleword): batch mode, cache and ADR-005 accepted
```

### Closing Gates
- [ ] `nw-at-completeness-check` — AT completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline review (slice close gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data flow review (gate #9, parallel: pre-embed → cache → runs; crash-recovery; SPOF = local cache/checkpoint files)
- [ ] `nw-data-engineer-reviewer` — cache schema, persistence of the new result fields on both backends
- [ ] `nw-researcher-reviewer` — V3–V7 evidence in ADR-005
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass (`docs/plan/gate-evidence/slice-48B.json`)
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)
