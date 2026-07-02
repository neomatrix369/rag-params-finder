# Interview Summary
> Reconstructed: true | Source: health-check | Date: 2026-07-02

## Scenario

**Brownfield + Growing Requirement (Flow D)** — mature RAG sweep codebase (v0.11.0, 20+ slices) extended by PCTO spec for SIE inference, Aim logging, and `/api/v1` sweep APIs.

## Goals

1. Add SIE as primary open-source embedding backend (BGE-M3, Stella-v5, SPLADE-v3) without removing Voyage baseline.
2. Ship hackathon-critical API surface: `POST /api/v1/sweep`, caller-supplied `corpus`, Aim experiment tracking.
3. Improve local dev ergonomics (Atlas Local, backend switching) to escape M0 storage ceiling.
4. Continue incremental slices (export, mode indicator, SIE Scooter) post-hackathon.

## Constraints

- All PCTO changes are **additive** — no rewrites of orchestrator pipeline.
- Voyage AI stays as numeric baseline for sweep comparisons.
- MCP server explicitly **Won't** this cycle; `GET /api/v1/best-config` is the integration point.
- Major toolchain bumps (Vite 8, ESLint 9, sentence-transformers v4+) deferred — require dedicated slices.
- Factory-function dispatch pattern for new providers (`embedder_factory.py`), not Protocol ceremony.

## Success Criteria

- Slice 21 skateboard: SIE encode + sweep endpoint + Aim logging + quality gates green.
- Local dev: `./start-services.sh --local` with auto-provisioned search indexes.
- Plan artifacts stay synced with `docs/slices/PROGRESS.md` (canonical slice status).

## Out of Scope (confirmed)

- Ollama + Tier 2–3 retrieval (Slice 23 — Could, post-hackathon).
- Parallel sweep execution (Slice 16 — Should, not urgent).
- Kimchi provider (branch #13 — separate hackathon track).
