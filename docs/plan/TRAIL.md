# Trail
> ~3 min read (this doc) · [GAP_ANALYSIS](GAP_ANALYSIS.md) ~2 min · [DECISIONS](DECISIONS.md) ~2 min · [HANDOFF](HANDOFF.md) ~1 min

## Original Material

- **PCTO Spec** (`docs/PCTO-rag-params-finder-2026-06-27.md`): Add SIE as primary open-source inference backend (encode + score + extract), Tavily as live corpus builder, Aim for experiment tracking, and two new API endpoints (`POST /api/v1/sweep`, `GET /api/v1/best-config`)
- **Codebase** (v0.11.0, 20+ slices complete): Mature Voyage AI + local sentence-transformers RAG sweep pipeline, MongoDB Atlas, FastAPI, React dashboard, Docker, full CI toolchain
- **Constraints**: Hackathon deadline — Slice 21 targets Days 1–5; Voyage AI stays as numeric baseline (not replaced); all PCTO changes are additive (no rewrites)

## Flow

**Brownfield + Growing Requirement** (Flow D) — mature codebase, PCTO is the new feature extension spec. All changes compose on top of existing pipeline.

## Slices

Each PCTO slice lives in its own file below. Existing planned slices (10, 16, 19) have spec files in `docs/slices/` — referenced here, not duplicated.

| # | File | Name | MoSCoW | Status | Issue | Read time | Last Updated |
|---|------|------|--------|--------|-------|-----------|--------------|
| 21 | [slice-21-sie-skateboard.md](slice-21-sie-skateboard.md) | SIE Skateboard — embeddings + Tavily + Aim + `/api/v1/sweep` | Must | pending | — | ~4 min | 2026-06-27 |
| 22 | [slice-22-sie-scooter.md](slice-22-sie-scooter.md) | SIE Scooter — reranking + `/api/v1/best-config` + MCP stub | Should | pending | — | ~3 min | 2026-06-27 |
| 23 | [slice-23-sie-bicycle.md](slice-23-sie-bicycle.md) | SIE Bicycle — Ollama + Tier 2–3 methods + Evidently AI | Could | pending | — | ~3 min | 2026-06-27 |
| 19 | [../slices/SLICE-19-STORAGE-QUOTA-GUARD.md](../slices/SLICE-19-STORAGE-QUOTA-GUARD.md) | Storage quota guard | Should | pending | — | — | — |
| 16 | [../slices/SLICE-16-PARALLEL-SWEEP-RUNS.md](../slices/SLICE-16-PARALLEL-SWEEP-RUNS.md) | Parallel sweep | Should | pending | — | — | — |
| 10 | [../slices/SLICE-10-RUN-RECOVERY.md](../slices/SLICE-10-RUN-RECOVERY.md) | Run recovery | Could | pending | — | — | — |

**Execution order**: 21 → 19 (can overlap) → 22 → 16 → 23 → 10

## Supporting Artifacts

| File | Status | Read time | Last Updated |
|------|--------|-----------|--------------|
| GAP_ANALYSIS.md | written | ~2 min | 2026-06-27 |
| DECISIONS.md | written | ~2 min | 2026-06-27 |
| HANDOFF.md | pending | — | — |

## Slice Token Summary

Updated as each slice reaches Gate Status PASSED.

| Slice | Plan tkns in/out | Exec tkns in/out | Turns | Context pressure |
|-------|-----------------|-----------------|-------|-----------------|
| 21 — SIE Skateboard | — / — | — / — | — | — |
| 22 — SIE Scooter | — / — | — / — | — | — |
| 23 — SIE Bicycle | — / — | — / — | — | — |
