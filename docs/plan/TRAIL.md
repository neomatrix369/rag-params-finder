# Trail
> ~3 min read (this doc) · [GAP_ANALYSIS](GAP_ANALYSIS.md) ~2 min · [DECISIONS](DECISIONS.md) ~2 min · [HANDOFF](HANDOFF.md) ~1 min · [PROGRESS](../slices/PROGRESS.md) ~2 min

## Original Material

- **PCTO Spec** (`docs/PCTO-rag-params-finder-2026-06-27.md`): Add SIE as primary open-source inference backend (encode + score + extract), caller-supplied corpus (`corpus: list[str]` field on `SweepRequest`), Aim for experiment tracking, and two new API endpoints (`POST /api/v1/sweep`, `GET /api/v1/best-config`)
- **Codebase** (v0.11.0, 20+ slices complete): Mature Voyage AI + local sentence-transformers RAG sweep pipeline, MongoDB Atlas, FastAPI, React dashboard, Docker, full CI toolchain
- **Constraints**: Hackathon deadline — Slice 21 targets Days 1–5; Voyage AI stays as numeric baseline (not replaced); all PCTO changes are additive (no rewrites)

Routing: Brownfield + Growing Requirement (Flow D) · Chosen: 2026-07-02 · Source: health-check-inferred

Model split — Planning: claude-opus-4-8 · Execution: claude-sonnet-4-6

## Flow

**Brownfield + Growing Requirement** (Flow D) — mature codebase, PCTO is the new feature extension spec. All changes compose on top of existing pipeline.

## Slices

Each PCTO slice lives in its own file below. Existing planned slices (10, 16, 19) have spec files in `docs/slices/` — referenced here, not duplicated.

| # | File | Name | MoSCoW | Status | Depends on | Issue | Read time | Last Updated |
|---|------|------|--------|--------|------------|-------|-----------|--------------|
| 21 | [../slices/SLICE-21-SIE-SKATEBOARD.md](../slices/SLICE-21-SIE-SKATEBOARD.md) | SIE Skateboard — embeddings + Aim + `/api/v1/sweep` | Must | ✅ PASSED | none | — | ~4 min | 2026-06-29 |
| 25 | [../slices/SLICE-25-ATLAS-LOCAL.md](../slices/SLICE-25-ATLAS-LOCAL.md) | Atlas Local Dev Mode — `mongodb-atlas-local` as opt-in backend | Should | ✅ PASSED | 21 | — | ~2 min | 2026-06-29 |
| 25B | [../slices/SLICE-25B-ATLAS-SWITCHING.md](../slices/SLICE-25B-ATLAS-SWITCHING.md) | Atlas Backend Switching — single-flag cloud ↔ local switching | Should | ✅ PASSED | 25 | — | ~2 min | 2026-06-29 |
| 28 | [../slices/SLICE-28-RESULTS-EXPORT.md](../slices/SLICE-28-RESULTS-EXPORT.md) | Results export — CSV/JSONL download (issue #49) | Must | 📋 PLANNED | none | [#49](https://github.com/neomatrix369/rag-params-finder/issues/49) | ~3 min | 2026-07-06 |
| 22 | [../slices/SLICE-22-SIE-SCOOTER.md](../slices/SLICE-22-SIE-SCOOTER.md) | SIE Scooter — reranking + SPLADE v3 sparse + `/api/v1/best-config` | Should | 📋 PLANNED | 21 | — | ~3 min | 2026-06-27 |
| 26 | [../slices/SLICE-26-LOCAL-MONGODB-DOCS.md](../slices/SLICE-26-LOCAL-MONGODB-DOCS.md) | Local MongoDB: smooth path docs + script feedback | Should | 📋 PLANNED | 25B | — | ~1.5 min | 2026-06-29 |
| 27 | [../slices/SLICE-27-MONGODB-MODE-INDICATOR.md](../slices/SLICE-27-MONGODB-MODE-INDICATOR.md) | MongoDB mode indicator (cloud vs local) | Should | 📋 PLANNED | 25B | — | ~2 min | 2026-06-29 |
| 19 | [../slices/SLICE-19-STORAGE-QUOTA-GUARD.md](../slices/SLICE-19-STORAGE-QUOTA-GUARD.md) | Storage quota guard (cloud production) | Should | 📋 PLANNED | none | — | — | — |
| 16 | [../slices/SLICE-16-PARALLEL-SWEEP-RUNS.md](../slices/SLICE-16-PARALLEL-SWEEP-RUNS.md) | Parallel sweep | Should | 📋 PLANNED | none | — | — | — |
| 11 | [../slices/SLICE-11-SEARCH-EXPLORER.md](../slices/SLICE-11-SEARCH-EXPLORER.md) | Search Explorer enhancements — visualization + query filtering | Could | 📋 PLANNED | none | — | ~30 min | 2026-07-05 |
| 23 | [../slices/SLICE-23-SIE-BICYCLE.md](../slices/SLICE-23-SIE-BICYCLE.md) | SIE Bicycle — Ollama + Tier 2–3 methods + Evidently AI | Could | 📋 PLANNED | 22 | — | ~3 min | 2026-06-27 |
| 10 | [../slices/SLICE-10-RUN-RECOVERY.md](../slices/SLICE-10-RUN-RECOVERY.md) | Run recovery | Could | 📋 PLANNED | none | — | — | — |

**Execution order**: 21 → 25 → 25B (done) → **28** → **22** → 26 → 27 → 19 → 16 → 11 → 23 → 10 *(active work: 22 — Slice 28 not starting immediately)*

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

## Supporting Artifacts

| File | Status | Read time | Last Updated |
|------|--------|-----------|--------------|
| GAP_ANALYSIS.md | updated | ~2 min | 2026-07-02 |
| DECISIONS.md | updated | ~2 min | 2026-07-06 |
| HANDOFF.md | updated | ~2 min | 2026-07-06 |
| [../slices/PROGRESS.md](../slices/PROGRESS.md) | merged SSOT | ~2 min | 2026-07-06 |
| interview_summary.md | reconstructed | ~1 min | 2026-07-02 |
| gate-evidence/ | backfilled (21, 25, 25B) | — | 2026-07-02 |

## Slice Token Summary

Updated as each slice reaches Gate Status PASSED.

| Slice | Plan tkns in/out | Exec tkns in/out | Turns | Context pressure |
|-------|-----------------|-----------------|-------|-----------------|
| 21 — SIE Skateboard | — / — | — / — | — | — |
| 25 — Atlas Local | — / — | — / — | — | — |
| 25B — Atlas Switching | — / — | — / — | — | — |
| 22 — SIE Scooter | — / — | — / — | — | — |
| 23 — SIE Bicycle | — / — | — / — | — | — |
