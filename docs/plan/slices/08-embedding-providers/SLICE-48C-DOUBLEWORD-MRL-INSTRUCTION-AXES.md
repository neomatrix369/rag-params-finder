# Slice 48C — MRL `dimensions` Axis + `query_instruction` Axis

**Status**: 📋 PLANNED (design decision required at slice start; see Open design decisions)
**Branch**: `slice/48c-embedding-dim-instruction-axes`
**Estimated time**: ~4–6 h (depends on the Postgres option chosen)
**MoSCoW**: Should (owner decision 2026-09-24; DECISIONS #189, #196). Start only after 48B ✅.
**Source brief**: [`BRIEF-doubleword-embedder.md`](../../BRIEF-doubleword-embedder.md) §6.4, §12.

## Problem

Qwen3-Embedding-8B supports Matryoshka (MRL) output sizes of 32–4096 and task instructions on queries. Both change retrieval quality and storage cost. The owner wants them as sweep axes, so the sweep can answer "is 512-dim good enough?" and "does the instruction help on my data?".

## Goal

A DoubleWord config can sweep `dimensions` (e.g. `[512, 1024, 2048]`) and `query_instruction` (e.g. `[null, "<task>"]`). There is **one paid document embedding pass at max(dimensions)**; lower dims are derived by truncate + L2-renormalize from the 48B cache. Instruction variants **reuse the stored document vectors** and re-embed only queries.

## Context
> Read before any implementation. Do not rely on conversation history alone.
- **Stage objective**: new sweep axes for embedding shape and query instruction.
- **Depends on**: **48B** ✅ (cache with full-dim storage, pre-embed step, cost fields).
- **Global invariants**: → [`docs/plan/invariants.md`](../../invariants.md). Identity namespace changes (index/column names) = **HITL + ADR** per `DECISION-OWNERSHIP.md`.
- **Hard storage constraints found in recon (2026-09-24)**:
  - Mongo: vector indexes are `vector_index_{dims}` on the shared `embedding` field with an `embedding_model` filter. Every new dimension = one more Atlas search index, counted by `search_index_plan`'s capacity assessment (the M0/shared-tier cap is already near its limit with 384/1024/30522 + text). The capacity check must fail **at submit**, never mid-run.
  - Postgres: `schema.sql` has only `embedding_384` and `embedding_1024` columns. **pgvector HNSW indexes support `vector` only up to 2000 dims.** 2048/4096 would need `halfvec` (≤4000) or exclusion.
  - Run identity: `_run_config_key` (results_analyzer) and `pipeline/signatures.py` key on `embedding_model`, so dim/instruction must enter identity and the mandatory `embedding_model` filter, or vectors of different dims/instructions mix.
> The executor may diverge from the plan if new evidence warrants. Document deviations in PROGRESS.md before marking PASSED.

## Open design decisions (HITL at slice start; log in DECISIONS)

| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | How the axes appear in config | (a) `embedding.axes: {dimensions: [...], query_instruction: [...]}` scoped to MRL-capable models; (b) derived model-id variants `Qwen/Qwen3-Embedding-8B@512` | (a). Keeps the registry id clean; expansion adds two product dimensions for MRL models only |
| D2 | Postgres dims beyond 1024 | (i) allowlist `{384, 512, 1024}` on Postgres and reject others with 422; (ii) add `halfvec` columns for 2048/4096; (iii) a generic column per dim | (i) for the Should scope. Column/namespace growth is HITL + ADR |
| D3 | Stored `embedding_model` value | a composite like `Qwen/Qwen3-Embedding-8B#d512`, or a separate `embedding_dim` filter field | Composite. Rides the existing mandatory filter with no new index filter field |

## Non-goals
- MRL for non-DoubleWord models (Voyage dims are fixed in the registry; revisit when a second MRL model appears — Rule of 3).
- Document-side instructions (Qwen3 guidance: documents are plain text).
- A dim-vs-quality-vs-storage report view (separate Tier-3 spec).

## Output contract
- **Baseline**: current TRAIL/PROGRESS status and `git status`; expansion snapshots for all example configs.
- A config with dimensions `[512, 1024]` × instruction `[null, I]` expands to 4× the runs of its non-axis equivalent, and every run's identity string contains both values.
- A document batch is paid **once** at max dim: the stubbed DoubleWord API bills 1 document batch for all dims.
- Instruction variants share document vectors: only query batches differ.
- Unsupported combinations (Postgres dim not allowlisted, or index capacity exceeded) → 422 at submit with an actionable message.

## GWT Scenarios

```gherkin
@pending_decision_D1
Scenario: Axis expansion count
  Given 1 DoubleWord model, dimensions [512,1024,2048], query_instruction [null, "Given a question…"] and 1 chunk config
  When expand_sweep is called
  Then 6 runs are returned and each identity includes its dim and instruction hash

Scenario: One paid document pass serves every dimension
  Given batch mode, dimensions [512,1024,2048] and an empty cache
  When the experiment runs
  Then exactly 1 document batch is submitted at dim 2048
  And stored vectors at 512 and 1024 are unit-norm prefixes of the 2048 vector

Scenario: Truncation rejects larger-than-source dims
  When truncate_and_normalize is called with dim 4096 on a 2048 vector
  Then a ValueError is raised

Scenario: Instruction variants reuse document vectors
  Given query_instruction [null, I]
  When the experiment runs
  Then 1 document batch and 2 query batches are submitted
  And both instruction runs query the same stored chunk rows

@pending_decision_D3
Scenario: Vectors of different dims never mix in retrieval
  Given stored chunks at 512 and 1024 for the same experiment
  When a 512 run queries
  Then only rows whose embedding_model identity has dim 512 are searched

@pending_decision_D2
Scenario: Postgres rejects a non-allowlisted dim at submit (if D2 = i)
  Given STORAGE_BACKEND postgres and dimensions [2048]
  When POST /experiments is called
  Then HTTP 422 lists the supported Postgres dims

Scenario: Postgres rejects any dimension above the pgvector HNSW limit (independent of D2)
  Given STORAGE_BACKEND postgres and dimensions [4096]
  When POST /experiments is called
  Then HTTP 422 states the 2000-dim HNSW limit for vector columns

Scenario: Atlas index capacity exceeded is caught at submit
  Given the cluster tier cannot host another vector index
  When a config requiring vector_index_512 is submitted
  Then HTTP 422 names the required index and the capacity limit
```

## Before-Checks
- [ ] 48B ✅ PASSED
- [ ] D1–D3 decided (HITL) and logged in DECISIONS **before** any 48C code. No auto-proceed on the recommendations. ADR-005 amended if D2/D3 change the identity namespace; update the `@pending_decision` scenarios above to match.
- [ ] Branch from latest `main`; `./scripts/ci/quality-gates.sh` green

## After-Checks
- [ ] `./scripts/ci/quality-gates.sh` pass; every GWT scenario ↔ ≥1 test
- [ ] Coverage 100% line + branch on the axis expansion + truncation modules; floors unchanged
- [ ] Complexity evidence: xenon **enforcing** E/C/C; `expand_sweep` rank must not worsen (extract an axis helper if needed)
- [ ] Mutation testing on identity composition + truncation: ≤10% survivors or a waiver
- [ ] Doc audit → YES: configuration.md axes, doubleword-setup.md storage notes, schema docs if D2 ≠ i
- [ ] Security audit → NO (no new inputs reaching shell/DB beyond validated ints/strings) unless D2 adds DDL

## Commits
```
feat(config): sweep MRL dimensions and query instruction for DoubleWord models
feat(pipeline): derive lower MRL dims from one full-dim embedding pass
```

### Closing Gates
- [ ] `nw-at-completeness-check` — AT completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline review (slice close gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data flow review (gate #9, parallel: identity + index namespace)
- [ ] `nw-data-engineer-reviewer` — Postgres/Atlas dimension handling
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass (`docs/plan/gate-evidence/slice-48C.json`)
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)
