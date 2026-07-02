# Decisions
> ~2 min read

| # | Date | Slice | Decision | Why | Rejected Alternative |
|---|------|-------|----------|-----|----------------------|
| 1 | 2026-06-27 | — | Single integrated flow-planner session (not two sequential steps) | Avoids duplicate work and plan divergence; PCTO IS the spec input for the upgrade | Run integrate-PCTO first, then separately run flow-planner |
| 2 | 2026-06-27 | — | PCTO slices numbered 21–23 in existing project scheme | Preserves continuity with 20-slice history in PROGRESS.md | Start new numbering from 1 in a separate PCTO plan file |
| 3 | 2026-06-27 | — | Slice 21 before Slice 19 | Hackathon deadline; PCTO Slice 1 (Days 1–5) is highest-value; Atlas M0 workaround covers interim risk | Slice 19 first — correct long-term but delays hackathon deliverable |
| 4 | 2026-06-27 | 21 | `sie_embedder.py` as new file mirroring `local_embedder.py` interface | Composability — orchestrator dispatches by provider string; each provider is an independent module | Modify `embedder.py` directly — breaks single-responsibility |
| 5 | 2026-06-27 | 21 | `SweepRequest` accepts caller-supplied `corpus: list[str]`; falls back to topic string when empty | No external dependencies or API keys required; simpler, fully testable, composable | Inline corpus fetching — hidden I/O in the pipeline, harder to test |
| 6 | 2026-06-27 | 21 | `aim_logger.py` as thin wrapper (not direct `aim` calls) | Replaceable — PCTO risk table names MLflow as backup; wrapper isolates the dependency | Direct `aim.Run()` calls in orchestrator — hard to swap |
| 7 | 2026-06-27 | 21 | Voyage AI stays as numeric baseline (not removed) | PCTO spec: "voyage-3.5 stays as the numeric baseline. Every sweep run compares at least one SIE model against it." | Remove Voyage to simplify — contradicts PCTO spec |
| 8 | 2026-06-27 | — | MCP server explicitly deferred — **Won't have this cycle** | No immediate hackathon value; adds deployment complexity (Alpic.ai account, MCP protocol) without improving sweep quality. `GET /api/v1/best-config` is the clean integration point if ever needed. | Embed MCP in service (Slice 22) — couples transport concern to sweep logic; harder to reuse |
| 9 | 2026-06-27 | — | If MCP is ever built, it must be a standalone reusable skill or global tool | MCP is a transport layer, not a domain concern. Embedding it in `rag-params-finder` would prevent reuse across other services. A standalone skill can wrap any `best-config`-compatible endpoint. | Inline `mcp_server.py` in this service — tight coupling, not reusable |
| 10 | 2026-06-27 | all | When a new RAG dimension (DB/embedder/chunker/retriever) is introduced, apply the **simplest design pattern** that fits the routing/dispatch problem. Factory function preferred over Protocol/ABC unless a contract must be enforced across teams or packages. Upgrade only when complexity demands it. Applied to Slice 21: `embedder_factory.py` (factory fn, not Protocol class). | YAGNI + Simple Design — pattern overhead is a cost; ceremony without runtime benefit is waste. | Default to Protocol/facade for every new provider — adds ~40 lines with zero runtime gain at current scale |
| 11 | 2026-07-01 | 28 | Dedicated Slice 28 for results export (issue #49) instead of waiting for bundled Slice 11 | Export is a shippable vertical slice with clear acceptance criteria; unblocks external contributors and stakeholder sharing | Fold into Slice 11 Search Explorer bundle — delays delivery behind visualization work |
| 12 | 2026-07-01 | 28 | Export rows sourced from `analyze_results()` `detailed_results`, not raw Mongo `results` docs | Scores/ranks match Search Explorer; single normalization path | Duplicate CSV logic in route from raw docs — drift risk vs dashboard |
| 13 | 2026-07-01 | 28 | Default CSV omits `chunk_text`; JSONL may include it | Keeps CSV small and avoids dumping full chunk bodies into spreadsheets | Always include chunk_text — noisy for stakeholders, large files |
| 14 | 2026-07-02 | health-check | Gap 2: routing fingerprint | Appended `Routing: Brownfield + Growing Requirement (Flow D)` to TRAIL.md | AUTO-FIXED |
| 15 | 2026-07-02 | health-check | Gap 4: Depends on column | Added to TRAIL.md Slices table; existing rows defaulted per dependency graph | AUTO-FIXED |
| 16 | 2026-07-02 | health-check | Gap 5: gate-evidence stubs | Backfilled slice-21.json, slice-25.json, slice-25B.json | AUTO-FIXED |
| 17 | 2026-07-02 | health-check | Gap 1: interview_summary.md | Reconstructed from TRAIL + PROGRESS + PCTO spec | AUTO-FIXED |
| 18 | 2026-07-02 | health-check | Gap 3: model split | Defaults: Planning claude-opus-4-8 · Execution claude-sonnet-4-6 | AUTO-FIXED |
| 19 | 2026-07-02 | — | Created docs/plan/PROGRESS.md | plan-modifier requires plan-level tracker separate from docs/slices/PROGRESS.md | **Superseded by #23** |
| 23 | 2026-07-02 | — | Merge docs/plan/PROGRESS.md into docs/slices/PROGRESS.md | Single SSOT — AGENTS.md/CLAUDE.md already point to slices/PROGRESS; duplicate caused drift | Delete docs/plan/PROGRESS.md |
| 20 | 2026-07-02 | — | Dependabot #26–#43 triage recorded | 4 merged (#36–#39 CI actions), 5 closed (breaking toolchain bumps) | Execute when stale |
| 21 | 2026-07-02 | — | Deferred toolchain upgrades documented in TRAIL + GAP_ANALYSIS | Vite 8, ESLint 9, react-hooks 7, ST v4+ need dedicated slices — not blind Dependabot merges | Close-and-document pattern |
| 22 | 2026-07-02 | — | GAP_ANALYSIS refresh cadence | Update on slice PASS or quarterly; stale analysis misleads continuation sessions | Manual until automated |
