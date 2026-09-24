# Slice 48A — Mixed-Provider Embedding Axis + DoubleWord Batch Provider with Detached Async Watcher (Skateboard)

**Status**: 📋 PLANNED
**Branch**: `slice/48a-doubleword-batch-provider`
**Estimated time**: ~9–11 h in five ordered streams (T0 spike ≤45 min · S1 axis ~2 h · S2 batch client port ~1.5 h · S3 cache + plan/submit ~2.5 h · S4 watcher + resume ~3 h). S1 is independent and may ship as its own PR.
**MoSCoW**: Must (owner decisions 2026-09-24; DECISIONS #189–#190, #200–#203)
**Source brief**: [`BRIEF-doubleword-embedder.md`](../../BRIEF-doubleword-embedder.md). This spec wins where they differ.
**Reference implementation**: `playgroup_202602_docextract` → `llm_doubleword.py` (batch client) and `extractor.py::_run_all_doubleword` (submit-all → poll-all → checkpoint/resume); lessons in `DW_FB.md` and `docs/doubleword-platform-knowledge.md`. **Port its patterns; do not import the repo.**

> Scope flipped to **batch-first** on 2026-09-24 (#202): DoubleWord is batch/async by nature and docextract never used realtime. Realtime moved to [48D](SLICE-48D-DOUBLEWORD-REALTIME-MODE.md) (Could).

## Problem

Two problems:

1. Comparing providers takes one experiment each, because `EmbeddingConfig.provider` is a single value.
2. DoubleWord is **asynchronous by nature**: primarily a batch cloud whose jobs take minutes to 24 h, with realtime limited and priced highest.

The sweep executor has **one worker** (`server/core/pipeline/executors.py:24`, `SWEEP_EXECUTOR = ThreadPoolExecutor(max_workers=1)`). Waiting for a batch inside a sweep would therefore block every other experiment for hours.

## Goal

1. **S1 (provider-agnostic):** `embedding.models` may mix providers. Each run's `embedding_provider` is derived from the registry. Existing configs behave byte-identically.
2. **S2–S4 (DoubleWord batch):** an experiment using `Qwen/Qwen3-Embedding-8B` @1024 plans every document and query text over the **declared** sweep space (grid and Bayesian, #193). It submits **all** batch jobs, checkpoints them, and **releases the sweep thread**. A detached async **watcher** polls all pending batches in one loop, fills the embedding cache when they complete, then schedules the experiment's runs, which read vectors from the cache. If the server restarts at any point, the watcher resumes from checkpoints on boot without resubmitting.

## Context
> Read before any implementation. Do not rely on conversation history alone.
- **Stage objective**: first usable DoubleWord path, using its batch/async nature correctly, plus provider comparison inside one sweep.
- **Depends on**: none (builds on shipped 18 list-axis pattern, 21 factory/guard/example-config pattern, 32–38 dual backend).
- **Global invariants**: → [`docs/plan/invariants.md`](../../invariants.md). Factory dispatch (#10); provider opt-in + fail-closed; secrets server-side; mandatory `embedding_model` filter.
- **Codebase realities (recon 2026-09-24, `main` @ `6283caa`)**:
  - `embedder_factory.get_embedder(provider)` returns sync `(embed_docs(texts, model_id, **kw), embed_query(text, model_id))`. `_run_single` calls `embed_docs` per run and `embed_query` per query (`orchestrator.py` ~L887–971).
  - `schedule_sweep()` submits to the single-worker `SWEEP_EXECUTOR`. `server/main.py` has a FastAPI `lifespan` (startup indexes + reconciliation; shutdown `shutdown_executors()`).
  - `startup_reconciliation.py` marks stale `running` experiments on boot. It **must exempt** experiments whose `pre_embed.state == "waiting"`, or every restart would kill in-flight batches.
  - `Provider` literal is duplicated in `server/models/config.py:10` and `server/models/status.py:9`.
  - `sie_guard._uses_sie` checks `config.embedding.provider == "sie"`. Guard call sites: `server/api/experiments.py:69`, `orchestrator.py:137` (Bayesian), `:594` (grid).
  - `server/api/experiments.py:120` writes a single `sweep_summary.embedding_provider`; FE `ExperimentDetailScreen.tsx:564` renders one value.
  - Vector indexes are dim-keyed (`vector_index_1024`, PG `embedding_1024`). 1024 dims needs **no** index/DDL change.
  - `openai` is **not** a dependency today; `httpx` is.
- **docextract lessons applied here** (see brief Appendix A): `AsyncOpenAI(base_url="https://api.doubleword.ai/v1")`; upload JSONL from memory `(name, bytes)`, `purpose="batch"`; checkpoint `{batch_id, submitted_at, n}` **before** polling; **submit all first, then poll all** in one loop at 10 s; resume set = `{validating, in_progress, finalizing, completed}`, else drop checkpoint and resubmit; `retrieve` error (batch not found) → resubmit; two error channels (`output_file_id` row errors + `error_file_id` pre-processing rejections, which are **silent if ignored**); 5 MB/line; `PermissionDeniedError` on submit, or a completed batch where **every** row errors "not configured / not available", → persist the model as unavailable and skip it on future runs; graceful shutdown keeps checkpoints; use API `created_at`/`completed_at` for elapsed time; log the dashboard link `https://app.doubleword.ai/batches/{id}`; **do not use `autobatcher`** (it hides batch ids, so no checkpoint/resume).
> The executor may diverge from the plan if new evidence warrants. Document deviations in PROGRESS.md before marking PASSED.

## Non-goals
> Out of scope for this slice. Do not implement here.
- Realtime `/v1/embeddings` calls (→ 48D, Could).
- Cost capture/analytics, double-billing adoption by `metadata.job_key`, dashboard pre-embed progress card, pause/cancel refinements beyond the minimum below, ctx-limit auto-detection (→ **48B**).
- `dimensions` ≠ 1024 and `query_instruction` axes (→ 48C). The instruction is a fixed constant; no document instruction.
- Webhooks (`batch.completed`): the server is not publicly reachable; polling is the contract (DW_FB #6).
- `autobatcher` (DW_FB #7) and DoubleWord's single-request `/jobs` async API (unverified for embeddings; V11 records it only).
- Wiring the cache into Voyage/local/SIE (Rule of 3).
- A generic `requires_env` schema field (#192).

## Output contract
> Observable shape of completion (shape only, not exact file paths).
- **Baseline**: TRAIL/PROGRESS status + `git status`; `expand_sweep` snapshots for every `configs/{mongodb,supabase}/*.yaml` on `main`.
- A config mixing `all-MiniLM-L6-v2`, a Voyage 1024-dim model and `Qwen/Qwen3-Embedding-8B` (no `embedding.provider`) expands to runs with providers `local` / `voyage` / `doubleword`. All pre-existing configs expand byte-identically.
- Submitting a DoubleWord experiment returns immediately. `GET /experiments/{id}` shows `status: running`, `pre_embed: {state: "waiting", batches: [{batch_id, role, status, completed, total, dashboard_url}]}`, and runs `queued`.
- **While it waits, a second (non-DoubleWord) experiment submitted afterwards starts and completes.** The sweep worker is not held.
- When the batches complete, the experiment's runs execute and it reaches `complete`, with 1024-dim DoubleWord vectors stored (Mongo and Postgres).
- Restarting the server mid-batch → after boot, the same `batch_id`s are polled and the experiment completes. No second upload; not marked `partial`.
- Without `DOUBLEWORD_API_KEY`: submit → **422** naming the key; nothing created. Non-DoubleWord configs are unaffected.
- `docs/adr/ADR-005-doubleword-embedding-provider.md` is **Proposed**, with V1–V6, V9 and V11 results.

## Acceptance Criteria

### T0 — Verification spike (Must, ≤45 min, before S2; needs key)
- [ ] `scripts/spikes/dw_embed_spike.py` (opt-in, `AsyncOpenAI`, not imported by server/tests) answers, via a 3-line **embeddings** batch: **V3** (batch on `/v1/embeddings` completes; docextract only ever proved `/v1/chat/completions`), **V4** (output line shape `response.body.data[0].embedding` + `usage.prompt_tokens`), **V5** (list `input` per line), **V6** (`completion_window="1h"` accepted), **V1/V2** (`dimensions=1024` honoured in the body? default dim), **V9** (exact model id + Qwen3 query-prefix format), **V11** (does `/jobs` async support embeddings? record only). Record in ADR-005.
- [ ] **If V3 = NO** → STOP (HITL): the batch-first premise fails. Re-order to 48D realtime first and log it in DECISIONS.
- [ ] **If V1 = NO** → request full vectors; truncate + L2-renormalize client-side (brief §6.4).

### S1 — Mixed-provider embedding axis (Must; independent)
- [ ] `EmbeddingConfig.provider` optional (`None` default). When set, the existing single-provider validation applies. When omitted, models may come from any provider.
- [ ] `model_registry.provider_for_model(model_id: str) -> str` raises `ValueError(f"Unknown embedding model '{model_id}'")`. It is the single owner, called by `expand_sweep`, `sie_guard` and `doubleword_guard`.
- [ ] `sie_guard._uses_sie` → `any(provider_for_model(m) == "sie" for m in config.embedding.models)`.
- [ ] Summary contract: new experiments always write `embedding_providers: list[str]`. `embedding_provider` = the single provider, or `"mixed"`. The TS type adds `embedding_providers?: string[]`; the detail badge renders `embedding_providers ?? [embedding_provider]`.
- [ ] `"doubleword"` added to `Provider` in `server/models/config.py`. `server/models/status.py` drops its own literal and imports it (or both import from `enums.py` if a cycle appears).
- [ ] CLI `config_loader` accepts the provider-less form; `configuration.md` documents both forms.

### S2 — DoubleWord batch client (Must; port of docextract `llm_doubleword.py`)
- [ ] Add the `openai` dependency (pin a current major; `pip-audit` clean; lens #13 row in DECISIONS). `server/core/embedding/doubleword_client.py`:
  - `create_async_client() -> AsyncOpenAI`: key from `settings.doubleword_api_key: SecretStr`, `base_url` from settings (default `https://api.doubleword.ai/v1`).
  - `build_jsonl(items, *, model, dimensions) -> bytes`: url `/v1/embeddings`, custom_id = cache key, 5 MB/line guard.
  - `submit_batch(client, job_key, payload, window) -> str`: upload from memory, then `batches.create(endpoint="/v1/embeddings", metadata={"source": "rag-params-finder", "job_key": job_key})`.
  - `poll_batch(client, batch_id) -> BatchSnapshot(status, output_file_id, error_file_id, completed, total, failed, created_at, completed_at)`.
  - `download_vectors` / `download_error_file`: both channels merged, `prompt_tokens` summed.
  - `cancel_batch`.
- [ ] Registry entry `Qwen/Qwen3-Embedding-8B`: `provider=doubleword`, `dimensions=1024`, `contextualized=False`, `batch_only=True`.
- [ ] Unavailable-model registry `.rpf_state/doubleword_unavailable.json` (`{model_id: reason}`). It is written on `PermissionDeniedError` at submit, or when a completed batch has **all** rows erroring with "not configured"/"not available". `doubleword_guard` rejects that model at submit (422 with reason + how to clear: delete the entry).
- [ ] The key is never logged; all logs use scoped logging (`scope_log`).

### S3 — Cache + plan + submit (Must)
- [ ] `server/core/embedding/embedding_cache.py`: `cache_key(text, *, provider, model, dim, instruction, role) -> str` (sha256 of a JSON list); `get_many` / `put_many`; stdlib SQLite rows `(key, dim, vec float32 BLOB, prompt_tokens INT NULL)` so 48B can price every text, `settings.embedding_cache_path` (default `.rpf_cache/embeddings.sqlite`); `PRAGMA journal_mode=WAL`. Thread- **and** event-loop-safe: the watcher writes via `asyncio.to_thread`, runs read from the sweep thread. Shared across sweeps (#194). WARN at startup if the path is under a temp dir. Compose named volume; `.gitignore`/`.dockerignore` cover `.rpf_cache/`, `.rpf_state/`.
- [ ] `server/core/pipeline/pre_embed.py`, with effect isolation:
  - **pure** `plan_pre_embed(config, source_text, queries, cached_keys: frozenset[str]) -> PreEmbedPlan`: frozen `EmbedJob(job_key, identity, role, items)`, cache misses only, declared space for grid **and** Bayesian (#193), DoubleWord models only.
  - **effectful** `submit_pre_embed(plan, client, checkpoint) -> list[SubmittedJob]`: submits **all** jobs first (docextract Phase 2), then writes checkpoint entries `{experiment_id, job_key, batch_id, role, n, submitted_at}` to `.rpf_state/doubleword_batches.json` (atomic write).
- [ ] Orchestrator entry points (grid `:594` and Bayesian `:137`): if the plan has jobs → submit, persist `pre_embed.state="waiting"`, **return without running** (the sweep thread is released). If the plan is empty (everything cached) → run immediately. No branches inside `_run_sweep_inner` (xenon must not worsen).
- [ ] `embed_documents_doubleword` / `embed_query_doubleword` (factory branch) **only read the cache**. A miss raises `DoublewordCacheMissError` naming the key count (never silently embed or store a partial corpus).

### S4 — Detached watcher + resume (Must)
- [ ] `server/core/pipeline/doubleword_watcher.py`: one `asyncio` task started in `lifespan` startup **only when** `DOUBLEWORD_API_KEY` is set. It loads checkpoints (boot resume), then loops every `DOUBLEWORD_POLL_INTERVAL_S` (default 10). Each pass: `poll_batch` every pending job.
  - `completed` → download both channels, `put_many`, drop the checkpoint.
  - `failed`/`expired` → resubmit **once** (then fail the experiment naming the batch id).
  - `cancelled` → fail.
  - `retrieve` error (not found) → drop the checkpoint and resubmit once.
- [ ] Missing ids (row errors ∪ error file) → one retry batch of only those ids; still missing → experiment `failed`, naming the count and the first ids.
- [ ] When **all** jobs of an experiment are done → `pre_embed.state="ready"` and `schedule_sweep(run_sweep, experiment_id, config)`. The runs then execute from the cache.
- [ ] Minimum controls: **cancel** while waiting → `cancel_batch` for its jobs, drop checkpoints, experiment `cancelled`. **Pause** while waiting → keep polling but do not schedule runs until resumed.
- [ ] `lifespan` shutdown: cancel the watcher **task** only. Never cancel remote batches; checkpoints are preserved (docextract graceful-shutdown pattern).
- [ ] `startup_reconciliation` exempts experiments with `pre_embed.state == "waiting"` that have checkpoint entries. A waiting experiment **without** checkpoints (orphan) is marked `failed` with a clear reason.
- [ ] Each batch record exposes `dashboard_url`, and elapsed time uses API `created_at`/`completed_at`.

### Docs + config (Must)
- [ ] `configs/{mongodb,supabase}/example-doubleword.yaml`, `configs/mongodb/example-provider-compare.yaml`; `docs/user-guide/doubleword-setup.md` covers: key, **batch latency (1h/24h windows; 24h cheaper)**, restart-safe, `.rpf_state`/`.rpf_cache` volumes, single uvicorn worker, unavailable-model reset. Also `.env.example`, `configuration.md`, `extending.md`, `CLAUDE.md` Key Files + Provider System, `README.md` vendor-neutral.
- [ ] **HITL at slice start:** default `DOUBLEWORD_COMPLETION_WINDOW` (`1h` faster vs `24h` cheaper). Log in DECISIONS.

## GWT Scenarios (acceptance tests: author RED first)

```gherkin
Feature: Mixed-provider embedding axis

  Scenario: Provider is derived per model when embedding.provider is omitted
    Given embedding.models [all-MiniLM-L6-v2, voyage-3.5-lite, Qwen/Qwen3-Embedding-8B] and no embedding.provider
    When expand_sweep is called with 1 chunk config and 1 dense retriever
    Then 3 runs are returned with embedding_provider local, voyage and doubleword in model order

  Scenario Outline: Existing example configs expand byte-identically (regression lock)
    Given the example config <path> as on main
    When expand_sweep is called on the slice branch
    Then the RunParams list equals the main snapshot
    Examples: every file under configs/mongodb/ and configs/supabase/

  Scenario: Explicit provider still rejects a mismatched model
    Given embedding.provider voyage and embedding.models [all-MiniLM-L6-v2]
    Then validation fails naming the model, its provider local and the configured provider voyage

  Scenario: SIE guard fires for a mixed config containing an SIE model
    Given SIE_ENABLED false and models [voyage-3.5-lite, bge-m3] with no provider
    When the experiment is submitted
    Then it is rejected (422) mentioning SIE_ENABLED and nothing is created

  Scenario: Mixed experiment summary lists all providers, legacy clients still render
    Given a submitted mixed-provider experiment
    Then sweep_summary.embedding_providers is [local, voyage, doubleword] and embedding_provider is "mixed"

Feature: DoubleWord batch submission releases the sweep worker

  Scenario: Submit returns immediately and the experiment waits on the provider
    Given DOUBLEWORD_API_KEY is set and a stubbed DoubleWord API that accepts uploads and batches
    When a DoubleWord experiment with 2 chunk configs and 3 queries is submitted
    Then the response is immediate and the experiment shows pre_embed.state waiting
    And one document batch and one query batch are recorded, each with a dashboard_url
    And all its runs are queued

  Scenario: A later experiment is not blocked by a waiting DoubleWord experiment
    Given a DoubleWord experiment is waiting on its batches
    When a local-provider experiment is submitted afterwards
    Then the local experiment completes while the DoubleWord experiment is still waiting

  Scenario: Everything already cached skips submission
    Given the cache holds every document and query text of the config
    When the DoubleWord experiment is submitted
    Then no batch is created and the runs execute immediately

  Scenario: Bayesian sweep plans the declared space
    Given search_strategy bayesian, chunk_sizes [256,512,1024] and overlaps [0,64]
    When the experiment is submitted
    Then the document batch covers chunks of all 6 declared (size, overlap) combinations

  # Provider wire-contract test: the JSONL line IS the external interface
  Scenario: JSONL line shape
    When build_jsonl([("k1","hello")], model Qwen/Qwen3-Embedding-8B, dimensions 1024) is called
    Then the line has custom_id k1, method POST, url /v1/embeddings and body {model, input "hello", dimensions 1024}

  Scenario: Oversized line is rejected before upload
    Given a text whose JSONL line exceeds 5 MB
    When the experiment is submitted
    Then it is rejected naming the chunk config and nothing is uploaded

Feature: Detached watcher completes experiments

  Scenario: Completed batches fill the cache and trigger the runs
    Given a waiting experiment whose batches the stubbed DoubleWord API reports completed
    When the watcher polls
    Then vectors are cached, pre_embed.state becomes ready, and the experiment completes with 1024-dim DoubleWord chunks stored

  Scenario Outline: Runs complete on both storage backends
    Given STORAGE_BACKEND <backend> and a completed DoubleWord pre-embed
    When the runs execute
    Then chunks are stored in the 1024 vector slot and dense retrieval returns results
    Examples: | mongodb | postgres |

  Scenario: Pre-processing rejections are not silently lost
    Given the output file has vectors for k1,k2 and the error file rejects k3 with context_length_exceeded
    When the watcher processes the batch
    Then a retry batch containing only k3 is submitted

  Scenario: Still-missing chunks fail the experiment loudly
    Given the retry batch also rejects k3
    When the watcher processes it
    Then the experiment is failed with a message naming 1 missing chunk and k3, and no chunks are stored

  Scenario Outline: Terminal failure resubmits once, then fails
    Given a checkpointed batch that ends <status>, and its resubmission also ends <status>
    When the watcher processes both
    Then exactly one resubmission happened and the experiment fails naming the second batch id
    Examples: | failed | expired |

  Scenario: All rows "not available" marks the model unavailable
    Given a completed batch where every row errors "model not configured or not available"
    When the watcher processes it
    Then the experiment fails and Qwen/Qwen3-Embedding-8B is recorded as unavailable
    And a later submission of a DoubleWord config is rejected (422) with that reason and how to clear it

  Scenario: Permission denied at submit marks the model unavailable
    Given the stubbed DoubleWord API denies batch creation (403)
    When a DoubleWord experiment is submitted
    Then it is rejected with the provider's reason and the model is recorded as unavailable

  Scenario: Cancel while waiting cancels the remote batch
    Given a waiting experiment with batch b-1
    When the experiment is cancelled
    Then b-1 is cancelled at the provider, its checkpoint is removed and the experiment is cancelled

  Scenario: Pause while waiting defers the runs
    Given a waiting experiment is paused and its batches then complete
    Then vectors are cached but no run starts until the experiment is resumed

Feature: Restart safety

  Scenario: Server restart resumes the same batches
    Given a waiting experiment with checkpointed batch b-1 in progress
    When the server shuts down and starts again
    Then no batch is cancelled at shutdown, b-1 is polled after boot without a new upload
    And the experiment is not marked partial and later completes

  Scenario: Checkpointed batch no longer exists
    Given a checkpoint for b-1 that the stubbed DoubleWord API reports as not found
    When the watcher resumes after boot
    Then the checkpoint is replaced by exactly one new batch for the same job

  Scenario: Orphan waiting experiment is reconciled
    Given an experiment with pre_embed.state waiting and no checkpoint entries
    When the server boots
    Then the experiment is failed with a reason stating its batches cannot be resumed

Feature: Readiness and secrets

  Scenario: Missing key rejects a DoubleWord experiment
    Given DOUBLEWORD_API_KEY is unset
    When configs/mongodb/example-doubleword.yaml is submitted
    Then it is rejected (422) naming DOUBLEWORD_API_KEY and docs/user-guide/doubleword-setup.md, and nothing is created

  Scenario: Missing key does not affect other configs
    Given DOUBLEWORD_API_KEY is unset
    When configs/mongodb/example-local.yaml is submitted
    Then it is accepted, and no watcher task is running

  Scenario: API key never appears in logs
    Given DOUBLEWORD_API_KEY "dw-secret-123" and a failing upload
    Then no captured log record contains "dw-secret-123"

  Scenario: Cache miss at run time fails loudly
    Given a DoubleWord run whose texts are not all cached
    When embed_documents_doubleword is called
    Then DoublewordCacheMissError names how many texts are missing

  @integration
  Scenario: Live smoke (opt-in, skipped without key)
    Given DOUBLEWORD_API_KEY is set
    When a 3-text embeddings batch is submitted with completion_window 1h and polled to completion
    Then 3 vectors of length 1024 are returned
```

**Step reuse:** "Given a stubbed DoubleWord API …" (`openai` client pointed at an `httpx.MockTransport`-backed `http_client`) and "When … is submitted" are shared fixtures in `tests/fixtures/doubleword.py`; 48B/48C/48D reuse them.

## Before-Checks
- [ ] Branch `slice/48a-doubleword-batch-provider` from latest `main`; `git diff --stat main` empty
- [ ] `./scripts/ci/quality-gates.sh` green on main; baseline `expand_sweep` snapshots captured
- [ ] harness-scout `detect_confirm` fresh (external async integration + new concurrency seam; the #197 degradation does **not** apply to the rescoped 48A)
- [ ] T0 spike run (key required; V3 is a hard gate)
- [ ] HITL: `DOUBLEWORD_COMPLETION_WINDOW` default decided and logged

## After-Checks
- [ ] `./scripts/ci/quality-gates.sh` pass
- [ ] Specification coverage: every GWT scenario ↔ ≥1 named test; all failure channels covered (403, all-rows-unavailable, row error, error file, failed/expired, not-found, orphan, cache miss)
- [ ] Coverage 100% line + branch on `doubleword_client.py`, `embedding_cache.py`, `pre_embed.py`, `doubleword_watcher.py`, `doubleword_guard.py`; floors unchanged or higher
- [ ] Complexity evidence: xenon **enforcing** E/C/C; new modules A/B; orchestrator ranks unchanged; `.reports/complexity/pr-body.md`
- [ ] Mutation testing on plan/cache-key/missing-id policy/resume triage: ≤10% survivors or a waiver
- [ ] Dependency audit: `openai` version + `pip-audit` result logged (lens #13)
- [ ] Manual (with key): provider-compare config completes; a restart during the wait resumes the same `batch_id`; a local experiment submitted during the wait completes first
- [ ] Doc audit → YES (Docs + config list); `/sync-docs`
- [ ] Security audit → YES: SecretStr, no key in logs/checkpoints, TLS base URL, state files contain ids only, SQLite parameterised

## Commits
```
test(config): lock example-config sweep expansion before mixed providers
feat(config): derive embedding provider per model so one sweep can compare providers
feat(embedding): port DoubleWord batch client from docextract for embeddings
feat(pipeline): plan and submit DoubleWord pre-embed batches without holding the sweep worker
feat(pipeline): resume DoubleWord batches from checkpoints via a detached watcher
docs(doubleword): setup guide, example configs and ADR-005 (Proposed)
```

### Closing Gates
- [ ] `nw-at-completeness-check` — AT completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline review (slice close gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data flow review (gate #9, parallel: submit → watcher → cache → runs; restart/resume; event-loop ↔ thread seam)
- [ ] `nw-researcher-reviewer` — V-spike evidence in ADR-005
- [ ] `nw-documentarist-reviewer` — setup guide + configuration reference
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass (`docs/plan/gate-evidence/slice-48A.json`)
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)
