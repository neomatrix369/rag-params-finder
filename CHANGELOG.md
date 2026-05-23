# Changelog

All notable changes to **rag-params-finder** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.2.0] - 2026-05-23

### Added

#### 🎯 Weighted Averaging (Query-Level Fairness)
- **New metric**: `query_avg_score` — weighted per-query average where each query contributes equally
- **Configurable tiebreaker**: `TIEBREAKER_METRIC` env var (`query_avg` default, `chunk_avg` legacy)
- **Why it's better**: Prevents queries with many results from dominating the average score
- **Example**: Query 1 returns 5 high-scoring chunks, Query 2 returns 3 low-scoring chunks
  - Old (chunk avg): Query 1 dominates (5/8 = 62.5% weight) → 87% avg
  - New (query avg): Each query weighted equally (50% each) → 84.5% avg
- **Dashboard**: Both metrics displayed with visual distinction (✓ for query avg)

#### 🏆 Tiebreaker Explanation UI
When multiple configs achieve the same max score (e.g., all at 100%), the dashboard now shows:

- 🟠 **Amber alert badge**: "N configs tied at 100%"
- ℹ️ **Explanation panel**: Tiebreaker criteria (query avg → chunk size → overlap)
- ⭐ **#1 badge**: "Best by tiebreaker" (yellow)
- 🔀 **#2, #3 badges**: "Tied" (amber)
- **Contextual annotations** on each card explaining WHY it's ranked that way
  - Example: "✓ Ranked #1 by: smallest chunk size (512 vs 1024) → faster processing + less storage"
- **Dynamic section description**: Updates text when ties exist

#### 🔗 Detailed Results ↔ Hyperparameters Mapping
The **Detailed Results tab** now shows:

- **Chunk size/overlap badges** (purple) — map individual results back to configs
- **Query text** — see which query each result answered
- **Explanatory header**: "Individual chunk results — See Hyperparameters tab for aggregated config performance"
- **Click to expand** long chunk text

#### 📊 Collapsible Sweep Dimensions Panel
New collapsible section at the top of Hyperparameters tab showing:

- Unique values for: embedding models, chunking methods, chunk sizes, overlaps, retrievers
- **Cartesian product calculation**: "1 model × 5 methods × 3 sizes × 2 overlaps × 4 retrievers = 120 configurations"
- Collapsed by default to reduce clutter

### Changed

- **Backend sorting**: Now uses 4-level sort (max_score DESC, query_avg_score DESC, chunk_size ASC, overlap ASC)
- **Config ranking**: Uses weighted `query_avg_score` by default instead of unweighted `avg_score`
- **Dashboard tabs**: Hyperparameters and Detailed Results tabs now have clear explanatory headers

### Fixed

- Confusing UI when multiple configs achieved the same max score (no explanation why one was "best")
- Detailed Results tab didn't show chunk size/overlap → couldn't map results back to configs
- Missing query text in Detailed Results → couldn't tell which query each result answered

---

## [0.1.0] - 2026-05-05

### Added

- Initial release with MongoDB Atlas + Voyage AI support
- 5 chunking methods: fixed, recursive, token, sentence, semantic
- 4 retrieval methods: dense, sparse, hybrid, cross-encoder (local) / reranker (Voyage)
- React dashboard with experiments list and detail views
- CLI for experiment submission and control (pause, resume, cancel, delete)
- Search index preflight checks with Atlas storage quota guards
- Unified retriever configuration format
- Startup reconciliation for interrupted experiments

---

## [0.0.1] - 2026-04-15

### Added

- Project skeleton and initial architecture
- MongoDB Atlas vector search integration
- Basic experiment orchestration pipeline
- CLI submission framework

---

[Unreleased]: https://github.com/youruser/rag-params-finder/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/youruser/rag-params-finder/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/youruser/rag-params-finder/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/youruser/rag-params-finder/releases/tag/v0.0.1
