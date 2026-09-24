# Slice 48B — DoubleWord Cost Capture + Batch Hardening + Pre-Embed Progress UI

**Status**: 📋 PLANNED
**Branch**: `slice/48b-doubleword-cost-hardening`
**Estimated time**: ~5–6 h in four ordered streams (T0 spike · S1 cost · S2 double-billing + cross-experiment adoption · S3 progress UI · S4 ctx-limit diagnostics)
**MoSCoW**: Must (owner decisions 2026-09-24; DECISIONS #189, #194, #199–#203)
**Source brief**: [`BRIEF-doubleword-embedder.md`](../../BRIEF-doubleword-embedder.md) §5.3, §7.2, §8, Appendix A. This spec wins where they differ.
**Reference implementation**: `playgroup_202602_docextract` → `llm_doubleword.py`, `extractor.py::_run_all_doubleword`, `sync_doubleword_models.py::extract_ctx_from_error`, `DW_FB.md` #1/#4/#5/#9/#10.

> Rescoped on 2026-09-24 (#202): the batch client, cache, pre-embed submission, detached watcher and boot resume moved **into 48A** (batch-first). 48B hardens that path and makes its cost visible.

## Problem

After 48A, DoubleWord sweeps work and survive restarts, but four gaps remain:

- **No cost visibility.** The whole point of DoubleWord is price, yet results carry no token or cost fields, so there's no quality-vs-cost comparison.
- **Double-billing risk.** A lost `.rpf_state` checkpoint file means a resubmission pays twice.
- **Duplicate batches.** Two experiments needing the same texts submit duplicate batches.
- **Poor feedback.** Users only see a JSON `pre_embed` object, and context-length rejections are reported as generic failures.

## Goal

- Every DoubleWord run and experiment reports tokens and cost.
- A batch is never paid for twice for the same job, even without the local checkpoint file.
- Experiments needing the same job share one batch.
- The dashboard shows pre-embed progress with a link to the DoubleWord dashboard.
- Context-limit rejections name the actual limit and the chunk config to shrink.

## Context
> Read before any implementation. Do not rely on conversation history alone.
- **Stage objective**: make the 48A batch path cost-transparent and billing-safe.
- **Depends on**: **48A** ✅ (batch client, cache rows with `prompt_tokens`, checkpoint store, watcher, `pre_embed` object, ADR-005 Proposed).
- **Global invariants**: → [`docs/plan/invariants.md`](../../invariants.md).
- **Codebase realities**:
  - The run/experiment docs are dicts persisted via `StorageBackend` (Postgres `doc` JSONB), so new fields need no DDL. Verify in S1.
  - The DoubleWord batch result JSONL has `usage.prompt_tokens` but **no cost** (DW_FB #1/#5). The undocumented `GET /batches/{id}/analytics` returns `total_cost` and must be called via `httpx` (not the OpenAI surface) and degrade gracefully (knowledge doc §2.3).
  - Pricing differs by window: 24h is 30–50% cheaper than 1h (DW_FB Pricing). Docs model ids have diverged from API ids before, so the registry's id stays authoritative and prices are manual config.
> The executor may diverge from the plan if new evidence warrants. Document deviations in PROGRESS.md before marking PASSED.

## Non-goals
> Out of scope for this slice. Do not implement here.
- Automatic pricing sync from docs (docextract keeps it disabled because docs ids mismatch).
- Pareto (quality vs cost) chart; CSV/JSONL export columns (→ Slice 28 once merged).
- Cache purge CLI/eviction (Could).
- Realtime pricing path (→ 48D).
- `dimensions` / `query_instruction` axes (→ 48C).

## Output contract
> Observable shape of completion (shape only, not exact file paths).
- **Baseline**: TRAIL/PROGRESS status + `git status`; a Voyage-only golden result set captured before edits.
- Each DoubleWord run result carries `embed_mode="batch"`, `completion_window`, `embed_tokens_docs`, `embed_tokens_queries`, `embed_cost_usd` (list-price cost of that config, independent of cache state).
- The experiment `pre_embed` carries `tokens`, `cost_incurred_usd` (analytics `total_cost` if available, else tokens × price[window]) and `elapsed_s` from API timestamps.
- Deleting `.rpf_state/doubleword_batches.json` mid-batch and resubmitting the same config → the in-flight remote batch is **adopted** (found by `metadata.job_key`), not paid again.
- Two experiments needing the same job while one batch is pending → one batch, and both complete.
- The detail screen shows "Waiting for DoubleWord batch — n/N (open in DoubleWord ↗)" while `pre_embed.state=waiting`.
- A context-length rejection message names the detected token limit and the offending chunk config.
- The Voyage-only golden results are byte-identical; ADR-005 → **Accepted** with V7 + V10 results.

## Acceptance Criteria

### T0 — Spike additions (Must; needs key)
- [ ] **V7** (`GET /batches/{id}/analytics` → `total_cost`, via `httpx`) and **V10** (`client.batches.list()` returns `metadata`, incl. `job_key`). Record in ADR-005.
- [ ] **If V10 = NO** → adoption degrades to checkpoint-only. Document the double-billing risk in `doubleword-setup.md`; log it in DECISIONS.

### S1 — Cost capture (Must)
- [ ] Registry entry gains `price_per_mtok: {"1h": float, "24h": float}` (optional `TypedDict` field; other models omit it). Values are HITL-confirmed from the DoubleWord models page at slice start.
- [ ] Per-run fields above, computed from cache-row `prompt_tokens`, so cache hits still report the config's list price.
- [ ] Per-experiment `cost_incurred_usd`: analytics via `httpx` (5 s timeout, 1 retry), else tokens × price[window]. Analytics failure → WARN, never fails the experiment.
- [ ] Fields round-trip on Mongo and Postgres, and are shown in the detail run table (FE type + render test).

### S2 — Double-billing guard + cross-experiment adoption (Must)
- [ ] Before any `submit_batch`: (1) a local checkpoint for `job_key` → attach to it; (2) else `batches.list()` recent pages → adopt a batch with the same `metadata.job_key` in `{validating, in_progress, finalizing, completed}`; (3) else submit.
- [ ] Checkpoint entries become `{job_key, batch_id, experiment_ids: [...]}`, so one batch serves several waiting experiments. The watcher schedules each experiment when **all** its jobs are ready.
- [ ] Atomic checkpoint writes guarded by a process lock (the watcher and sweep thread both write).

### S3 — Pre-embed progress UI (Should inside a Must slice)
- [ ] `frontend/src/types/index.ts` `PreEmbed` type. The progress card on the detail screen shows state, per-batch `completed/total`, elapsed time and the `dashboard_url` link. It also shows the reason when `failed`, and when the model is marked unavailable. Vitest render tests for waiting / ready / failed.

### S4 — Context-limit diagnostics (Should inside a Must slice)
- [ ] Port `extract_ctx_from_error` (regex over error-file messages, rounded to thousands, ignores < 1000). A failed experiment's message names the detected limit, and the chunk config(s) whose chunks exceeded it.
- [ ] Plan-time guard: estimated tokens (existing tokenizer helper, conservative chars/token) > registry context (32K) → 422 at submit naming the chunk config.

## GWT Scenarios (acceptance tests: author RED first)

```gherkin
Feature: Cost capture

  Scenario Outline: Run results carry token and list-price cost on both backends
    Given a completed DoubleWord experiment on <backend> with completion_window 24h
    When results are read back
    Then every DoubleWord run has embed_mode batch, embed_tokens_docs > 0 and embed_cost_usd = tokens × 24h price
    Examples: | mongodb | postgres |

  Scenario: Repeat experiment is not billed again but still priced
    Given the cache already holds every text of experiment A
    When experiment B with the same corpus and model completes
    Then no paid DoubleWord batch is created, pre_embed.cost_incurred_usd is 0, and each run's embed_cost_usd is > 0

  Scenario: Cost prefers analytics, falls back to tokens × price
    Given analytics returns total_cost 0.0123 for the experiment's batch
    Then pre_embed.cost_incurred_usd is 0.0123
    Given analytics fails
    Then cost_incurred_usd = prompt_tokens × window price / 1e6, a warning is logged, and the experiment still completes

  Scenario: Voyage-only golden results unchanged (regression)
    Given the Voyage-only golden config captured before edits
    When it is re-run with stubbed Voyage responses
    Then the persisted result documents equal the baseline apart from timestamps and ids

Feature: Billing safety

  Scenario: Lost checkpoint adopts the remote batch instead of paying twice
    Given no local checkpoint for job J
    And the stubbed DoubleWord API lists batch b-1 with metadata.job_key J in progress
    When an experiment needing J is submitted
    Then b-1 is attached and no new batch is created

  Scenario: Remote batch in a terminal failure state is not adopted
    Given the stubbed DoubleWord API lists batch b-1 for job J as expired
    When an experiment needing J is submitted
    Then a new batch is created for J

  Scenario: Two experiments needing the same job share one batch
    Given experiment X is waiting on batch b-1 for job J
    When experiment Y needing J is submitted
    Then no new batch is created and both X and Y complete after b-1 completes

Feature: Progress and diagnostics

  Scenario: Detail screen shows waiting progress with a DoubleWord link
    Given pre_embed.state waiting with one batch at 40 of 100
    When the detail screen renders
    Then it shows "40 / 100" and a link to the batch on app.doubleword.ai

  Scenario: Context-length rejection names the limit and the chunk config
    Given the error file rejects k3 with "maximum context length is 32768 tokens"
    When the retry also fails
    Then the experiment failure message names 32000 tokens and the chunk config that produced k3

  Scenario: Oversized chunk is rejected at submit
    Given a chunk config whose largest chunk is estimated above the model context
    When the experiment is submitted
    Then it is rejected (422) naming the chunk config
```

## Before-Checks
- [ ] 48A ✅ PASSED (gate evidence + `/verify-slice` COMPLETE)
- [ ] Branch from latest `main`; `git diff --stat main` empty; `./scripts/ci/quality-gates.sh` green
- [ ] HITL: `price_per_mtok` values confirmed and logged
- [ ] harness-scout `detect_confirm`

## After-Checks
- [ ] `./scripts/ci/quality-gates.sh` pass; every GWT scenario ↔ ≥1 test
- [ ] Coverage 100% line + branch on the cost, adoption and ctx-parse units; floors unchanged or higher
- [ ] Complexity evidence: xenon **enforcing** E/C/C; `.reports/complexity/pr-body.md`
- [ ] Mutation testing on the cost formula + adoption triage: ≤10% survivors or a waiver
- [ ] Manual (with key): delete the checkpoint file mid-batch → resubmit → the same `batch_id` is adopted; the cost shown matches the DoubleWord dashboard
- [ ] Doc audit → YES: `doubleword-setup.md` (cost fields, window pricing, adoption behaviour), `configuration.md`, ADR-005 → Accepted
- [ ] Security audit → YES: analytics call uses the same SecretStr header; no key in logs or state files

## Commits
```
feat(results): capture DoubleWord embedding tokens and cost per run and experiment
fix(pipeline): adopt in-flight DoubleWord batches by job key to prevent double billing
feat(dashboard): show DoubleWord pre-embed progress with provider link
feat(pipeline): name the context limit and chunk config on DoubleWord rejections
docs(doubleword): cost fields and ADR-005 accepted
```

### Closing Gates
- [ ] `nw-at-completeness-check` — AT completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline review (slice close gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data flow review (gate #9, parallel: adoption + shared batches)
- [ ] `nw-data-engineer-reviewer` — result fields on both backends
- [ ] `nw-researcher-reviewer` — V7/V10 evidence in ADR-005
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass (`docs/plan/gate-evidence/slice-48B.json`)
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)
