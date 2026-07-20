# Trail
> ~3 min read (this doc) · [GAP_ANALYSIS](GAP_ANALYSIS.md) ~2 min · [DECISIONS](DECISIONS.md) ~2 min · [HANDOFF](HANDOFF.md) ~1 min · [PROGRESS](../slices/PROGRESS.md) ~2 min · [PRD Supabase](PRD-supabase-pgvector-migration.md) ~3 min

## Original Material

- **PCTO Spec** (`docs/PCTO-rag-params-finder-2026-06-27.md`): Add SIE as primary open-source inference backend (encode + score + extract), caller-supplied corpus (`corpus: list[str]` field on `SweepRequest`), Aim for experiment tracking, and two new API endpoints (`POST /api/v1/sweep`, `GET /api/v1/best-config`)
- **Supabase migration PRD** (`docs/plan/PRD-supabase-pgvector-migration.md`, 2026-07-09): Dual-backend storage Protocol; Postgres/pgvector + Supabase as target primary store; Mongo retained for rollback/A-B until Slice 38 cutover
- **Codebase** (v0.11.0, 20+ slices complete): Mature Voyage AI + local sentence-transformers RAG sweep pipeline, MongoDB Atlas, FastAPI, React dashboard, Docker, full CI toolchain
- **Constraints**: Hackathon deadline — Slice 21 targets Days 1–5; Voyage AI stays as numeric baseline (not replaced); PCTO changes remain additive; **Slice 39 is a ≤2 h demo interrupt, then storage migration resumes ahead of Slice 22** (2026-07-18)

Routing: Brownfield + Growing Requirement (Flow D) · Chosen: 2026-07-02 · Source: health-check-inferred · Reconfirmed: 2026-07-09 (Supabase PRD Add path)

Model split — Planning: claude-opus-4-8 · Execution: claude-sonnet-4-6

## Flow

