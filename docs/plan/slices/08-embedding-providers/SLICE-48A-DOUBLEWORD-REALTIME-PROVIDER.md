# Slice 48A — Mixed-Provider Embedding Axis + DoubleWord Realtime Provider (Skateboard)

**Status**: 📋 PLANNED
**Branch**: `slice/48a-doubleword-realtime`
**Estimated time**: ~5–6 h (T0 spike ≤30 min · S1 axis ~2 h · S2 provider ~3 h)
**MoSCoW**: Must (owner decision 2026-09-24; DECISIONS #189–#190)
**Source brief**: [`BRIEF-doubleword-embedder.md`](../../BRIEF-doubleword-embedder.md). This spec wins where they differ.

## Problem

Comparing a new embedding provider against the Voyage baseline currently takes one experiment per provider, because `EmbeddingConfig.provider` is a single value. The owner wants to sweep DoubleWord's `Qwen/Qwen3-Embedding-8B` (MRL, instruction-aware, batch-priced) **inside the same sweep** as Voyage and local models, so quality results sit side by side.

## Goal

1. **S1 (provider-agnostic):** `embedding.models` may mix models from different providers. Each run's `embedding_provider` is derived from the model registry. Existing single-provider configs behave byte-identically.
2. **S2 (DoubleWord realtime):** `Qwen/Qwen3-Embedding-8B` at **1024 dims** runs end-to-end (chunk → embed → store → query) on both Mongo and Postgres through the realtime `/v1/embeddings` API. This is opt-in: without `DOUBLEWORD_API_KEY`, configs that use it are rejected with HTTP 422, and every other config is unaffected.

## Context
> Read before any implementation. Do not rely on conversation history alone.
- **Stage objective**: first usable DoubleWord path plus the ability to compare providers inside one sweep.
- **Depends on**: none (builds on shipped 18 list-axis pattern, 21 factory/guard/example-config pattern, 32–38 dual backend).
- **Global invariants**: → [`docs/plan/invariants.md`](../../invariants.md). Key ones: factory dispatch over Protocol (#10); provider opt-in and fail-closed; secrets server-side; the `embedding_model` filter on every vector search.
- **Codebase realities (recon 2026-09-24, `main` @ `6283caa`)**:
  - `server/core/embedding/embedder_factory.py::get_embedder(provider)` returns sync `(embed_docs(texts, model_id, **kw), embed_query(text, model_id))`.
  - `Provider` literal is **duplicated** in `server/models/config.py:10` and `server/models/status.py:9` (both include reserved `"kimchi"`).
  - `EmbeddingConfig.validate_models_match_provider` enforces one provider; `expand_sweep` copies `config.embedding.provider` into every `RunParams.embedding_provider`.
  - `sie_guard._uses_sie` checks `config.embedding.provider == "sie"`, so it must check per model once providers mix.
  - `server/api/experiments.py:120` writes a single `sweep_summary.embedding_provider`; the frontend `ExperimentDetailScreen.tsx:564` renders it as a one-value badge.
  - Vector indexes are keyed by dimension (`vector_index_1024`; Postgres `embedding_1024`), so a 1024-dim DoubleWord model needs **no** index or schema change.
  - OpenAI-compatible `httpx` embedding client precedent: `server/core/kimchi_embedder.py` on the unmerged, unrelated-history branch `tessl-hackathon-kimchi-integration`. Use it as reference only (`_normalize_base_url`, retry loop); do **not** merge that branch.
> The executor may diverge from the plan if new evidence warrants. Document deviations in PROGRESS.md before marking PASSED.

## Non-goals
> Out of scope for this slice. Do not implement here.
- Batch/async mode, embedding cache, pre-embed phase, cost capture (**48B**).
- `dimensions` ≠ 1024 and `query_instruction` as sweep axes (**48C**). In 48A the instruction is a fixed module constant, and there is no document instruction (YAGNI).
- A generic `requires_env` schema field. Readiness goes through the guard (#192).
- A shared "OpenAI-compatible embeddings" primitive. Kimchi (unmerged) + DoubleWord = 2 callers, below the Rule of 3.
- DoubleWord reranking (none offered) and chat models.
- Merging the kimchi branch.

## Output contract
> Observable shape of completion (shape only, not exact file paths).
- **Baseline**: current TRAIL/PROGRESS status and `git status` recorded before edits; `expand_sweep` output snapshot for **every** `configs/{mongodb,supabase}/*.yaml` captured on `main`.
- A config listing `all-MiniLM-L6-v2`, a Voyage 1024-dim model and `Qwen/Qwen3-Embedding-8B` with **no** `embedding.provider` expands to runs whose `embedding_provider` is `local` / `voyage` / `doubleword` respectively.
- Every pre-existing example config expands to exactly the baseline snapshot (byte-identical `RunParams` list).
- With the key set: an experiment using the DoubleWord example config finishes `complete`, and its results show `embedding_provider=doubleword` next to other providers (dashboard + `GET /experiments/{id}`).
- Without the key: `POST /experiments` with a DoubleWord model returns **422**, naming `DOUBLEWORD_API_KEY`, and creates no experiment. Non-DoubleWord configs still return 200.
- `docs/adr/ADR-005-doubleword-embedding-provider.md` exists with status **Proposed** and a filled V1, V2, V8, V9 results table.

## Acceptance Criteria

### T0 — Verification spike (Must, ≤30 min, before production code; needs `DOUBLEWORD_API_KEY`)
- [ ] `scripts/spikes/dw_embed_spike.py` (opt-in, not imported by server/tests) answers **V1** (`dimensions` honoured?), **V2** (default dim), **V8** (10 sequential realtime calls: error rate and p50/p95 latency), and **V9** (exact model id accepted and query-prefix format (`Query:` with or without a trailing space)).
- [ ] Results recorded in the ADR-005 draft. **If V1 = NO** → S2 requests full vectors and truncates + L2-renormalizes client-side (brief §6.4). **If V8 shows realtime unusable** → STOP and escalate (HITL): 48A's skateboard premise fails and 48B moves first.
- [ ] No key available → the spike is recorded as `NOT RUN`; S1 proceeds; S2 proceeds on the documented OpenAI-compatible contract with V1 assumed NO (the safe path).

### S1 — Mixed-provider embedding axis (Must)
- [ ] `EmbeddingConfig.provider` becomes optional (`None` default). When set, the existing single-provider validation still applies (back-compatible). When omitted, models may come from any registered provider.
- [ ] One helper owns "provider for model" (`model_registry`). `expand_sweep` and guards call it; no parallel lookup.
- [ ] `sie_guard` fires if **any** configured model is SIE (not only when `embedding.provider == "sie"`).
- [ ] `sweep_summary.embedding_provider` stays a string for single-provider experiments. Mixed experiments get the new field `embedding_providers: list[str]`, and the frontend detail badge renders all values. The TS type is updated in `frontend/src/types/index.ts`.
- [ ] CLI `config_loader` accepts the provider-less form; `docs/user-guide/configuration.md` documents both forms.

### S2 — DoubleWord realtime provider (Must)
- [ ] `"doubleword"` added to `Provider`. The duplicate literal in `status.py` is replaced by an import from `config.py` (Duplication Horizon: the file is touched, and this leaves one owner).
- [ ] Registry entry `Qwen/Qwen3-Embedding-8B`: `provider=doubleword`, `dimensions=1024`, `contextualized=False`.
- [ ] `server/core/embedding/doubleword_embedder.py` provides `embed_documents_doubleword(texts, model_id, cancel_check=None) -> list[list[float]]` and `embed_query_doubleword(text, model_id) -> list[float]`. It uses a sync `httpx.Client` singleton, `POST {base}/embeddings` with list `input` in bounded batches, sends `dimensions` only when V1 = YES, and preserves input order. It checks returned vector length (mismatch → raise, never silently store). Retries 429/5xx with exponential backoff (max 4). **Fails fast** on 401/403/404 with `DoublewordUnavailableError`. Calls `cancel_check()` between batches.
- [ ] Query texts are formatted with the Qwen3 instruction prefix (fixed constant); documents are plain text.
- [ ] `server/settings.py`: `doubleword_api_key: SecretStr | None`, `doubleword_base_url` (default `https://api.doubleword.ai/v1`). The key is never logged.
- [ ] `embedder_factory.get_embedder("doubleword")` branch; error message lists it among supported providers.
- [ ] `server/core/guards/doubleword_guard.py::validate_doubleword_readiness(config)` raises when any model is DoubleWord and the key is unset. It is wired at the **same two call sites** as `validate_sie_readiness` (`server/api/experiments.py` submit → 422; orchestrator start).
- [ ] Example configs `configs/mongodb/example-doubleword.yaml` + `configs/supabase/example-doubleword.yaml` (DoubleWord only), and `configs/mongodb/example-provider-compare.yaml` (local + Voyage 1024 + DoubleWord, provider omitted).
- [ ] Docs: `docs/user-guide/doubleword-setup.md` (key from app.doubleword.ai, realtime is best-effort, cost note, M0 note: no new index at 1024), `.env.example`, `configuration.md`, `docs/contributor-guide/extending.md`, `CLAUDE.md` Key Files + Provider System, `README.md` stays vendor-neutral ("batch-priced embedding providers").

## Files Changed (expected)

| File | Change |
|---|---|
| `server/models/config.py` | `Provider` += `doubleword`; `EmbeddingConfig.provider` optional; `expand_sweep` derives provider per model |
| `server/models/status.py` | import `Provider` from `config.py` (dedupe) |
| `server/core/model_registry.py` | DoubleWord entry; `provider_for_model()` helper |
| `server/core/embedding/doubleword_embedder.py` | **new** realtime client |
| `server/core/embedding/embedder_factory.py` | `doubleword` branch |
| `server/core/guards/doubleword_guard.py` | **new** readiness guard |
| `server/core/guards/sie_guard.py` | per-model SIE detection |
| `server/api/experiments.py`, `server/core/pipeline/orchestrator.py` | wire guard next to SIE guard; `embedding_providers` summary |
| `server/settings.py` | DoubleWord settings |
| `frontend/src/types/index.ts`, `ExperimentDetailScreen.tsx` | multi-value provider badge |
| `configs/{mongodb,supabase}/example-doubleword.yaml`, `configs/mongodb/example-provider-compare.yaml` | **new** |
| `tests/server/core/embedding/test_doubleword_embedder.py`, `tests/server/core/guards/test_doubleword_guard.py`, `tests/server/models/test_mixed_provider_expansion.py`, `tests/test_config_examples.py` | GWT tests |
| `scripts/spikes/dw_embed_spike.py`, `docs/adr/ADR-005-doubleword-embedding-provider.md`, docs listed above | spike + ADR (Proposed) + docs |

## GWT Scenarios (acceptance tests: author RED first)

```gherkin
Feature: Mixed-provider embedding axis

  Scenario: Provider is derived per model when embedding.provider is omitted
    Given an ExperimentConfig with embedding.models [all-MiniLM-L6-v2, voyage-3.5-lite, Qwen/Qwen3-Embedding-8B] and no embedding.provider
    When expand_sweep is called with 1 chunking method, 1 size, 1 overlap and 1 dense retriever
    Then exactly 3 runs are returned
    And their embedding_provider values are local, voyage and doubleword in model order

  Scenario Outline: Existing example configs expand byte-identically (regression lock)
    Given the example config <path> as it exists on main
    When expand_sweep is called on the slice branch
    Then the RunParams list equals the snapshot captured on main
    Examples: every file under configs/mongodb/ and configs/supabase/

  Scenario: Explicit provider still rejects a mismatched model
    Given embedding.provider voyage and embedding.models [all-MiniLM-L6-v2]
    When the config is validated
    Then a ValueError names the model, its registered provider local and the configured provider voyage

  Scenario: Unknown model is rejected in the provider-less form
    Given no embedding.provider and embedding.models [not-a-model]
    When the config is validated
    Then a ValueError lists the known models

  Scenario: SIE guard fires for a mixed config containing an SIE model
    Given SIE_ENABLED is false and embedding.models [voyage-3.5-lite, bge-m3] with no provider
    When POST /experiments is called
    Then HTTP 422 mentions SIE_ENABLED and no experiment is created

  Scenario: Mixed experiment summary lists all providers
    Given a submitted mixed-provider config
    When GET /experiments/{id} is called
    Then sweep_summary.embedding_providers equals [local, voyage, doubleword]

Feature: DoubleWord realtime provider

  Scenario: Documents are embedded in input order at 1024 dims
    Given an httpx MockTransport answering /v1/embeddings with 1024-dim vectors tagged by input index
    When embed_documents_doubleword is called with 5 texts and batch size 2
    Then 3 HTTP requests are sent with model Qwen/Qwen3-Embedding-8B
    And 5 vectors of length 1024 are returned in input order

  Scenario: Query text carries the Qwen3 instruction; documents do not
    Given a MockTransport that records request bodies
    When embed_query_doubleword("what is RAG?") and embed_documents_doubleword(["RAG is"]) are called
    Then the query input starts with "Instruct: " and contains "Query:" followed by the query
    And the document input is exactly "RAG is"

  Scenario: Server returns the wrong dimension
    Given V1 = YES and a MockTransport returning 4096-dim vectors
    When embed_documents_doubleword is called
    Then a ValueError reports expected 1024 and got 4096, and nothing is returned

  Scenario: Client-side MRL fallback when dimensions is unsupported (only if V1 = NO)
    Given V1 = NO and a MockTransport returning 4096-dim vectors
    When embed_documents_doubleword is called
    Then each returned vector has length 1024, unit L2 norm, and is proportional to the first 1024 components

  Scenario: Transient 429 is retried
    Given a MockTransport that returns 429 once then 200
    When embed_documents_doubleword is called
    Then 2 requests are sent and vectors are returned

  Scenario Outline: Permission errors fail fast without retry
    Given a MockTransport that returns <status>
    When embed_documents_doubleword is called
    Then DoublewordUnavailableError is raised after exactly 1 request
    Examples: | status | 401 | 403 | 404 |

  Scenario: Retries exhausted
    Given a MockTransport that always returns 503
    When embed_documents_doubleword is called
    Then an error naming DoubleWord and the attempt count is raised after 4 attempts

  Scenario: Cancellation between batches
    Given 4 texts, batch size 2 and a cancel_check that raises on its second call
    When embed_documents_doubleword is called
    Then exactly 1 HTTP request is sent and the cancel exception propagates

  Scenario: API key never appears in logs
    Given DOUBLEWORD_API_KEY is "dw-secret-123" and a request fails with 500
    When the failure is logged
    Then no captured log record contains "dw-secret-123"

  Scenario: Missing key rejects a DoubleWord experiment at submit
    Given DOUBLEWORD_API_KEY is unset
    When POST /experiments is called with configs/mongodb/example-doubleword.yaml
    Then HTTP 422 names DOUBLEWORD_API_KEY and points to docs/user-guide/doubleword-setup.md
    And no experiment document exists

  Scenario: Missing key does not affect other configs (default-path safety)
    Given DOUBLEWORD_API_KEY is unset
    When POST /experiments is called with configs/mongodb/example-local.yaml
    Then HTTP 200 is returned

  Scenario: Factory dispatch
    When get_embedder("doubleword") is called
    Then it returns (embed_documents_doubleword, embed_query_doubleword)

  Scenario: No new vector index is required at 1024 dims
    Given configs/mongodb/example-doubleword.yaml with a dense retriever
    When required_search_indexes is computed
    Then it equals {vector_index_1024}

  Scenario: Postgres stores DoubleWord vectors in the 1024 column
    Given a 1024-dim DoubleWord chunk document
    When it is mapped to a Postgres row
    Then embedding_1024 is populated and embedding_384 is null

  @integration
  Scenario: Live smoke (opt-in, skipped without key)
    Given DOUBLEWORD_API_KEY is set
    When 3 texts are embedded realtime
    Then 3 vectors of length 1024 are returned
```

**Step reuse:** "Given a MockTransport …" and "When POST /experiments …" steps are shared fixtures (≥4 uses each). The MockTransport fixture lives in `tests/fixtures/doubleword.py` and 48B reuses it.

## Before-Checks
- [ ] Branch `slice/48a-doubleword-realtime` from latest `main`; `git diff --stat main` empty
- [ ] `./scripts/ci/quality-gates.sh` green on main (zero-regression baseline)
- [ ] Baseline `expand_sweep` snapshots for all example configs captured (Output contract)
- [ ] harness-scout `detect_confirm` against the TRAIL execution embed (or honour the degradation note, DECISIONS #197)
- [ ] T0 spike run, or recorded `NOT RUN` with the V1-NO safe path chosen

## After-Checks
- [ ] `./scripts/ci/quality-gates.sh` pass (ruff, mypy, pytest unit tier, FE lint/test/typecheck/build, audits)
- [ ] Specification coverage: every GWT scenario above maps to ≥1 named test; all error paths (422, 401/403/404, retries exhausted, dim mismatch, cancel) covered
- [ ] Coverage: new modules `doubleword_embedder.py` and `doubleword_guard.py` at 100% line + branch; backend floors (#142) and FE floors 95/90/95/95 unchanged or higher
- [ ] Complexity evidence: xenon **enforcing** E/C/C on `server/ cli/` (no new function above B; `expand_sweep` must not grow above its current rank), plus `bash scripts/ci/complexity-report.sh` → `.reports/complexity/pr-body.md`
- [ ] Mutation testing on `doubleword_embedder.py` + provider derivation: ≤10% survivors or a documented waiver
- [ ] Stub scan: no `TODO`/`FIXME`/`NotImplemented`/bare `pass` in new files
- [ ] Manual (with key): `rag-params-finder run --config configs/mongodb/example-provider-compare.yaml` → `complete`; dashboard shows 3 providers
- [ ] Manual (without key): the same command prints the 422 message; `example-local.yaml` still runs
- [ ] Doc audit → YES (files listed in S2); `/sync-docs` run
- [ ] Security audit → YES (new outbound HTTP + secret): key via `SecretStr`, not logged, TLS base URL, no key in configs

## Commits
```
test(embedding): lock example-config sweep expansion before mixed providers
feat(config): derive embedding provider per model so one sweep can compare providers
feat(embedding): add DoubleWord Qwen3-Embedding-8B realtime provider behind key guard
docs(doubleword): setup guide, example configs and ADR-005 (Proposed)
```

### Closing Gates
- [ ] `nw-at-completeness-check` — AT completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline review (slice close gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data flow review (gate #9, parallel: new provider path + per-run provider derivation)
- [ ] `nw-researcher-reviewer` — V-spike evidence in ADR-005 (external integration)
- [ ] `nw-documentarist-reviewer` — setup guide + configuration reference
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass (`docs/plan/gate-evidence/slice-48A.json`, incl. `coverage_pct`, `branch_pct`, `coverage_target`, `complexity_tool`, `complexity_ceiling`, `complexity_passed`)
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)
