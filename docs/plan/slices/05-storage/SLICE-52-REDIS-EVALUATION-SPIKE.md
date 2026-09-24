# SLICE 52 — Redis Evaluation Spike + Decision Record (docs + throwaway PoC)

**MoSCoW:** MUST *(proposed — owner to confirm, #227)*
**Target time:** ~6–8 h in six ordered streams (R0 delta ~45 min · R1 candidates ~1 h · R2 adoption ~1 h · R3 PoC ~1.5 h · R4 Branch B ~45 min · R5 scoring + outputs ~2 h)
**Status:** 📋 PLANNED
**Depends on:** none (hard). Soft: Slice 49 / 50 / 51 **specs** (read as fixed inputs — their code need not exist). May run in parallel with Slice 49 execution.
**Branch:** `slice/52-redis-evaluation-spike`
**Feature:** Redis as vector store (Branch A) + supporting infrastructure (Branch B) — ADR-007
**Source:** [`BRIEF-redis-evaluation.md`](../../BRIEF-redis-evaluation.md) (owner prompt v2, verbatim + reconciliation)

> **Fusion note (#224):** the prompt's Steps 0, 0B, 0C, 1, 2, 3A, 3B, 4 and 5 are fused into **one** research slice because they share one evidence base and one output pair (report + HTML). Steps 0 / 0B / 0C are **delta-only**: the Mongo/Postgres adapter review, target design and 15-stage journey already live in Slices 49 and 51 — this slice links them and adds the Redis column, instead of repeating the audit.

---

## Context

Produce the evidence-backed decision for whether and how Redis joins rag-params-finder. The outputs are a Markdown report, a self-contained HTML guide, `ADR-007` (**Proposed**) and a **GO / NO-GO** per branch that gates Slices 53 and 54. There is no product code: the PoC is a throwaway script run against `redis:8` / `valkey` containers and is not committed under `server/`.

- **Depends-on outputs:** Slice 49 target design (`VectorStoreAdapter`, `VectorCapabilities`, registry, `VECTOR_STORE_BACKEND`) and Slice 51 journey + docs-parity design are the fixed inputs; D1–D5 accepted (#215). Branch B anchors: 48A S3 `embedding_cache.py` (planned), `server/core/pipeline/executors.py`, `server/core/pipeline/experiment_control.py`, `server/core/embedding/rate_limiter.py`, Slice 16 Approach B.
- **Invariants pointer:** `docs/plan/invariants.md`. Cost gate: $0 and no card. Self-hosted wins ties. Default store stays `mongodb` (#130).

## Non-goals

- Any edit under `server/`, `cli/`, `frontend/`, `scripts/`, `configs/`, compose files or workflows (all → Slice 53 / 54).
- Re-auditing Mongo/Postgres adapter design or the 15-stage journey from scratch. Link Slice 49 / 51 and record only drift found since `dcdbd6f`.
- Auditing Elasticsearch code (there is none on `main`).
- Evaluating paid tiers beyond a one-line upgrade-path note.
- Deciding MoSCoW, D1–D5 changes, image licence choice or GO / NO-GO. Those are **HITL**: the slice recommends and the owner decides.

## Output contract

- **Baseline:** `ls docs/_internal/ docs/adr/` shows neither `REDIS-EVALUATION.md` nor `ADR-007-*`.
- `docs/_internal/REDIS-EVALUATION.md` with every RESPONSE section of the brief, in order. Every metric has a source URL + retrieval date, or appears under **Coverage Gaps**.
- `docs/_internal/redis-evaluation.html`: a single file with zero external `<script>`/`<link>`/`@import`/font requests, light/dark, mobile-safe, and a scoring table whose weights (default 50/30/20) recompute the ranking live.
- `docs/adr/ADR-007-redis.md` in status **Proposed**, mirroring the `ADR-004`/`ADR-006` shape.
- A PoC transcript (commands + outputs) embedded in the report appendix, tagged `"__mocked": false`, or `"__mocked": true` + `"__source"` where live access failed.
- DECISIONS rows recording the owner's GO / NO-GO for Branch A (→ 53) and Branch B cache (→ 54).

## Reuse ledger (reuse-first — don't reinvent the wheel)

| Need | Existing artifact to reuse | Action |
|---|---|---|
| Mongo/Postgres adapter review + four-place branching evidence | Slice 49 Context / Reuse ledger / grep baseline | **Reuse** — link and cite; record only drift since `dcdbd6f` |
| Target adapter design (protocol, capabilities, registry, switching) | Slice 49 Output contract + "Protocol scope" | **Reuse** verbatim as the target. The report adds Redis capability values only |
| `GET /api/stores`, FE labels, CLI thin-client fix, drift fixes | Slice 51 | **Reuse** — Redis consumes them, no redesign |
| 15-stage journey matrix + docs-parity check design | Slice 51 (journey docs + registry-driven gate generalising `test_config_examples.py`) | **Reuse** — add a Redis column; the parity check design is Slice 51's |
| "Adding a vector store" checklist | `docs/contributor-guide/extending.md` registry flow (Slice 49/51 doc exits) | **Extend** with the Redis-learned items (memory preflight, eviction, persistence) — proposed text only |
| Setup-guide outline | `docs/user-guide/postgres-setup.md` 11-section shape (as mirrored by ES in 51) | **Mirror** for the `redis-setup.md` outline |
| ADR shape | `docs/adr/ADR-004-postgresql-pgvector-vector-store.md` | **Mirror** for ADR-007 |
| Evaluation / comparison method | ES planning #217 reviewer triage; Slice 38 top-3 overlap method | **Reuse** the comparison method for the PoC relevance check |
| Branch B embedding cache | 48A S3 `cache_key(...)`, `get_many`/`put_many` (planned) | **Reuse** as the attach point. Redis = backend option, not a new cache |
| Branch B queue / rate limiting | `executors.py`, `experiment_control.py`, `rate_limiter.py`, Slice 16 Approaches A/B | **Reuse** as evidence for the Won't / flip-trigger verdicts |
| Brief-with-reconciliation pattern | `BRIEF-doubleword-embedder.md` | **Reused** already for `BRIEF-redis-evaluation.md` |
| **Net-new (only)** | Candidate / adoption / free-tier research, PoC script (scratch), report + HTML + ADR-007 prose | Write new — the Redis-specific evidence |

---

## Slice Workflow Bundle

- Slice name: `slice-52-redis-evaluation-spike`
- Branch: `slice/52-redis-evaluation-spike`
- Files (expected):
  - `docs/_internal/REDIS-EVALUATION.md` — **new** (report)
  - `docs/_internal/redis-evaluation.html` — **new** (single-file guide)
  - `docs/adr/ADR-007-redis.md` — **new** (Proposed)
  - `docs/plan/DECISIONS.md`, `docs/plan/TRAIL.md`, `docs/plan/slices/PROGRESS.md` — **edit** (GO/NO-GO rows; 53/54 status)
  - PoC script: session scratchpad only (e.g. `poc_redis_vectors.py`); **not** committed
- Streams:
  - **R0 — Delta surface map (~45 min):** re-run Slice 49's grep baseline on current `main`; confirm 49/51 file refs are still valid (`/divergence-check`). Fill the **Redis planned** column of the parity + journey matrices with the file each stage will touch.
  - **R1 — Candidates + free gate (~1 h):** Redis Open Source 8.x + Query Engine, Vector Sets, Redis Stack (status), Redis Cloud free, RedisVL, `redis-py`, `langchain-redis` / LlamaIndex Redis, LangCache, RQ / arq / Celery / Huey, Valkey + valkey-search (label **not Redis Inc.**), Upstash, Aiven for Valkey. Official sources only; drop discontinued options with the reason.
  - **R2 — Adoption & outreach (~1 h):** GitHub / PyPI / Docker Hub / vendor-outreach metrics with URL + date; flag conflicting signals.
  - **R3 — PoC (~1.5 h, throwaway):** against `redis:8` **and** a valkey-search image, run: `FT.CREATE` on HASH with TAG `embedding_model`/`experiment_id`/`run_id`, TEXT `text`, VECTOR `embedding_384` + `embedding_1024` (HNSW, COSINE, FLOAT32) → insert ~1k docs with mixed dims → filtered KNN on each field → BM25 text query → `FT.HYBRID` availability probe → score conversion check (`score = 1 − distance/2` vs `(1+cos)/2`) → `INFO memory` per 1k vectors → `maxmemory-policy` behaviour → restart with/without AOF. Record the **compatibility table** (Redis 8 vs Valkey) and the client choice evidence (`redis-py` vs RedisVL).
  - **R4 — Branch B verdicts (~45 min):** one row each for embedding cache, semantic/LLM cache, job queue, rate limiting, CI speed-ups: adapter · default impl · attach point (file path) · benefit · ops cost · self-hosted vs managed · verdict · flip trigger.
  - **R5 — Scoring + outputs (~2 h):** per-branch weighted tables (50/30/20) + equal-weight sensitivity, primary / fallback / flip conditions, combined deployment (one vs two instances; eviction + persistence as adapter config), Redis touchpoint plan against the checklist covering all 15 stages, zero-changes verdict, sequencing vs 49–51, walkthrough + sample `configs/redis/*.yaml` (illustrative), `redis-setup.md` outline, snippets (all marked illustrative). Then the HTML guide and ADR-007 (Proposed).
- Exit criteria: all GWT below evidenced; owner GO / NO-GO recorded; 53/54 stubs updated to match the decision (MoSCoW / scope) or deferred.
- Commit pattern: `docs(research): Redis evaluation report + guide + ADR-007 (Proposed)`
- **Doc exit (Must):** report + HTML + ADR-007 + DECISIONS/TRAIL/PROGRESS. `docs/adr/` index / `docs/README.md` link to ADR-007 once it exists.

---

## Spec (GWT)

```gherkin
Feature: Redis evaluation produces an evidence-backed, owner-decidable recommendation

  Scenario: Every candidate has a free-gate verdict backed by an official source
    Given the candidate list in the brief (Step 1)
    When the report's candidate table is complete
    Then every candidate shows branch, hosting model, adapter implemented and a PASS/FAIL free-gate verdict
      And each verdict cites an official URL with a retrieval date
      And discontinued or renamed offerings are listed as dropped, with the reason

  Scenario: Every adoption number is cited or declared a Coverage Gap
    Given the adoption metrics in Step 2
    When a metric cannot be retrieved from a public source
    Then it appears under Coverage Gaps and never as an estimate in the scoring table

  Scenario: The report reuses the Elasticsearch-track review instead of repeating it
    Given Slices 49 and 51 already hold the Mongo/Postgres adapter review, target design and 15-stage journey
    When the report's surface map, parity matrix and journey sections are read
    Then they link those slices for Mongo/Postgres
      And the only new content is the Redis column plus drift found since dcdbd6f

  Scenario Outline: PoC proves D4 filtered dense search on per-dimension fields in one index
    Given a running <image> container with one index holding embedding_384 and embedding_1024 fields
    When a KNN query runs on <field> with embedding_model, experiment_id and run_id filters
    Then only documents that have that field and match all three filters are returned
      And the result is recorded as PASS or FAIL in the compatibility table
    Examples:
      | image         | field          |
      | redis:8       | embedding_384  |
      | redis:8       | embedding_1024 |
      | valkey-search | embedding_384  |
      | valkey-search | embedding_1024 |

  Scenario: Score convention matches the (1+cos)/2 scale used by Postgres and Elasticsearch
    Given Redis COSINE vector distance d for a query/document pair with cosine similarity c
    When the adapter score is computed as 1 - d/2
    Then it equals (1 + c)/2 within 1e-6 for the PoC sample

  Scenario: Memory-bound behaviour is measured, not assumed
    Given 1k, 10k and (extrapolated) 36k vectors of 1024 dims
    When INFO memory is sampled after each load
    Then the report gives bytes-per-vector including HNSW overhead
      And states which free tiers can or cannot hold a sweep-scale experiment

  Scenario: Branch B verdicts are anchored to real code paths
    Given the Branch B candidates (embedding cache, semantic cache, job queue, rate limiting, CI speed-ups)
    When each verdict is written
    Then it names the existing file or planned slice it would attach to
      And a Won't verdict states the concrete trigger that would flip it

  Scenario: Weights change the ranking visibly and reproducibly
    Given the HTML scoring table at the default weights 50/30/20
    When the viewer sets the weights to 33/33/34
    Then totals and rank order recompute without a reload
      And the report's sensitivity section names what drives any rank change

  Scenario: The HTML guide is fully self-contained
    Given docs/_internal/redis-evaluation.html
    When it is scanned for script src, stylesheet link, @import and web-font URLs
    Then none point to an external host
      (citation anchors to sources are allowed)

  Scenario: Divergence from D1–D5 is surfaced, never silent
    Given a Redis-specific reason that argues against one of D1–D5
    When the report is finalised
    Then the reason appears in Open questions with a recommended stance
      And no slice stub changes that decision until the owner records it in DECISIONS

  Scenario: ADR numbering does not collide
    Given ADR-005 (DoubleWord) and ADR-006 (Elasticsearch) are already assigned
    When the Redis ADR is created
    Then it is ADR-007 with status Proposed

  Scenario: The zero-changes criterion is assessed explicitly
    Given the touchpoint plan for a Redis vector adapter
    When it is compared with the acceptance criterion (no route, sweep, UI-component or CLI-command change)
    Then the report states MET, or lists each violating file and the Slice 49/51 gap that causes it
```

*(AT step-definition pass via `nw-distill` pending before 🔨 IN PROGRESS, same precedent as 49–51 (#216). This slice ships no product code, so its ATs are **evidence checks**: file existence, grep, the PoC transcript and the HTML scan.)*

---

## Before-Checks [GATE]

- [ ] Slice 49 and 51 specs on the branch (the fixed inputs); D1–D5 recorded (#215).
- [ ] Docker available locally for the PoC; images pulled: `redis:8` and a valkey-search image (exact tag chosen in R1).
- [ ] harness-scout `detect_confirm` at slice start. Research + judgment-heavy: expect the planning tier. Degradation note #228 applies until run.
- [ ] Web access for official sources. If blocked, record it as a Coverage Gap and don't guess.

## After-Checks [GATE]

- [ ] Specification coverage: every GWT scenario above ↔ ≥1 evidence item (file, grep output, transcript excerpt) listed in gate evidence.
- [ ] Branch coverage: N/A — no product code (PoC is uncommitted scratch). Reason recorded in gate evidence.
- [ ] Complexity evidence: N/A — policy `reporting`; no source files changed (`git diff --stat -- server cli frontend` empty).
- [ ] `bash scripts/ci/repo-lint.sh` green (markdownlint on the report + ADR).
- [ ] HTML self-containment scan (grep for external `src=`/`href=` on script/link, `@import`, `url(http`) → zero hits.
- [ ] Owner GO / NO-GO for Branch A and Branch B recorded in DECISIONS; 53/54 stubs aligned.
- [ ] `docs/plan/gate-evidence/slice-52.json` written by the executor (docs-only schema: `coverage_pct: null` with reason, `complexity_passed: "n/a"`, evidence list).

---

### Closing Gates

- [ ] `nw-at-completeness-check` — evidence-check completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — **N/A** (no product code). Record the waiver in gate evidence.
- [ ] `nw-researcher-reviewer` — every Redis/Valkey/free-tier fact is evidence-backed and dated; conflicting signals flagged
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — Redis capability values, memory/eviction/persistence stance and combined-deployment design reconcile with Slice 49 (no new SPOF, no store-string branching)
- [ ] `nw-documentarist-reviewer` — report/HTML/ADR structure (Diataxis: explanation + reference)
- [ ] `nw-gate-evidence-validator` — docs-only schema conditions pass
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)

## Gate Status

📋 PLANNED. The spec is drafted. The owner still has to confirm MoSCoW (#227); then the `nw-distill` evidence-check pass runs before 🔨 IN PROGRESS.