**Brownfield + Growing Requirement** (Flow D) — mature codebase; PCTO + storage migration compose on existing pipeline via Protocol/adapters (Decision #10 upgraded only where dual-backend contract requires it).

## Slices

Each PCTO / migration slice lives in its own file below. Existing planned slices have spec files in `docs/slices/` — referenced here, not duplicated.

| # | File | Name | MoSCoW | Status | Depends on | Issue | Read time | Last Updated |
|---|------|------|--------|--------|------------|-------|-----------|--------------|
| 21 | [../slices/SLICE-21-SIE-SKATEBOARD.md](../slices/SLICE-21-SIE-SKATEBOARD.md) | SIE Skateboard — embeddings + Aim + `/api/v1/sweep` | Must | ✅ PASSED | none | — | ~4 min | 2026-06-29 |
| 25 | [../slices/SLICE-25-ATLAS-LOCAL.md](../slices/SLICE-25-ATLAS-LOCAL.md) | Atlas Local Dev Mode — `mongodb-atlas-local` as opt-in backend | Should | ✅ PASSED | 21 | — | ~2 min | 2026-06-29 |
| 25B | [../slices/SLICE-25B-ATLAS-SWITCHING.md](../slices/SLICE-25B-ATLAS-SWITCHING.md) | Atlas Backend Switching — single-flag cloud ↔ local switching | Should | ✅ PASSED | 25 | — | ~2 min | 2026-06-29 |
| 29 | [../slices/SLICE-29-PADDING-PROPAGATION.md](../slices/SLICE-29-PADDING-PROPAGATION.md) | Padding cross-cutting propagation — config key, API, types, UI | Must | ✅ PASSED | none | — | ~2 min | 2026-07-05 |
| 32 | [../slices/SLICE-32-STORAGE-BACKEND-PROTOCOL.md](../slices/SLICE-32-STORAGE-BACKEND-PROTOCOL.md) | Storage Protocol + Mongo adapter (Storage + Retriever ports) | Must | 📋 PLANNED | none | — | ~2 min | 2026-07-09 |
| 33 | [../slices/SLICE-33-POSTGRES-SCHEMA-CRUD.md](../slices/SLICE-33-POSTGRES-SCHEMA-CRUD.md) | Supabase schema + pool + CRUD (+ minimal local pgvector) | Must | 📋 PLANNED | 32 | — | ~2 min | 2026-07-09 |
| 34 | [../slices/SLICE-34-POSTGRES-DENSE-RETRIEVAL.md](../slices/SLICE-34-POSTGRES-DENSE-RETRIEVAL.md) | Supabase dense retrieval (pgvector HNSW) | Must | 📋 PLANNED | 33 | — | ~2 min | 2026-07-09 |
| 35 | [../slices/SLICE-35-POSTGRES-SPARSE-HYBRID.md](../slices/SLICE-35-POSTGRES-SPARSE-HYBRID.md) | Supabase sparse + hybrid RRF (+ Mongo equivalence gate) | Must | 📋 PLANNED | 34 | — | ~2 min | 2026-07-09 |
| 36 | [../slices/SLICE-36-POSTGRES-PREFLIGHT-STATS.md](../slices/SLICE-36-POSTGRES-PREFLIGHT-STATS.md) | Supabase preflight + db-stats + storage mode indicator | Must | 📋 PLANNED | 35 | — | ~2 min | 2026-07-09 |
| 37 | [../slices/SLICE-37-POSTGRES-LOCAL-CLOUD-PARITY.md](../slices/SLICE-37-POSTGRES-LOCAL-CLOUD-PARITY.md) | Supabase local + hosted parity + boot reconciliation | Must | 📋 PLANNED | 36 | — | ~2 min | 2026-07-09 |
| 38 | [../slices/SLICE-38-CUTOVER-ADR-004.md](../slices/SLICE-38-CUTOVER-ADR-004.md) | Quality comparison + ADR-004 + default cutover | Must | 📋 PLANNED | 37 | — | ~2 min | 2026-07-09 |
| 28 | [../slices/SLICE-28-RESULTS-EXPORT.md](../slices/SLICE-28-RESULTS-EXPORT.md) | Results export — CSV/JSONL download (issue #49; @cschanhniem) | Must | 📋 PLANNED | none | [#49](https://github.com/neomatrix369/rag-params-finder/issues/49) | ~3 min | 2026-07-06 |
| 22 | [../slices/SLICE-22-SIE-SCOOTER.md](../slices/SLICE-22-SIE-SCOOTER.md) | SIE Scooter — reranking + SPLADE v3 sparse + `/api/v1/best-config` | Must | 📋 PLANNED | 21, 32, 38 (soft) | — | ~3 min | 2026-07-09 |
| 26 | [../slices/SLICE-26-LOCAL-MONGODB-DOCS.md](../slices/SLICE-26-LOCAL-MONGODB-DOCS.md) | Local MongoDB: smooth path docs + script feedback | Should | 📦 DEFERRED | 25B | — | ~1.5 min | 2026-07-09 |
| 27 | [../slices/SLICE-27-MONGODB-MODE-INDICATOR.md](../slices/SLICE-27-MONGODB-MODE-INDICATOR.md) | MongoDB mode indicator (cloud vs local) | Should | 📦 DEFERRED | 25B | — | ~2 min | 2026-07-09 |
| 19 | [../slices/SLICE-19-STORAGE-QUOTA-GUARD.md](../slices/SLICE-19-STORAGE-QUOTA-GUARD.md) | Storage quota guard (cloud production) | Should | 📦 DEFERRED | none | — | — | 2026-07-09 |
| 16 | [../slices/SLICE-16-PARALLEL-SWEEP-RUNS.md](../slices/SLICE-16-PARALLEL-SWEEP-RUNS.md) | Parallel sweep | Should | 📋 PLANNED | none | — | — | — |
| 11 | [../slices/SLICE-11-SEARCH-EXPLORER.md](../slices/SLICE-11-SEARCH-EXPLORER.md) | Search Explorer enhancements — visualization + query filtering | Could | 📋 PLANNED | none (soft: 30) | — | ~3 min | 2026-07-09 |
| 23 | [../slices/SLICE-23-SIE-BICYCLE.md](../slices/SLICE-23-SIE-BICYCLE.md) | SIE Bicycle — Ollama + Tier 2–3 methods + Evidently AI | Could | 📋 PLANNED | 22 | — | ~3 min | 2026-07-09 |
| 10 | [../slices/SLICE-10-RUN-RECOVERY.md](../slices/SLICE-10-RUN-RECOVERY.md) | Run recovery | Could | 🔨 PARTIAL | none | — | — | 2026-07-09 |
| 30 | [../slices/SLICE-30-SEARCH-EXPLORER-UX.md](../slices/SLICE-30-SEARCH-EXPLORER-UX.md) | Search Explorer UX fixes — tab latency, zero-score, BM25 labels, VDB card | Could | 📋 PLANNED | none | — | ~2 min | 2026-07-07 |
| 31 | [../slices/SLICE-31-EXPERIMENT-LIST-FILTER.md](../slices/SLICE-31-EXPERIMENT-LIST-FILTER.md) | Experiment list filter — status dropdown + name/ID search | Should | 📋 PLANNED | none | — | ~2 min | 2026-07-07 |
| 39 | [../slices/SLICE-39-DEMO-READY-DASHBOARD-POLISH.md](../slices/SLICE-39-DEMO-READY-DASHBOARD-POLISH.md) | Demo-ready dashboard polish — list-to-detail visual journey | Should | 📋 PLANNED | none | — | ~3 min | 2026-07-18 |

**Execution order**: 21 → 25 → 25B → 29 (done) → **39** *(≤2 h demo interrupt)* → **32 → 33 → 34 → 35 → 36 → 37 → 38** → **22** → 28*(external)* → 31 → 30 → 16 → 11 → 23 → 10.
*Deferred Mongo QoL: 26, 19 — re-scope after cutover. Slice 27 scope absorbed into 36 as a storage-mode indicator.*

**PCTO escape hatch (Slice 22):** If slices 32–36 slip **>2 days** past the PCTO deadline, start Slice 22 on Mongo via StorageBackend Protocol only (hard dep: 32 merged); budget ~30 min to re-port history queries when Slice 38 lands; retest on Supabase backend after 38.

**CI:** Mandatory Postgres regression job from Slice 33 merge onward; cutover gates in PRD (latency ≤2× p99, hybrid drift ≤5%, rollback >30 min).

**Docs:** Per-slice user/dev guide gates in [PRD §Documentation matrix](PRD-supabase-pgvector-migration.md#documentation-matrix); `/sync-docs` at Slices **37** and **38**.

### Infrastructure slices (complete — tracked in [docs/slices/PROGRESS.md](../slices/PROGRESS.md))

| # | Name | Status | Notes |
|---|------|--------|-------|
| 14 | Docker Compose | ✅ COMPLETE | `./start-services.sh` |
| 18 | Unified retriever config | ✅ COMPLETE | `retrievers` list format |
| 20 | Toolchain hardening | ✅ COMPLETE | quality-gates, gitleaks, dependabot |
| 24 | Port standardisation | ✅ COMPLETE | frontend :5374, SIE :8720 |

## Deferred Work (no slice yet — see GAP_ANALYSIS)

| Area | Blocker | Target |
|------|---------|--------|
| Vite 6 → 8 + `@vitejs/plugin-react` upgrade | Peer dep conflict (#43 closed) | Future toolchain slice |
| ESLint 8 → 9 + react-refresh 0.5 + security 4.0 | Config migration required (#41, #42 closed) | Future toolchain slice |
| eslint-plugin-react-hooks 7 | React 19 hook rules fail CI (#26 closed) | After SearchExplorerScreen refactor |
| sentence-transformers v4+ | mypy CrossEncoder mismatch (#40 closed) | Dedicated ML stack slice |
| Mongo adapter removal | Dual-backend kept through Slice 38 | Post-cutover cleanup (Won't this cycle) |

## Supporting Artifacts

| File | Status | Read time | Last Updated |
|------|--------|-----------|--------------|
| PRD-supabase-pgvector-migration.md | added | ~3 min | 2026-07-09 |
| GAP_ANALYSIS.md | updated | ~2 min | 2026-07-09 |
| DECISIONS.md | updated | ~2 min | 2026-07-09 |
| HANDOFF.md | updated | ~2 min | 2026-07-09 |
| [../slices/PROGRESS.md](../slices/PROGRESS.md) | merged SSOT | ~2 min | 2026-07-09 |
| interview_summary.md | reconstructed | ~1 min | 2026-07-02 |
| gate-evidence/ | backfilled (21, 25, 25B, 29) | — | 2026-07-09 |

## Slice Token Summary

Updated as each slice reaches Gate Status PASSED.

| Slice | Plan tkns in/out | Exec tkns in/out | Turns | Context pressure |
|-------|-----------------|-----------------|-------|-----------------|
| 21 — SIE Skateboard | — / — | — / — | — | — |
| 25 — Atlas Local | — / — | — / — | — | — |
| 25B — Atlas Switching | — / — | — / — | — | — |
| 32–38 — Supabase migration | — / — | — / — | — | — |
| 22 — SIE Scooter | — / — | — / — | — | — |
| 23 — SIE Bicycle | — / — | — / — | — | — |

## Reviews

| Date | Reviewer | Verdict | Notes |
|---|---|---|---|
| 2026-07-09 | nw-solution-architect-reviewer (iter 1) | Conditionally approved | AC coupling, equivalence gates, Slice 22 Protocol dep — edits applied same day |
| 2026-07-09 | local (data/platform/PO) | Partial | Usage limit — merged into PRD/TRAIL/33/36/37 |
| 2026-07-09 | nw-product-owner-reviewer (iter 2) | **APPROVED** | DoR 9/9; escape hatch, soft dep 22→38, Slice 27→36, CI note verified |
| 2026-07-09 | nw-data-engineer-reviewer (iter 2) | **APPROVED** | 8.3/10; 7 non-blocking gaps (CI schedule, cost row, boot-recon GWT, minimal-docker trade-off) |
| 2026-07-09 | nw-solution-architect-reviewer (iter 2) | **APPROVED** | Conditional items verified: behavioral ACs, storage seam, experiment_id contract, SPLADE fallback; ready for Slice 32 |
| 2026-07-09 | nw-platform-architect-reviewer (iter 2) | **Conditionally approved** | Cutover gates + mandatory Postgres CI — applied to PRD/33/38 |
| 2026-07-09 | nw-solution-architect-reviewer (iter 3) | **APPROVED** | Gap-bridge uncommitted delta: TRAIL↔PROGRESS↔specs aligned; Slice 22 dep 32; SLICE-11 created |
| 2026-07-09 | nw-documentarist-reviewer (iter 3) | **APPROVED** | Gap-bridge docs; soft-dep 30 note applied; latency handoff in SLICE-11 |
