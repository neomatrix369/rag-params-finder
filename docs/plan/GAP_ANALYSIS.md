# Gap Analysis
> ~2 min read · **Updated 2026-07-29** after Slice 22 `/nw-execute` + `/sync-docs` · prior: Slice 22 plan refresh 2026-07-29 · Gap bridge 2026-07-09

Canonical build status: [docs/plan/slices/PROGRESS.md](../plan/slices/PROGRESS.md) · Migration PRD: [PRD-supabase-pgvector-migration.md](PRD-supabase-pgvector-migration.md) · Active Must next: [SLICE-28](slices/02-dashboard/SLICE-28-RESULTS-EXPORT.md) (external)

---

## Closed Gaps (since 2026-06-27 snapshot)

| Area | Was | Now | Closed by |
|------|-----|-----|-----------|
| SIE inference backend | Not installed | BGE-M3, Stella-v5 via `sie_embedder.py` + `embedder_factory.py` | Slice 21 ✅ |
| Caller-supplied corpus | PDF only | `corpus: list[str]` on `SweepRequest` | Slice 21 ✅ |
| Aim experiment tracking | None | `aim_logger.py` (no-op on failure) | Slice 21 ✅ |
| `POST /api/v1/sweep` | Missing | Live in `server/api/sweep.py` | Slice 21 ✅ |
| SIE health check | MongoDB only | `/health` includes SIE status | Slice 21 ✅ |
| Atlas M0 storage ceiling (local dev) | Blocker | `./start-services.sh --mongodb-local` + auto indexes | Slice 25/25B ✅ |
| CI action upgrades (repo-lint, gitleaks) | Mixed v4/v2 | All jobs on checkout/setup-python v6; gitleaks v3 | PRs #36–#39 ✅ |
| Migration decision | ADR-003 locked Atlas | Team approved Supabase/pgvector + dual-backend | PRD 2026-07-09 |
| Slice 11 spec missing | TRAIL linked 404 | `SLICE-11-SEARCH-EXPLORER.md` created; scope bounded vs 28/30 | Gap bridge 2026-07-09 |
| Plan ↔ spec drift (10, 19, 26, 27) | TRAIL vs spec status mismatch | TRAIL + specs synced; Before-Checks on deferred slices | Gap bridge 2026-07-09 |
| Bayesian search (simple functional) | Slice 41A — numeric axes, optuna, trial log | Fully implemented + all ACs verified | Slice 41A ✅ 2026-07-23 |
| Docker build optimisation | Multi-stage builds, cache mounts, nginx runtime, CI job | Fully implemented (server + frontend Dockerfiles) | Slice 42 ✅ 2026-07-25 |
| Project hygiene + nightly CI | Nightly T4 jobs, idempotent hooks, Chalk attestation, BACKEND_CHANGED | All merged to main (PRs #103–106) | Maintenance batch 2026-07-24 |
| gate-evidence stubs (historical slices 1–9, 42) | All PASSED slices should have gate-evidence JSON | Stubs created; 42 now has real evidence, 1–9 inferred | plan-health-check AUTO-FIX 2026-07-25 |
| Dual-backend storage Protocol | Mongo-only modules | `StorageBackend` + `RetrieverBackend` ports; Mongo + Postgres adapters on main | Slices 32–38 ✅ (formal 32B gate debt parallel) |
| Dense/sparse/hybrid on Postgres | Atlas only | pgvector HNSW + tsvector + RRF | Slices 34–35 ✅ |
| Index preflight / db-stats on Postgres | Atlas Admin only | Postgres catalog preflight + four-value `storage_mode` | Slice 36 ✅ |
| Local + cloud Postgres DX | Atlas Local only | `--postgres-local` / `--postgres-cloud` + config↔server 422 | Slice 37 ✅ |
| ADR-004 + quality comparison | ADR-003 only | ADR-004 Accepted; local comparison VERIFIED; **no default flip** (#130) | Slice 38 ✅ |
| User/dev Postgres doc footprint | Mongo guides only | `postgres-setup.md` + operator parity | Slices 37–38 + sync-docs ✅ |
| Best-config lookup | Stub placeholder | `GET /api/v1/best-config?task=` reads persisted Tier-1 history via StorageBackend | Slice 22 ✅ |
| SIE reranking | Voyage + CrossEncoder only | `provider: sie` + `bge-reranker` via `SIEClient.score()` | Slice 22 ✅ |
| SPLADE v3 sparse Tier-1 assert | Registry + index only | Sparse-only `bm25` Tier-1 path reuses `splade-v3` (no registry re-add) | Slice 22 ✅ |

---

## Remaining Capability Gaps

| Area | PCTO / Roadmap Requirement | What Exists | Gap | Severity | Target |
|------|---------------------------|-------------|-----|----------|--------|
| Results export | CSV/JSONL download | JSON via `/results` and `/explore` only | Export endpoint + dashboard button | **Must** (#49) | Slice 28 |
| Local MongoDB UX docs | Smooth onboarding | Unified `mongodb-setup.md` | **📦 DEFERRED** | Should | was 26 |
| Storage quota guard (Atlas) | Cloud production safety | Boot reconciliation only | **📦 DEFERRED** — Postgres stats in 36 | Should | was 19 |
| Ollama + Tier 2–3 | HyDE, Multi-Query, etc. | None | Full retrieval tier expansion | Could | Slice 23 |
| Evidently AI monitoring | Drift alerts | None | Integration | Could | Slice 23 |
| MCP server | `get_rag_config` tool | None | **Won't this cycle** — use best-config HTTP | Won't | — |
| Formal Protocol gate closure | Tracker COMPLETE for 32/32C/32B/33 | Protocol **IMPLEMENTED** on main; 38 ✅ | Coverage/mutation/nw-review close-out | Should (parallel) | 32B chain |
| Live SIE smoke (Slice 22 After-Check) | Manual sweep → best-config on real gateway | Unit/mocked path **VERIFIED** | Optional operator probe | Could | post-merge |

---

## Toolchain / Dependabot Gaps (deferred — no active slice)

| Upgrade | Status | Blocker | Action taken |
|---------|--------|---------|--------------|
| eslint-plugin-react-hooks 5→7 | Closed (#26) | New React 19 lint rules in SearchExplorerScreen | Defer until screen refactor |
| eslint-plugin-react-refresh 0.4→0.5 | Closed (#41) | npm ERESOLVE vs eslint@8 | Defer until ESLint 9 slice |
| eslint-plugin-security 1.7→4.0 | Closed (#42) | `plugin:security/recommended` breaking change | Defer until ESLint config migration |
| vite 6→8 | Closed (#43) | `@vitejs/plugin-react@4.x` peer range | Defer intentional toolchain slice |
| sentence-transformers `<4`→`<6` | Closed (#40) | mypy CrossEncoder type mismatch | Defer ML stack slice |

---

## What Is Already Sufficient (No Gap)

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI + `/experiments` API | ✅ | Unchanged; `/api/v1` is additive |
| MongoDB Atlas + Local | ✅ | Remains via dual-backend until post-38 cleanup |
| Voyage AI embeddings + reranking | ✅ | Numeric baseline preserved |
| Dense/sparse/hybrid retrieval (Tier 1) on Mongo | ✅ | Atlas vector + FTS |
| Orchestrator pipeline | ✅ | Provider dispatch via factory |
| Docker Compose stack | ✅ | Prod + dev HMR; Postgres profile in 37 |
| Docker build layering + CI validation | ✅ | Multi-stage + BuildKit cache + nginx runtime; Slice 42 ✅ |
| CI / quality gates | ✅ | `./scripts/ci/quality-gates.sh` |
| Chunkers | ✅ | PRs #47/#48 |
| Parallel sweep | ✅ | Slice 16 COMPLETE |
| Dense/sparse/hybrid on Postgres | ✅ | Slices 34–35 |
| SIE Scooter (rerank + best-config + SPLADE assert) | ✅ | Slice 22 COMPLETE |

---

## Divergence Check (Spec ↔ Tests ↔ Code)

| Area | Spec says | Code does | Gap | Action |
|------|-----------|-----------|-----|--------|
| Storage backend | Dual Protocol; operator-selected engine (#130 no default flip) | Protocol + Mongo + Postgres adapters on main | **No** (formal 32B debt parallel) | — |
| best-config | Returns recommendation from history | `GET /api/v1/best-config?task=` → highest score / 404 | **No** | — |
| SPLADE sparse sweep | End-to-end sparse path assert | Sparse-only Tier-1 `bm25` + existing registry | **No** (narrow Tier-1 assert) | — |
| SIE reranking | BGE-reranker scores | `reranker.py` → `score_documents_sie` | **No** | — |
| Export | CSV/JSONL download | Not implemented | **Yes** | Slice 28 |
| All Slice 21 items | SIE + sweep + Aim | Implemented + tested | **No** | — |

**Result**: Soft cutover (38) ✅. PCTO Slice **22** ✅ COMPLETE (**IMPLEMENTED**; unit **VERIFIED**). Critical remaining Must: Slice **28** export. Formal 32B gate debt stays parallel.
