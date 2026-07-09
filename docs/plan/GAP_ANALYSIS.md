# Gap Analysis
> ~2 min read · **Updated 2026-07-09** after Supabase/pgvector migration PRD integration

Canonical build status: [docs/slices/PROGRESS.md](../slices/PROGRESS.md) · Migration PRD: [PRD-supabase-pgvector-migration.md](PRD-supabase-pgvector-migration.md)

---

## Closed Gaps (since 2026-06-27 snapshot)

| Area | Was | Now | Closed by |
|------|-----|-----|-----------|
| SIE inference backend | Not installed | BGE-M3, Stella-v5 via `sie_embedder.py` + `embedder_factory.py` | Slice 21 ✅ |
| Caller-supplied corpus | PDF only | `corpus: list[str]` on `SweepRequest` | Slice 21 ✅ |
| Aim experiment tracking | None | `aim_logger.py` (no-op on failure) | Slice 21 ✅ |
| `POST /api/v1/sweep` | Missing | Live in `server/api/sweep.py` | Slice 21 ✅ |
| SIE health check | MongoDB only | `/health` includes SIE status | Slice 21 ✅ |
| Atlas M0 storage ceiling (local dev) | Blocker | `./start-services.sh --local` + auto indexes | Slice 25/25B ✅ |
| CI action upgrades (repo-lint, gitleaks) | Mixed v4/v2 | All jobs on checkout/setup-python v6; gitleaks v3 | PRs #36–#39 ✅ |
| Migration decision | ADR-003 locked Atlas | Team approved Supabase/pgvector + dual-backend | PRD 2026-07-09 |

---

## Remaining Capability Gaps

| Area | PCTO / Roadmap Requirement | What Exists | Gap | Severity | Target |
|------|---------------------------|-------------|-----|----------|--------|
| Dual-backend storage | Protocol + Mongo/Postgres adapters | Mongo-only modules (`atlas.py`, retriever, indexes) | Extract Protocol; Postgres path | **Critical** (migration) | Slices 32–38 |
| Dense/sparse/hybrid on Postgres | Parity with Atlas retrieval | Atlas `$vectorSearch` / `$search` only | pgvector + tsvector + RRF | **Critical** | 34–35 |
| Index preflight / db-stats on Postgres | HTTP 422 + dashboard panels | Atlas Admin + search index guard | Postgres introspection + `pg_*` sizes | **Critical** | 36 |
| Local + cloud Postgres DX | Mirror Atlas Local story | Atlas Local only | Docker pgvector + Supabase URI | **Critical** | 37 |
| ADR-004 + quality comparison | Supersede ADR-003 | ADR-003 Accepted | Side-by-side + cutover docs | **Critical** | 38 |
| Best-config lookup | `GET /api/v1/best-config?task=...` | Stub returns placeholder message | History query + recommendation logic | **Critical** (PCTO) | Slice 22 *(after 38)* |
| SIE reranking | BGE-reranker via SIE `score` | Voyage + CrossEncoder only | SIE score path in `reranker.py` | Notable | Slice 22 |
| SPLADE v3 sparse sweep | Full sparse retrieval via SIE | Registry + sparse index exist; sweep path incomplete | End-to-end + Postgres sparsevec gate | Notable | 35 + 22 |
| Results export | CSV/JSONL download | JSON via `/results` and `/explore` only | Export endpoint + dashboard button | **Must** (#49) | Slice 28 |
| MongoDB mode visibility | Cloud vs local indicator | URI detection exists | **Absorbed into Slice 36** (storage mode: mongo \| local-postgres \| supabase) | Should | 36 |
| Local MongoDB UX docs | Smooth onboarding | Unified `mongodb-setup.md` | **📦 DEFERRED** | Should | was 26 |
| Storage quota guard (Atlas) | Cloud production safety | Boot reconciliation only | **📦 DEFERRED** — Postgres stats in 36 | Should | was 19 |
| Parallel sweep | `parallelism > 1` | Sequential `BackgroundTasks` | Bounded concurrency | Should | Slice 16 |
| Ollama + Tier 2–3 | HyDE, Multi-Query, etc. | None | Full retrieval tier expansion | Could | Slice 23 |
| Evidently AI monitoring | Drift alerts | None | Integration | Could | Slice 23 |
| MCP server | `get_rag_config` tool | None | **Won't this cycle** — use best-config HTTP | Won't | — |

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
| CI / quality gates | ✅ | `./scripts/quality-gates.sh` |
| Chunkers | ✅ | PRs #47/#48 |

---

## Divergence Check (Spec ↔ Tests ↔ Code)

| Area | Spec says | Code does | Gap | Action |
|------|-----------|-----------|-----|--------|
| Storage backend | Dual Protocol + Postgres primary after 38 | Mongo only | **Yes** | 32–38 |
| best-config | Returns recommendation from history | Stub only | **Yes** | Slice 22 |
| SPLADE sparse sweep | Full open-source sparse | Index + registry ready; encode path partial | **Partial** | 35 + 22 |
| SIE reranking | BGE-reranker scores | Voyage/CrossEncoder only | **Yes** | Slice 22 |
| Export | CSV/JSONL download | Not implemented | **Yes** | Slice 28 |
| All Slice 21 items | SIE + sweep + Aim | Implemented + tested | **No** | — |

**Result**: Migration is the new critical path. PCTO Slice 22 remains Must but sequenced after cutover.
