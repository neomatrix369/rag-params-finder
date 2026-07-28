# rag-params-finder — Build Progress

**Last Updated**: 2026-07-28 (Slice 44 Residual §4 **IMPLEMENTED** — Nightly Stryker narrow mutate; local ~8m; Nightly VERIFIED pending)
**Current**: **45** ✅ · **44** ✅ Residual §4 **IMPLEMENTED** (#163; Nightly artifact VERIFIED pending) · **40** 📋 (theme folders #162). Migration track: **38** ✅; formal gate-closure debt **32** / **32C** / **32B** / **33**. Then **22** · **28** · **41B**. Deferred Mongo QoL **26/27/19**

PCTO plan context: [`docs/plan/TRAIL.md`](../plan/TRAIL.md) · Gap analysis: [`docs/plan/GAP_ANALYSIS.md`](../plan/GAP_ANALYSIS.md) · Migration PRD: [`docs/plan/PRD-supabase-pgvector-migration.md`](../plan/PRD-supabase-pgvector-migration.md)

---

## Quick Status

| Slice | Status | Time Target | Notes |
|-------|--------|-------------|-------|
| 1 — Skateboard | ✅ COMPLETE | ~75 min | End-to-end pipeline verified |
| 2 — Rerank | ✅ COMPLETE | ~10 min | Voyage + local reranking |
| 3 — Sweep expansion | ✅ COMPLETE | ~15 min | Cartesian product of runs ⭐ CORE FEATURE |
| 4 — Live status + polling | ✅ COMPLETE | ~15 min | Phase tracking, CLI --watch, detail screen |
| 5 — Multiple queries from persona JSON | ✅ COMPLETE | ~10 min | Loop over persona questions |
| 6 — Additional chunkers + retrieval | ✅ COMPLETE | ~45 min | fixed, token, sentence, semantic + sparse/hybrid + 5 new configs |
| 7 — Free/local embedding + reranking | ✅ COMPLETE | ~15 min | sentence-transformers, no API key needed |
| 8 — Dashboard UX improvements | ✅ COMPLETE | ~2 h | Loading feedback panels, polling indicators, pagination, unified chrome |
| 9 — Experiment deletion | ✅ COMPLETE | ~1 h | CLI delete command + dashboard confirmation modal, cascade cleanup |
| — — Vector DB stats + collapsible rows + boot reconciliation | ✅ COMPLETE | ~1.5 h | Cluster/experiment storage stats; collapsible panels; orphan `running` → `partial` on server boot |
| — — Pause/resume + Voyage catalog expansion | ✅ COMPLETE | ~2 h | Cooperative pause/resume; 12 Voyage embedding models; `voyage-context-3` contextualized API + segment splitting |
| — — Voyage sweep UX + Atlas tier specs | ✅ COMPLETE | ~1 h | Elapsed/ETA on progress card; timezone-aware UTC timestamps; `started_at` on first run; cluster tier/provider/region in vector DB stats |
| — — Search index preflight + indexes CLI | ✅ COMPLETE | ~2 h | `search_index_plan` + `search_index_guard`; HTTP 422 on submit; fail before runs; `indexes list\|reset`; 17 pytest scenarios |
| — — Scoped logging (Option A) | ✅ COMPLETE | ~1 h | `scope_log.py` server/CLI; `devLog.ts` dashboard dev console; Voyage error + dashboard failure visibility |
| — — Dashboard polling + API responsiveness | ✅ COMPLETE | ~1 h | `executors.py` thread pools; list 2 s / stats 60 s / explore 15 s polls; batched db-stats; anti-jitter `PollingIndicator` |
| — — Kimchi embedding provider | 🔀 BRANCH | ~2 h | Full CAST integration on `tessl-hackathon-kimchi-integration`; **main** has `kimchi` in `Provider` type only (no registry models / embedder yet) — v0.8.0 release notes are historical |
| — — Unit pytest suite | ✅ COMPLETE | ~1 h | **26 tests** at Slice 20 baseline (now **58** — see `development.md`) |
| 18 — Unified retriever config | ✅ COMPLETE | ~4–6 h | Unified "retrievers" group (traditional search + rerankers); auto-migrate old format; multi-reranker chains; see [`SLICE-18-UNIFIED-RETRIEVER-CONFIG.md`](SLICE-18-UNIFIED-RETRIEVER-CONFIG.md) |
| 10 — Run recovery (retry) | 🔨 PARTIAL | ~1–2 h | Boot reconciliation ✅; retry CLI/API remaining — [`SLICE-10-RUN-RECOVERY.md`](SLICE-10-RUN-RECOVERY.md) |
| 11 — Search Explorer enhancements | 📋 PLANNED | ~45 min | Viz + query filter; soft dep **30**; export → Slice 28 |
| 28 — Results export (CSV/JSONL) | 📋 PLANNED | ~1.5 h | Contributor [@cschanhniem](https://github.com/cschanhniem) — [issue #49](https://github.com/neomatrix369/rag-params-finder/issues/49) author/assignee · [`SLICE-28-RESULTS-EXPORT.md`](SLICE-28-RESULTS-EXPORT.md) |
| 29 — Padding cross-cutting propagation | ✅ COMPLETE | ~2 h | `_run_config_key()` + API + TS types + UI — spec: [`SLICE-29-PADDING-PROPAGATION.md`](SLICE-29-PADDING-PROPAGATION.md) |
| 16 — Parallel sweep execution | ✅ COMPLETE | ~2–4 h | Bounded concurrent `_run_single`; see [`SLICE-16-PARALLEL-SWEEP-RUNS.md`](SLICE-16-PARALLEL-SWEEP-RUNS.md) |
| 20 — Toolchain hardening | ✅ COMPLETE | ~2–3 h | `quality-gates.sh`, `repo-lint.sh`, `pre-push-gates.sh` (full gates on push), `install-git-hooks.sh`, coverage CI, ESLint, bandit, pip-audit, gitleaks, dependabot — includes CI path-filter + audit-secrets split follow-up in `SLICE-20-TOOLCHAIN-HARDENING.md` — [`SLICE-20-TOOLCHAIN-HARDENING.md`](SLICE-20-TOOLCHAIN-HARDENING.md) |
| 14 — Docker Compose | ✅ COMPLETE | ~2–3 h | `./start-services.sh`, prod + `docker-compose.dev.yml`, Atlas `/healthz` — [`SLICE-14-DOCKER-COMPOSE.md`](SLICE-14-DOCKER-COMPOSE.md) |
| ~~15 — CI/CD~~ | ✅ (via 20) | — | Superseded by Slice 20 — CI + `quality-gates.sh` + git hooks |
| 21 — SIE Skateboard | ✅ COMPLETE | ~4–6 h | SIE embeddings (BGE-M3, Stella-v5); caller-supplied corpus (`corpus: list[str]`); Aim logging; `POST /api/v1/sweep`; enhanced `/health`; `embedder_factory.py` dispatch — spec: [`SLICE-21-SIE-SKATEBOARD.md`](SLICE-21-SIE-SKATEBOARD.md) |
| 24 — Port standardisation | ✅ COMPLETE | ~1 h | Unique static ports: frontend 5173→5374 (avoids Vite default), SIE 8080→8720 (avoids Jenkins/Tomcat/etc.); backend 8001 unchanged — spec: [`SLICE-24-PORT-STANDARDISATION.md`](SLICE-24-PORT-STANDARDISATION.md) |
| 25 — Atlas Local Dev Mode | ✅ COMPLETE | ~1 h | `mongodb-atlas-local` Docker image as opt-in local backend; `local-atlas` compose profile; auto-provision all search indexes on boot for local URI; eliminates M0 512 MB ceiling for local dev — spec: [`SLICE-25-ATLAS-LOCAL.md`](SLICE-25-ATLAS-LOCAL.md) |
| 25B — Atlas Backend Switching | ✅ COMPLETE | ~1 h | Shipped as `--local`; now `--mongodb-local`; `mongodb start\|stop\|reset\|status`; unified [`mongodb-setup.md`](../user-guide/mongodb-setup.md); `scripts/lib/compose.sh` + `server/db/mongodb_uri.py` — spec: [`SLICE-25B-ATLAS-SWITCHING.md`](SLICE-25B-ATLAS-SWITCHING.md) |
| 22 — SIE Scooter | 📋 PLANNED | ~3 h | SIE reranking + SPLADE sparse + `GET /api/v1/best-config` — Must — **after Slice 38** — spec: [`SLICE-22-SIE-SCOOTER.md`](SLICE-22-SIE-SCOOTER.md) |
| 23 — SIE Bicycle | 📋 PLANNED | ~3 h | Ollama + Tier 2–3 retrieval + Evidently AI (Could, post-hackathon) — spec: [`SLICE-23-SIE-BICYCLE.md`](SLICE-23-SIE-BICYCLE.md) |
| 26 — Local MongoDB smooth-path docs | 📦 DEFERRED | ~1 h | Re-scope after Postgres cutover — [`SLICE-26-LOCAL-MONGODB-DOCS.md`](SLICE-26-LOCAL-MONGODB-DOCS.md) |
| 27 — MongoDB mode indicator | 📦 DEFERRED | ~2 h | Absorbed into Slice 36 as four-value `storage_mode` (`mongodb\|postgres` × `local\|cloud`) — [`SLICE-27-MONGODB-MODE-INDICATOR.md`](SLICE-27-MONGODB-MODE-INDICATOR.md) |
| 19 — Atlas storage quota guard | 📦 DEFERRED | ~3–5 h | Atlas-specific; Postgres stats in Slice 36 — [`SLICE-19-STORAGE-QUOTA-GUARD.md`](SLICE-19-STORAGE-QUOTA-GUARD.md) |
| 32 — Storage Backend Protocol | 🔨 IN PROGRESS | ~3–4 h | Storage + Retriever ports; Mongo adapter — [`SLICE-32-STORAGE-BACKEND-PROTOCOL.md`](SLICE-32-STORAGE-BACKEND-PROTOCOL.md) · [PR #110](https://github.com/neomatrix369/rag-params-finder/pull/110) |
| 32C — Storage Protocol Review Remediation | 📋 PLANNED | ~2–3 h | Craft split, port schemas, index deferral, checklist hygiene — [`SLICE-32C-STORAGE-PROTOCOL-REVIEW-REMEDIATION.md`](SLICE-32C-STORAGE-PROTOCOL-REVIEW-REMEDIATION.md) |
| 32B — Storage Protocol Gate Closure | 📋 PLANNED | ~1–2 h | Coverage, mutation/waiver, full gates, nw-review, COMPLETE — [`SLICE-32B-STORAGE-PROTOCOL-GATE-CLOSURE.md`](SLICE-32B-STORAGE-PROTOCOL-GATE-CLOSURE.md) |
| 33 — Postgres schema + CRUD | 🔨 IN PROGRESS | ~4–6 h | Pool, schema, cascade, local Path A (shipped `--postgres` → `--postgres-local` in 37), 19 live tests, CI job — hosted DX deferred to 37 — [`SLICE-33-POSTGRES-SCHEMA-CRUD.md`](SLICE-33-POSTGRES-SCHEMA-CRUD.md) |
| 34 — Postgres dense retrieval | ✅ COMPLETE | ~3–4 h | pgvector dense + embedding_model filter; Atlas-scale scores; HNSW iterative_scan; mode/hosted DX handed to 36–37 — [`SLICE-34-POSTGRES-DENSE-RETRIEVAL.md`](SLICE-34-POSTGRES-DENSE-RETRIEVAL.md) |
| 35 — Postgres sparse + hybrid | ✅ COMPLETE | ~4–5 h | tsvector + RRF + Supabase-mode copy hygiene; equivalence CONDITIONAL → 38 — [`SLICE-35-POSTGRES-SPARSE-HYBRID.md`](SLICE-35-POSTGRES-SPARSE-HYBRID.md) |
| 36 — Preflight + stats + storage_mode | ✅ COMPLETE | ~3–4 h | Catalog preflight 422 + four-value `storage_mode`; live smoke `postgres-local`; mutation waived #101 — [`SLICE-36-POSTGRES-PREFLIGHT-STATS.md`](SLICE-36-POSTGRES-PREFLIGHT-STATS.md) |
| 37 — Local/cloud parity + low-friction switch | ✅ COMPLETE | ~3–4 h | Four-flag grid + config↔server 422 + supabase normalize + live `postgres-local`/`postgres-cloud` smoke; `SUPABASE_URI` alias; removed `--local`/`--postgres` flags — [`SLICE-37-POSTGRES-LOCAL-CLOUD-PARITY.md`](SLICE-37-POSTGRES-LOCAL-CLOUD-PARITY.md) · [`gate-evidence/slice-37.json`](../gate-evidence/slice-37.json) |
| 38 — Cutover + ADR-004 | ✅ COMPLETE | ~3–4 h | ADR-004 Accepted; local comparison VERIFIED; independent backends #129; **no default flip** (#130 Won't) — [`SLICE-38-CUTOVER-ADR-004.md`](SLICE-38-CUTOVER-ADR-004.md) · [`gate-evidence/slice-38.json`](../gate-evidence/slice-38.json) |
| 30 — Search Explorer UX | 📋 PLANNED | ~2 h | Tab latency, zero-score noise, BM25 labels, VDB card — Could — spec: [`SLICE-30-SEARCH-EXPLORER-UX.md`](SLICE-30-SEARCH-EXPLORER-UX.md) |
| 31 — Experiment list filter | 📋 PLANNED | ~2 h | Status dropdown + name/ID search — Should — spec: [`SLICE-31-EXPERIMENT-LIST-FILTER.md`](SLICE-31-EXPERIMENT-LIST-FILTER.md) |
| 39 — Demo-ready dashboard polish | ✅ COMPLETE | ≤2 h | Results-led list/detail journey; 390/1440 responsive, WCAG, keyboard, lifecycle, network, and component verification — [`SLICE-39-DEMO-READY-DASHBOARD-POLISH.md`](SLICE-39-DEMO-READY-DASHBOARD-POLISH.md) |
| 40 — Documentation Plan/Slices SSOT alignment | 📋 PLANNED | ~2–3 h | Plan vs slices boundary + numbered theme folders `01`–`07` (#162); `PROGRESS.md` flat SSOT; `git mv` Should — [`SLICE-40-DOCS-PLAN-SLICES-SSOT.md`](SLICE-40-DOCS-PLAN-SLICES-SSOT.md) |
| 41A — Bayesian Search: Simple Functional | ✅ COMPLETE | ~2.5 h | All ACs verified; trial_log, CLI Bayesian summary, and test rigour added in closure pass (2026-07-23); 217 tests green |
| 41B — Bayesian Search: Numeric Improvements | 📋 PLANNED | ~2–3 h | Unlocked: `bayesian.parallelism` (constant liar, ≤4 workers), `padding` as third numeric dimension, `n_trials` formula, 3-condition stopping loop, 41A embedding-parallelism gap fix — [`SLICE-41B-BAYESIAN-SEARCH-ADVANCED.md`](SLICE-41B-BAYESIAN-SEARCH-ADVANCED.md) |
| 41C — Bayesian Search: Extended | 📋 PLANNED | ~3–4 h | All questions resolved (A1 SQLite, A2 waived, A4 N=20, D3 sweep_summary keys, D7 RandomConfig); blocked only on 41B ✅: study persistence, categorical axes, random search, dashboard card, default promotion — [`SLICE-41C-BAYESIAN-SEARCH-EXTENDED.md`](SLICE-41C-BAYESIAN-SEARCH-EXTENDED.md) |
| 42 — Docker Build Optimisation | ✅ COMPLETE | ~2–3 h | Multi-stage server/frontend Dockerfiles; BuildKit cache mounts; nginx:alpine runtime (62 MB); CI docker-build job (non-blocking, path-scoped) — [PR #107](https://github.com/neomatrix369/rag-params-finder/pull/107) |
| 43 — Supabase example-config verification | ✅ COMPLETE | ~1–2 h | **Could** — 16/16 local Postgres smoke runs complete; operator docs distinguish `STORAGE_BACKEND` from `database_provider` and explain env asymmetry — [`SLICE-43-SUPABASE-CONFIG-VERIFICATION.md`](SLICE-43-SUPABASE-CONFIG-VERIFICATION.md) |
| 44 — Frontend coverage + gate summary | ✅ COMPLETE | Phase A+B + #142 | FE **95/90/95/95**; BE **95/90/n/a/95** — DECISIONS #142 — Residual §4 Nightly Stryker **IMPLEMENTED** (#163; Nightly VERIFIED pending) — [`SLICE-44-FRONTEND-COVERAGE-GATE.md`](SLICE-44-FRONTEND-COVERAGE-GATE.md) · [`gate-evidence/slice-44.json`](../gate-evidence/slice-44.json) |
| 45 — Module theme separation + FE/BE craft | ✅ COMPLETE | ~16–24 h | Hotspots 1–5 **IMPLEMENTED**; FE/BE craft + scripts themes; Could leftovers #161; floors green; mutation #160; evidence [`slice-45.json`](../gate-evidence/slice-45.json) — [`SLICE-45-MODULE-THEME-SEPARATION.md`](SLICE-45-MODULE-THEME-SEPARATION.md) · [PR #130](https://github.com/neomatrix369/rag-params-finder/pull/130) |

**Legend**: 📋 PLANNED, 🔨 IN PROGRESS, ✅ COMPLETE, 🔀 BRANCH, 📦 DEFERRED

---

## Plan Track (PCTO + storage migration)

Plan-tracked slices with dependencies. Gate evidence: [`docs/plan/gate-evidence/`](../plan/gate-evidence/). PRD: [`docs/plan/PRD-supabase-pgvector-migration.md`](../plan/PRD-supabase-pgvector-migration.md).

| Slice | MoSCoW | Status | Depends on | Notes |
|-------|--------|--------|------------|-------|
| 21 | Must | ✅ COMPLETE | — | SIE Skateboard |
| 25 | Should | ✅ COMPLETE | 21 | Atlas Local |
| 25B | Should | ✅ COMPLETE | 25 | Atlas switching |
| 29 | Must | ✅ COMPLETE | — | Padding propagation |
| 32 | Must | 🔨 IN PROGRESS | — | Storage + Retriever ports; Mongo adapter |
| 32C | Must | 📋 PLANNED | 32 | Review remediation — craft/architecture nw-review BLOCKERs |
| 32B | Must | 📋 PLANNED | 32C | Gate closure — coverage, mutation/waiver, full gates, nw-review |
| 33 | Must | 🔨 IN PROGRESS | 32B | Supabase schema + CRUD + local pgvector smoke |
| 34 | Must | ✅ COMPLETE | 33 | Dense pgvector |
| 35 | Must | ✅ COMPLETE | 34 | Sparse + hybrid + copy hygiene |
| 36 | Must | ✅ COMPLETE | 35 | Preflight + db-stats + storage mode (replaces 27) |
| 37 | Must | ✅ COMPLETE | 36 | Supabase local/hosted parity |
| 38 | Must | ✅ COMPLETE | 37 | ADR-004 + comparison; no default flip (#130) |
| 28 | Must | 📋 PLANNED | — | External — @cschanhniem / #49 |
| 22 | Must | 📋 PLANNED | 21, 32, 38 (soft) | SIE Scooter — hard dep 32 Protocol; soft 38 cutover |
| 26 | Should | 📦 DEFERRED | 25B | Mongo docs — re-scope post-cutover |
| 27 | Should | 📦 DEFERRED | — | Absorbed into Slice 36 four-value storage_mode (`mongodb\|postgres` × `local\|cloud`) |
| 19 | Should | 📦 DEFERRED | — | Atlas quota — Postgres path in 36 |
| 16 | Should | ✅ COMPLETE | — | Parallel sweep |
| 11 | Could | 📋 PLANNED | 30 (soft) | Search Explorer — viz + filters; after Slice 30 UX |
| 23 | Could | 📋 PLANNED | 22 | SIE Bicycle |
| 10 | Could | 🔨 PARTIAL | — | Boot reconciliation ✅; retry CLI/API remaining |
| 30 | Could | 📋 PLANNED | — | Search Explorer UX |
| 31 | Should | 📋 PLANNED | — | Experiment list filter |
| 43 | Could | ✅ COMPLETE | 35 (soft: 37) | Supabase config live smoke + operator QoL — hosted smoke remains optional and is owned by 37 |
| 39 | Should | ✅ COMPLETE | — | Demo-ready list/detail journey; lifecycle component coverage and clean implementation history verified |
| 40 | Should | 📋 PLANNED | — | Plan vs slices SSOT + theme folders `01`–`07` (#162); status SSOT remains flat here |
| 41A | Could | ✅ COMPLETE | 16 | All ACs closed; trial_log in bayesian_summary; CLI Trial History table; 10 new tests + parametrize refactor (13 total); 183 total tests green |
| 41B | Could | 📦 PARKED | 41A + owner data | Parallelism, categorical axes, study persistence, random search — open after 41A ships and production evidence exists; spec: [`SLICE-41B-BAYESIAN-SEARCH-ADVANCED.md`](SLICE-41B-BAYESIAN-SEARCH-ADVANCED.md) |
| 42 | Should | ✅ COMPLETE | none | Docker Build Optimisation — multi-stage builds, cache mounts, nginx runtime; [PR #107](https://github.com/neomatrix369/rag-params-finder/pull/107) |

**Execution order**: 21 → 25 → 25B → 29 → 39 (done) → **32 → 32C → 32B → 33 → 34 → 35 → 36 → 37 → 38** → **22** → 28*(external)* → 31 → 30 → 16 → 11 → 23 → 10

---

## Maintenance Log (non-slice)

| Date | Item | Outcome |
|------|------|---------|
| 2026-07-28 | Slice 44 Residual §4 Nightly Stryker **IMPLEMENTED** (#163) | Narrow mutate to utils/services/hooks (9 files / 868 mutants; 642 tested w/ ignoreStatic); `ignoreStatic` + exclude `StringLiteral`; concurrency 4; progress; pin 9.6.1; timeout 90; artifact@v5. Local full run **Done in 7m49s**, score ~64.7%. Nightly artifact **VERIFIED** pending `workflow_dispatch` URL. |
| 2026-07-28 | Slice 44 residual §4 — Nightly Stryker 1h timeout (#163) | Slice 44 PR #121 grew FE dry-run 16→252 tests; Nightly Stryker (~3770 mutants) cancels at GHA 1h with no artifact ([run 30329826459](https://github.com/neomatrix369/rag-params-finder/actions/runs/30329826459/job/90182449893)). Todos on [`SLICE-44`](SLICE-44-FRONTEND-COVERAGE-GATE.md) Residual §4: Must narrow mutate; Should ignore*/concurrency/progress; Could timeout/pin; NIT upload-artifact@v5. **PROPOSED** → later **IMPLEMENTED**. |
| 2026-07-27 | Meterian `.meterian` exclusions (chore/project-hygiene) | Added root `.meterian` (CVE + langsmith library waivers) for findings with no congruent lock fix — aim 4.x yanked, langchainjs CVE mis-attributed to Python, transformers blocked on ST&lt;4, langsmith≥0.8.18 blocked on sie-sdk websockets&lt;15. Parity with `.trivyignore` / `pip-audit.sh`. Docs: `development.md` + `nightly.yml` comment. **IMPLEMENTED**; **VERIFIED** pending next Meterian nightly/`workflow_dispatch`. |
| 2026-07-27 | Meterian nightly OSS + stack pin + artifacts (chore/project-hygiene) | Fixed GHA wiring: `oss: true` (public MIT; no token), `cli_args` (was invalid `meterian-args`), dropped `setup-java`, pinned `--enabled-scanners=python,nodejs` + `--scan-java=false`, archives `meterian-<run>` (HTML/JUnit/SARIF + `sbom.cdx.json`/`sbom.csv`). `meterian-reports/` gitignored. Local `security-scan.sh --meterian` remains Docker CLI + token-gated. **IMPLEMENTED** in `nightly.yml`; **VERIFIED** pending a successful nightly/`workflow_dispatch` run. |
| 2026-07-26 | Configs split: `configs/mongodb/` + `configs/supabase/` | Example YAMLs reorganised by backend with mirrored stems; shared `questions.example.json` at `configs/`. Docs/CLI/agent entry points + `test_config_examples.py` updated. Supabase twins use `database_provider: supabase`; sparse/hybrid still Slice 35. |
| 2026-07-24 | Commit-stage optimisations (chore/project-hygiene) | Three opts applied: (1) dmypy daemon replaces mypy at commit — warm ~0.5s vs 2.2s cold (first run ~60s); (2) `frontend-verify` hook split — `tsc --noEmit` at commit saves ~8s/commit, `vite build` deferred to push; (3) actionlint confirmed already running at ~620ms via pre-commit managed binary — no PATH install needed. `.dmypy.json` added to `.gitignore`. |
| 2026-07-24 | Chalk provenance job (chore/project-hygiene) | Added 7th nightly job `chalk` using `crashappsec/setup-chalk-action@v0.0.3`; marks `server/`, `cli/`, `scripts/` with embedded chalk marks; `id-token: write` grants Sigstore keyless signing; uploads `chalk.log` artifact (90 days, `if-no-files-found: warn`). Complements CycloneDX SBOM: SBOM answers "what's in the code?"; Chalk answers "is this the exact artifact CI built?". |
| 2026-07-24 | Nightly artifact archiving audit (chore/project-hygiene) | Audited all 6 nightly jobs for missing `if: always()` on upload steps. Found 4 gaps: `mutmut results`+`junitxml` lines lacked `\|\| true` (fixed), Stryker upload missing `if: always()` + `if-no-files-found: warn` (fixed), SBOM upload missing `if: always()` (fixed). trufflehog/meterian/container-scan produce no local artifacts — no gaps. |
| 2026-07-24 | Nightly cron fix: Monday-only → every night (chore/project-hygiene) | `cron: '0 2 * * 1'` (Monday only) changed to `'0 2 * * *'` (every night 02:00 UTC). Nightly is meant to run nightly; running only on Monday misses 6 days of vulnerability and mutation signal. |
| 2026-07-24 | BACKEND_CHANGED variable added to pre-push-gates.sh (chore/project-hygiene) | Only `BACKEND_LOCK_CHANGED` (gates pip-audit) existed; `BACKEND_CHANGED` (gates pytest) was absent — pytest ran unconditionally on every push. Added `BACKEND_CHANGED` tracking `server/\|cli/\|tests/\|pyproject.toml\|uv.lock`, matching `ci.yml` `backend` paths-filter exactly. Conservative fallback now sets all 4 vars to 1 when change detection fails. |
| 2026-07-24 | Nightly enhancements (chore/project-hygiene) | Added Meterian SCA + license as separate dedicated job (`--min-security=95 --min-licensing=95`); SBOM job kept separate (CycloneDX via `anchore/sbom-action`); P2 fix from review: Trivy license scan exit-code changed `0`→`1` (blocks on HIGH/CRITICAL, now consistent with container scan); `workflow_dispatch` already present — all nightly jobs can be triggered manually. |
| 2026-07-24 | Gate timing analysis (chore/project-hygiene) | Full commit/push/CI timing table produced. Key findings: commit wall-clock ~25s (tsc split saves 8s/commit); push ~30–43s; CI backend job ~112s (env setup dominates). Three optimisations justified above. All checks placement justified as efficient/pragmatic/complete. |
| 2026-07-24 | nw-review: nw-platform-architect-reviewer (chore/project-hygiene) | NEEDS_REVISION → fixed: 2 blockers (Stryker jest→vitest runner, TruffleHog @main pin); 3 criticals (trivy-action @master→0.29.0 ×2, sbom-action @v0→@v0.17.0); 1 high (missing `name:` in code-review-graph.yml); 1 medium (pre-push-gates fallback runs all checks when change detection fails). Fixed in commit e7740dc. |
| 2026-07-24 | Frontend JUnit XML + v8 coverage (chore/project-hygiene) | Vitest was only printing to stdout; no JUnit XML, no coverage files. Added `@vitest/coverage-v8`; updated `vite.config.ts` with JUnit reporter + coverage config; output to `.test-results/frontend-junit.xml` and `.reports/coverage/frontend/`; added `test:coverage` + `test:ci` scripts; output dirs gitignored. Baseline coverage: 47.45% statements. |
| 2026-07-24 | nw-agent-builder-reviewer run | P2 (fixed): Trivy SBOM exit-code inconsistency; P3 (noted): pre-push-gates.sh comment on `npm run test` → vitest. actionlint/shellcheck/safety verified clean. idempotency confirmed: zero overlap between commit and push stages. |
| 2026-07-24 | /sync-docs (chore/project-hygiene) | APPLIED — `CLAUDE.md` hook descriptions (line 234); `docs/contributor-guide/development.md` hook table + when-checks-run table + CI section (job count 4→5, nightly T4 row added) + pre-push-gates.sh description. No user-guide or CHANGELOG changes warranted (tooling chore, no user-facing behavior). |
| 2026-07-24 | Idempotent hooks (chore/project-hygiene) | Replaced push-gate full `quality-gates.sh --full` with `pre-push-gates.sh` (push-specific only: full pytest+coverage, vite build, pip-audit, vitest, npm audit); added `pytest-testmon` at commit stage — runs only tests for changed modules (~1.7s warm vs 30s full); eliminated commit/push duplication; PR #103 |
| 2026-07-24 | Project hygiene chore (chore/project-hygiene) | Added `.github/workflows/nightly.yml` (T4: mutmut, Stryker, TruffleHog full-history, SBOM+Trivy, Meterian, container scan); `.github/workflows/code-review-graph.yml`; `.prettierignore`; `.testmondata*` glob in `.gitignore` (covers SQLite WAL files); `workflow_dispatch` on nightly enables manual runs; PR #103 |
| 2026-07-24 | ruff markdown format fix | CI ruff (newer) formats Python blocks in `.md` files by default; local ruff 0.15.12 requires `--preview`; manually aligned `docs/_internal/TIEBREAKER-EXPLANATION-FEATURE.md` and `docs/contributor-guide/extending.md` to match expected output; merged PR #102 |
| 2026-07-23 | Slice 41A closure | Added trial_log to bayesian_summary (orchestrator+API+CLI), CLI _print_summary Trial History table, 10 new unit tests + parametrize refactor (13 total); lint/type fixes; all 14 ACs ticked; 183 tests green; gate-evidence PASSED |
| 2026-07-23 | Slice 41A AT coverage | /nw-distill → 17 ATs (AT-01–17) written across test_slice16_parallel_sweep.py and test_cli_print_summary.py; AT-08 uncovered production bug (UnboundLocalError in _finalise_bayesian_experiment PARTIAL+failures path); fixed with else: completion_reason = "partial_completion"; 200 tests green |
| 2026-07-23 | Coverage gap remediation | search_index_guard 49%→100% (9 tests: collect_search_index_snapshot + validate sub-paths); orchestrator 70%→72% (8 tests: pure functions, error handlers, early-cancel, truncation, defensive promotion); gap was masked by aggregate 80% gate; 217 tests green |
| 2026-07-22 | Slice 41B planning | Added PARKED slice for Bayesian advanced features (constant liar parallelism, categorical axes, study persistence, random search); TRAIL + PROGRESS + DECISIONS aligned; full architecture record preserved in slice spec |
| 2026-07-21 | Slice 41A implementation follow-up | Added Bayes summary normalization behavior in API/detail responses for partial and running states; documented `not_started` and `discarded_trials` contract alignment; docs now aligned with tested behavior |
| 2026-07-20 | Slice 40 merged into Slice 20 | CI/CD trigger topology hardening (tooling split, path filters, lockfile-aware audits) consolidated into Slice 20 as Round 2 follow-up and tracked as part of complete Slice 20 |
| 2026-07-19 | Slice 39 review revisions | Added 7 lifecycle component scenarios, wired them into local/CI gates, and removed unrelated MongoDB work from the implementation branch |
| 2026-07-18 | Slice 39 implementation verified | Exact-main before/after checks at 1440×900 and 390×844; lifecycle, async, keyboard, WCAG contrast, and 2 s polling checks passed |
| 2026-07-20 | Slice 40 introduced | Added a docs-alignment maintenance slice to formalize plan/slice tracking boundaries and keep PROGRESS SSOT in `docs/plan/slices/PROGRESS.md` |
| 2026-07-01 | Dependabot PR triage #26–#43 | 4 merged (#36–#39), 5 closed (#26, #40–#43) |
| 2026-07-02 | Plan health-check + gap refresh | TRAIL, GAP_ANALYSIS, HANDOFF updated; gate-evidence backfilled |
| 2026-07-02 | Merge plan PROGRESS into slices PROGRESS | Single SSOT — removed `docs/plan/PROGRESS.md` duplicate |
| 2026-07-04 | Merge PRs #56, #57, #58 | Actions upgrades (cache v6, checkout v7) + plan health-check refresh; all merged to main |
| 2026-07-04 | Plan health-check + gap analysis | TRAIL health ✅ OK (0 legacy gaps); PR queue updated; execution order + PR merge prereqs reviewed |
| 2026-07-05 | Merge PRs #47, #48, #59, #60, #61 | Chunker fixes + plan gap analysis + review follow-ups on main; Slice 28 unblocked |
| 2026-07-06 | Plan prereq clearance sync | HANDOFF, PROGRESS queue, slice Before-Checks updated; #47/#48 marked satisfied |
| 2026-07-06 | Slice 28 contributor assigned | @cschanhniem (issue #49 author/assignee) owns implementation; core team on Slice 22 |
| 2026-07-06 | Slice 29 complete | Padding in `_run_config_key()`, explore responses, sweep_summary, TS types, ExperimentDetail + SearchExplorer UI |
| 2026-07-09 | Supabase migration plan | PRD integrated; slices 32–38 Must; dual-backend; ahead of 22; deferred 26/27/19 |
| 2026-07-09 | Plan gap bridge (continuation) | Health ✅; created SLICE-11; aligned 19/26/27 DEFERRED specs; 10 PARTIAL; Before-Checks 10/16; deps 22/23/28 order |
| 2026-07-09 | nw-review iter 3 polish | TRAIL soft dep 30; escape-hatch >2d; PRD cutover baseline; SLICE-11 latency handoff; SLICE-36 storage-mode AC |

---

## Open PR Queue (snapshot 2026-07-06)

| PR | Verdict | Reason |
|----|---------|--------|
| #13 | Branch track | Kimchi integration — separate hackathon |

---

## Slice 1: Skateboard ✅

**Status**: ✅ BUILT (pending verification) | **Started**: 2026-05-02 | **Completed**: 2026-05-02 | **Target**: ~75 min

### Goal
End-to-end pipeline working with one chunker (RECURSIVE), one embedding model (voyage-3.5-lite), one query, no rerank, no sweep.

### Acceptance Criteria (Code Complete)
- [x] FastAPI boots; `/healthz` returns ok — **Code ready** (needs .env)
- [x] Atlas connection works; 6 collections + vector index exist — **Code ready** (needs manual vector index in Atlas UI)
- [x] `POST /experiments` accepts a minimal config and runs in BackgroundTask — **Code complete**
- [x] Pipeline: parse PDF → RECURSIVE chunker → Voyage embed → Atlas write → Voyage query embed → DENSE search → write results — **Code complete**
- [x] CLI submits and exits cleanly (no `--watch` polling yet) — **Code complete**
- [x] Dashboard ExperimentsScreen renders ONE row from `/experiments` — **Code complete**
- [x] README has Quickstart section (judge can run locally) — **Complete**

### Verification Pending
- [ ] Live test with real .env (VOYAGE_API_KEY + MONGODB_URI)
- [ ] Atlas vector index created manually
- [ ] Sample PDF added to `papers/sample.pdf`
- [ ] End-to-end run: CLI submit → server execute → dashboard display

### Files to Create
**Server**:
- `server/__init__.py`
- `server/main.py` — FastAPI app + /healthz
- `server/api/experiments.py` — POST /experiments, GET /experiments
- `server/core/pdf_parser.py` — pypdf wrapper
- `server/core/chunkers/__init__.py` — Enum + dispatcher
- `server/core/chunkers/recursive.py` — LangChain RecursiveCharacterTextSplitter
- `server/core/embedder.py` — Voyage client singleton
- `server/core/orchestrator.py` — Per-run pipeline executor
- `server/models/enums.py` — ChunkingMethod, RetrievalMethod, Phase
- `server/models/config.py` — Pydantic config models
- `server/models/status.py` — RunStatus model
- `server/models/results.py` — Result models
- `server/db/atlas.py` — MongoDB client + collection helpers
- `server/db/indexes.py` — Vector index creation
- `server/utils/logger.py` — Structured logging

**CLI**:
- `cli/__init__.py`
- `cli/main.py` — Typer app + `run` command
- `cli/config_loader.py` — YAML parser
- `cli/api_client.py` — HTTP client to server

**Frontend**:
- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/tailwind.config.js`
- `frontend/postcss.config.js`
- `frontend/index.html`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/ExperimentsScreen.tsx`
- `frontend/src/services/apiClient.ts`
- `frontend/src/types/index.ts` — Hand-mirrored enums + types

**Configs**:
- `configs/example.yaml`
- `configs/questions.example.json`

**Docs**:
- `docs/plan/slices/SLICE-01-SKATEBOARD.md`
- `docs/ARCHITECTURE.md` (brief)

### Quick-Win Cuts
- No reranking (Slice 2)
- No sweep expansion (Slice 3)
- No live status tracking (Slice 4)
- No multiple queries (Slice 5)
- No recovery logic (Slice 10)
- No --watch CLI flag (Slice 4)

### Verification
```bash
# Server
uvicorn server.main:app --reload --port 8001
curl http://localhost:8001/healthz

# CLI
rag-params-finder run --config configs/example.yaml

# Dashboard
cd frontend && npm run dev
```

### Files Created (53 total)

**Foundation** (7):
- pyproject.toml, .env.example, .gitignore, README.md
- docs/plan/slices/PROGRESS.md, docs/ARCHITECTURE.md, docs/plan/slices/SLICE-01-SKATEBOARD.md

**Server** (20):
- server/{__init__.py, main.py, utils/logger.py}
- server/models/{enums.py, config.py, status.py, results.py}
- server/db/{atlas.py, indexes.py}
- server/core/{orchestrator.py, pdf_parser.py, embedder.py, retriever.py}
- server/core/chunkers/{__init__.py, recursive.py, fixed.py, token.py, sentence.py, semantic.py}
- server/api/experiments.py

**CLI** (4):
- cli/{__init__.py, main.py, config_loader.py, api_client.py}

**Frontend** (13):
- frontend/{package.json, vite.config.ts, tailwind.config.js, postcss.config.js, index.html, tsconfig.json, tsconfig.node.json}
- frontend/src/{main.tsx, App.tsx, index.css}
- frontend/src/components/ExperimentsScreen.tsx
- frontend/src/services/apiClient.ts
- frontend/src/types/index.ts

**Configs** (2):
- configs/{example.yaml, questions.example.json}

**Placeholders** (4 chunkers):
- fixed.py, token.py, sentence.py, semantic.py (NotImplementedError, deferred to Slice 6)

### Decisions
| Decision | Why |
|---|---|
| pypdf over pdfminer.six | Simpler API, sufficient for plain text extraction |
| Voyage voyage-3.5-lite only | Cheapest model for MVP, add others in Slice 7 |
| RECURSIVE chunker only | Most common method, LangChain already has it |
| No rerank in Slice 1 | Simplify to DENSE-only retrieval first |
| BackgroundTasks not Celery | No queue infrastructure for hackathon MVP |
| Tailwind installed locally | No CDN scripts in index.html per spec |
| Hand-mirrored TS types | No codegen tooling for hackathon speed |
| Hardcoded single query | Defer persona JSON loop to Slice 5 |

---

## Slice 2: Rerank ✅

**Status**: ✅ BUILT | **Started**: 2026-05-02 | **Completed**: 2026-05-02 | **Target**: ~20 min | **Actual**: ~10 min

### Goal
Add Voyage rerank-2.5-lite to refine dense search results (top-20 → top-5).

### What Changed
- **NEW**: `server/core/reranker.py` — Voyage rerank client (reuses embedder's client singleton)
- **EDIT**: `server/core/orchestrator.py` — Conditional RERANKING phase after QUERYING; fetches `top_k_initial` candidates, reranks to `top_k_final`
- **EDIT**: `configs/example.yaml` — `rerank_model: rerank-2.5-lite` (was `null`)

### Key Design Decisions
| Decision | Why |
|---|---|
| Reuse embedder's `get_client()` singleton | Voyage SDK uses one client for embed + rerank; avoid duplicate initialization |
| Conditional reranking (gate on `rerank_model`) | Allows `null` to skip reranking for A/B comparison |
| `model_copy(update=...)` for SearchResult | Immutable Pydantic updates — preserves original dense_score alongside rerank_score |

### No Changes Required
- Frontend types already had `rerank_score?: number`
- `Phase.RERANKING` enum already existed
- `RetrievalConfig.rerank_model` already in config model

---

## Slice 3: Sweep Expansion ✅

**Status**: ✅ BUILT | **Started**: 2026-05-02 | **Completed**: 2026-05-02 | **Target**: ~25 min | **Actual**: ~15 min

### Goal
Cartesian product expansion: one YAML config with N models × M methods × P sizes × Q overlaps × R retrieval methods → N×M×P×Q×R independent runs.

### What Changed
- **NEW**: `RunParams` model + `expand_sweep()` in `server/models/config.py`
- **NEW**: `server/api/runs.py` — `GET /runs/{run_id}/status` endpoint
- **NEW**: `server/api/__init__.py` — package init
- **REWRITE**: `server/core/orchestrator.py` — split into `run_sweep()` + `run_single()` (accepts `RunParams`)
- **REWRITE**: `server/api/experiments.py` — shows run_count in POST response, adds `GET /experiments/{id}/results`, includes run statuses in `GET /experiments/{id}`
- **EDIT**: `server/main.py` — register `/runs` router
- **EDIT**: `configs/example.yaml` — multi-value sweep (3 chunk_sizes × 2 overlaps = 6 runs)
- **EDIT**: `frontend/src/types/index.ts` — `run_count`, `failed_count` fields on `Experiment`
- **EDIT**: `frontend/src/components/ExperimentsScreen.tsx` — Runs column + partial status badge

### Key Design Decisions
| Decision | Why |
|---|---|
| `expand_sweep()` as pure function on config | Testable without side effects; called both in API (preview count) and orchestrator (execute) |
| Bounded in-process parallelism implemented | `execution.parallelism` now caps concurrent sweep runs (default 1, max 16); see [Slice 16](SLICE-16-PARALLEL-SWEEP-RUNS.md) |
| `run_sweep()` + `run_single()` split | Single Responsibility — sweep management vs pipeline execution |
| `on_error: continue/stop` | Allows partial completion without losing all results |
| `partial` status for mixed outcomes | Distinguishes "some failed" from "all failed" or "all complete" |

---

## Slice 4: Live Status + Polling ✅

**Status**: ✅ BUILT | **Started**: 2026-05-02 | **Completed**: 2026-05-02 | **Target**: ~30 min | **Actual**: ~15 min

### Goal
Live status tracking with CLI --watch and dashboard drill-down.

### What Changed
- **EDIT**: `cli/main.py` — Added `--watch` flag (default on), Rich Live table polling runs every 2s
- **EDIT**: `cli/api_client.py` — Added `get_experiment()`, `get_run_status()` helpers
- **EDIT**: `server/core/orchestrator.py` — elapsed_ms tracking per run; experiment_id passed from API layer
- **EDIT**: `server/api/experiments.py` — experiment_id created in handler, returned in POST response
- **NEW**: `server/api/runs.py` — `GET /runs/{run_id}/status`
- **NEW**: `frontend/src/components/ExperimentDetailScreen.tsx` — Phase indicator dots, run table, polling
- **EDIT**: `frontend/src/App.tsx` — Simple state-based routing (list ↔ detail)
- **EDIT**: `frontend/src/components/ExperimentsScreen.tsx` — Clickable rows with `onSelect` prop

### Key Design Decisions
| Decision | Why |
|---|---|
| Rich Live table in CLI | Real-time phase display without clearing terminal |
| experiment_id created in API handler | Returned immediately so CLI can poll before background task finishes |
| Phase indicator dots in dashboard | Visual progress without text clutter |
| State-based routing (no react-router) | Minimal dependency; only two screens |

---

## Slice 5: Multiple Queries from Persona JSON ✅

**Status**: ✅ BUILT | **Started**: 2026-05-02 | **Completed**: 2026-05-02 | **Target**: ~20 min | **Actual**: ~10 min

### Goal
Load queries from persona JSON file and loop over all questions per run.

### What Changed
- **NEW**: `server/core/query_loader.py` — `Query` dataclass + `load_queries()` from persona JSON
- **EDIT**: `server/core/orchestrator.py` — Replaced hardcoded query with `load_queries()` loop; stores `persona_id` and `focus` on each `QueryResult`

### Key Design Decisions
| Decision | Why |
|---|---|
| `Query` as frozen dataclass (not Pydantic) | Lightweight read-only data; no serialization needed |
| Loop inside `run_single()` | Each query embeds + searches + reranks independently |
| Rerank phase entered per query | Phase indicator shows reranking activity for each query |

---

## Slice 7: Free/OS Embedding + Reranking Models ✅

**Status**: ✅ BUILT | **Started**: 2026-05-02 | **Completed**: 2026-05-02 | **Target**: ~15 min

### Goal
Add local sentence-transformers models (embedding + reranking) as alternatives to Voyage AI. No API key, no rate limits. Explicit `provider` field in YAML configs drives routing.

### What Changed
- **NEW**: `server/core/model_registry.py` — Unified registry for embedding and reranker models (provider, dimensions, HuggingFace ID)
- **NEW**: `server/core/local_embedder.py` — sentence-transformers SentenceTransformer wrapper (lazy-load, cached)
- **NEW**: `server/core/local_reranker.py` — sentence-transformers CrossEncoder wrapper (lazy-load, cached)
- **NEW**: `configs/example-local.yaml` — All-local experiment config (no Voyage key needed)
- **NEW**: `configs/example-voyage-ai.yaml` — Preserved Voyage AI config for reference
- **EDIT**: `server/models/config.py` — Added `provider` field to `EmbeddingConfig`, `rerank_provider` to `RetrievalConfig`; Pydantic validators cross-check model names match declared provider; `RunParams` carries `embedding_provider` and `rerank_provider`
- **EDIT**: `server/core/embedder.py` — Accepts `provider` param directly (no longer queries registry at runtime)
- **EDIT**: `server/core/reranker.py` — Accepts `provider` param directly
- **EDIT**: `server/core/orchestrator.py` — Passes `embedding_provider` and `rerank_provider` from `RunParams`
- **EDIT**: `cli/config_loader.py` — Validates models against registry at load time; cross-checks declared provider
- **EDIT**: `server/core/retriever.py` — Dynamic vector index name via `get_index_name(model)` (supports `vector_index_1024` and `vector_index_384`)
- **EDIT**: `server/db/indexes.py` — Updated log messages for multi-dimension indexes
- **EDIT**: `pyproject.toml` — Added `sentence-transformers>=2.6.0` dependency
- **EDIT**: `.env.example` — Documented that Voyage key is optional with local models
- **EDIT**: `README.md` — Updated for provider-based config, removed references to deleted `configs/example.yaml`
- **REMOVED**: `configs/example.yaml` — Replaced by `configs/example-local.yaml`

### Key Design Decisions
| Decision | Why |
|---|---|
| Explicit `provider` field in YAML | Config is source of truth for routing — no reliance on model-name-to-provider lookups at runtime |
| Provider flows through RunParams → orchestrator → embedder/reranker | End-to-end explicit routing; server reload issues can't break dispatch |
| Pydantic model_validator cross-checks provider vs model name | Fast-fail at config parse time with clear error messages |
| `sentence-transformers` for both embedding and reranking | Single package; SentenceTransformer for embeddings, CrossEncoder for reranking |
| `all-MiniLM-L6-v2` as first local model | Well-known, fast, 384-dim, ~23MB — proves the abstraction |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` for local reranking | ~23MB, MS MARCO trained, good quality |
| Separate vector indexes per dimension | Atlas requires exact `numDimensions`; `vector_index_1024` (Voyage) + `vector_index_384` (local) |
| Lazy-load and cache models | First run downloads from HuggingFace; subsequent runs instant |
| `numpy>=2` + `torch>=2.6` override | `sie-sdk` needs NumPy 2; torch 2.2 + NumPy 2 raised `Numpy is not available` |

---

## Slice 8: Dashboard UX Improvements ✅

**Status**: ✅ COMPLETE | **Started**: 2026-05-17 | **Completed**: 2026-05-17 | **Target**: ~2 h

### Goal
Improve dashboard loading UX with progress feedback, add pagination to all screens, and unify page layout with shared components.

### What Changed
- **NEW**: `frontend/src/components/LoadingFeedbackPanel.tsx` — Progress panel with byte-level progress bars and activity feed
- **NEW**: `frontend/src/components/PollingIndicator.tsx` — Subtle "Syncing..." indicator for background polls
- **NEW**: `frontend/src/components/DashboardShell.tsx` — Shared header and navigation across all screens
- **NEW**: `frontend/src/components/AppPageChrome.tsx` — Shared page wrapper (title, back button, actions)
- **NEW**: `frontend/src/services/fetchWithProgress.ts` — ReadableStream-based fetch with byte-level progress tracking
- **NEW**: `VERIFICATION_CHECKLIST.md` — Manual test cases for all loading states and polling behavior
- **EDIT**: `frontend/src/components/ExperimentsScreen.tsx` — Added pagination (10 items/page), integrated LoadingFeedbackPanel and PollingIndicator
- **EDIT**: `frontend/src/components/ExperimentDetailScreen.tsx` — Added pagination to runs table (10 runs/page)
- **EDIT**: `frontend/src/components/SearchExplorerScreen.tsx` — Added pagination to configs (5/page), collapsed sidebar, integrated re-query progress feedback
- **EDIT**: `frontend/src/services/apiClient.ts` — Refactored to use `fetchWithProgress` for streamed downloads
- **EDIT**: `frontend/src/constants.ts` — Added pagination constants (`ITEMS_PER_PAGE_*`)
- **UPDATED**: Screenshots in `docs/images/` — Reflect new UI with pagination and unified chrome

### Key Design Decisions
| Decision | Why |
|---|---|
| Dual loading indicators (panel vs badge) | Full progress panel for initial loads; subtle polling badge for background refreshes — clear state transitions |
| `fetchWithProgress` with ReadableStream | Byte-level progress tracking via `response.body.getReader()` — better UX than spinner for large payloads |
| Shared `DashboardShell` + `AppPageChrome` | Unified header/nav/layout across all screens — consistent UX, easier maintenance, DRY |
| Pagination defaults: 10 (experiments/runs), 5 (configs) | Prevents DOM overload and cognitive fatigue; configs are more verbose so lower per-page count |
| Activity feed in LoadingFeedbackPanel | Shows fetch milestones (start → headers → chunks → complete) — helps debug slow loads |
| `initialLoadDone` flag per screen | Polling indicator only appears after first load completes — avoids visual noise during hydration |

### Acceptance Criteria
- [x] LoadingFeedbackPanel appears during initial loads on all three screens
- [x] PollingIndicator shows during background polls (after initial load)
- [x] Pagination works on ExperimentsScreen (10 items/page)
- [x] Pagination works on ExperimentDetailScreen runs table (10 runs/page)
- [x] Pagination works on SearchExplorerScreen configs (5/page)
- [x] Re-query progress feedback in SearchExplorer when changing query filter
- [x] Unified header/navigation via DashboardShell
- [x] Page titles and back buttons via AppPageChrome
- [x] Screenshots updated to reflect new UI
- [x] Verification checklist created with manual test cases

### Follow-up Enhancements (2026-05-18)

**Extracted reusable progress component** for consistency:
- **NEW**: `frontend/src/components/ExperimentProgressCard.tsx` — Circular progress indicator (default/compact variants)
- **EDIT**: `frontend/src/components/ExperimentDetailScreen.tsx` — Uses `ExperimentProgressCard` (removed inline `ProgressRing`)
- **UPDATED**: Documentation to clarify two progress patterns:
  - `LoadingFeedbackPanel` → Network/API loading (byte-level progress)
  - `ExperimentProgressCard` → Experiment execution (run completion)

**Rationale**: Inline progress visualization in detail screen duplicated logic; extracting to component enables reuse across screens and maintains visual consistency.

---

## Slice 9: Experiment Deletion with Confirmation ✅

**Status**: ✅ COMPLETE | **Started**: 2026-05-19 | **Completed**: 2026-05-19 | **Target**: ~1 h

### Goal
Implement comprehensive experiment deletion with confirmation flows and cascading cleanup across CLI, server, and dashboard.

### What Changed
- **NEW**: `frontend/src/components/ConfirmDeleteModal.tsx` — Confirmation modal with experiment details, warning UI, and deletion statistics display
- **NEW**: `server/api/experiments_shared.py` — Shared delete helpers with cascade deletion logic across all collections
- **EDIT**: `server/api/experiments.py` — Added `DELETE /experiments/{id}` endpoint with `force` query parameter, validation against running experiments
- **EDIT**: `cli/main.py` — Added `delete` command with interactive confirmation prompt and `--force` flag
- **EDIT**: `cli/api_client.py` — Added `delete_experiment()` method for DELETE API calls
- **EDIT**: `frontend/src/components/ExperimentsScreen.tsx` — Added delete button in Actions column, integrated ConfirmDeleteModal, disabled for running experiments
- **EDIT**: `frontend/src/components/ExperimentDetailScreen.tsx` — Added delete button in header actions, integrated ConfirmDeleteModal
- **EDIT**: `frontend/src/services/apiClient.ts` — Added `deleteExperiment()` method with query string support
- **EDIT**: `frontend/src/types/index.ts` — Added `DeleteExperimentResponse` type for deletion statistics
- **EDIT**: `docs/user-guide/cli-reference.md` — Documented `delete` command with examples and use cases
- **EDIT**: `docs/user-guide/troubleshooting.md` — Replaced manual cleanup section with CLI/dashboard delete instructions
- **EDIT**: `CLAUDE.md` — Added delete command to CLI examples and updated key files list

### Key Design Decisions
| Decision | Why |
|---|---|
| Cascade delete across all collections | Prevents orphaned data; removes experiments, run_status, chunks, and results in one operation |
| Confirmation required by default | Deletion is permanent and destructive; explicit confirmation prevents accidental loss |
| `--force` flag for automation | Enables scripted deletion workflows without interactive prompts |
| Block deletion of running experiments | Prevents data corruption; users must cancel experiment first |
| Return deletion statistics | Provides transparency and verification of cascade cleanup |
| ConfirmDeleteModal shows experiment details | Users can verify they're deleting the correct experiment before confirming |
| Shared delete logic in `experiments_shared.py` | DRY principle; both API endpoint and future CLI/admin tools use same logic |

### Acceptance Criteria
- [x] CLI `delete` command with interactive confirmation prompt
- [x] CLI `--force` flag skips confirmation
- [x] DELETE endpoint returns deletion statistics (docs deleted per collection)
- [x] Running experiments cannot be deleted (API returns 400 error)
- [x] Dashboard delete buttons in experiments list and detail screen
- [x] ConfirmDeleteModal shows experiment details and deletion warning
- [x] Delete button disabled for running experiments with tooltip
- [x] Success toast shows deletion statistics
- [x] All pre-commit hooks pass (ruff, mypy, eslint, repo lint, tsc, build); pre-push runs `quality-gates.sh` (full gates) when hooks installed
- [x] Documentation updated (CLI reference, troubleshooting guide)

### Testing Notes
Manually verified:
- CLI delete with and without `--force`
- Dashboard delete from both list and detail screens
- Confirmation modal shows correct experiment details
- Running experiment deletion blocked with error message
- Deletion statistics displayed correctly in CLI and dashboard
- All associated data removed from MongoDB collections

---

## Vector DB Stats + Collapsible Rows + Boot Reconciliation ✅

**Status**: ✅ COMPLETE | **Started**: 2026-05-19 | **Completed**: 2026-05-19 | **Target**: ~1.5 h

### Goal
Surface MongoDB/Atlas storage footprint in the dashboard, improve experiments list UX with collapsible rows, and automatically fix experiments left `running` after server restart or crash.

### What Changed
- **NEW**: `server/core/atlas_storage.py` — Atlas Admin API cluster quota lookup + `dbStats` footprint; manual `MONGODB_STORAGE_LIMIT_MB` override
- **NEW**: `server/core/startup_reconciliation.py` — on boot, mark in-flight runs `interrupted` and recompute experiment status (`partial` / `complete` / `failed`)
- **NEW**: `server/utils/log_throttle.py` — throttle repetitive polling log lines
- **EDIT**: `server/api/experiments_shared.py` — `mongo_get_experiment_db_stats`, `mongo_get_vector_db_stats_grouped`
- **EDIT**: `server/api/experiments.py` — `GET /experiments/vector-db-stats`, `GET /experiments/{id}/db-stats`
- **EDIT**: `server/main.py` — call `reconcile_orphaned_experiments()` in lifespan
- **NEW**: `frontend/src/components/CollapsibleCard.tsx`, `VectorDbStatsPanel.tsx`, `ExperimentVectorDbStatsCard.tsx`
- **NEW**: `frontend/src/utils/experimentStatus.ts` — `summarizeExperimentRuns()` for outcome buckets
- **EDIT**: `frontend/src/components/ExperimentsScreen.tsx` — collapsible list rows, cluster stats panel, list→detail cache handoff
- **EDIT**: `frontend/src/components/ExperimentDetailScreen.tsx` — compact overview metrics (successful / failed / interrupted / not started), status-accurate outcome banners
- **EDIT**: `.env.example` — Atlas Admin API + storage limit vars

### Key Design Decisions
| Decision | Why |
|---|---|
| Reconcile orphans on every boot (not gated by `RECOVER_ON_BOOT`) | Status correction is safe and idempotent; retry remains opt-in via Slice 10 |
| `partial` when sweep incomplete | Distinguishes “41/90 complete + 48 never started” from green `complete` |
| Atlas quota via Admin API with manual fallback | M0 tier limits vary; hardcoded 512 MB was misleading |
| Outcome metrics from `run_status` phases | `run_count - failed_count` lied when runs never started |
| Collapsible state in `localStorage` | Per-panel persistence without server round-trips |

### Acceptance Criteria
- [x] `GET /experiments/vector-db-stats` returns grouped cluster stats
- [x] `GET /experiments/{id}/db-stats` returns per-experiment chunk/storage breakdown
- [x] Experiments list shows collapsible rows + vector DB stats panel
- [x] Experiment detail shows run-outcome buckets that sum to total runs
- [x] Partial experiments show “Sweep Incomplete” — not green success banner
- [x] Server boot reconciles stale `running` experiments to terminal status
- [x] Pre-commit hooks pass

---

## Voyage Sweep UX + Atlas Tier Specs ✅

**Status**: ✅ COMPLETE | **Started**: 2026-05-23 | **Completed**: 2026-05-23 | **Target**: ~1 h

### Goal
Fix misleading elapsed/duration times on long Voyage sweeps, surface Atlas cluster tier metadata in the dashboard, and polish experiment detail UX for running/paused sweeps.

### What Changed
- **EDIT**: `server/db/atlas.py` — PyMongo client `tz_aware=True`, `tzinfo=timezone.utc`
- **EDIT**: `server/core/orchestrator.py` — `started_at` set when first run begins; all timestamps timezone-aware UTC
- **EDIT**: `server/api/experiments_shared.py` — timezone-aware cancel/pause; db-stats includes `cluster_tier`, `cluster_tier_type`, `cluster_provider`, `cluster_region`
- **EDIT**: `server/core/atlas_storage.py` — `resolve_tier_specs()` from Atlas Admin API; shared-tier storage fallbacks (M0/M2/M5)
- **EDIT**: `frontend/src/components/ExperimentDetailScreen.tsx` — elapsed + ETA on progress card; duration shows — while running/paused; controls only in header
- **EDIT**: `frontend/src/components/VectorDbStatsPanel.tsx` — tier, cloud provider, region display
- **EDIT**: `.env.example` — Tier 1 rate limits as commented block above free-tier defaults
- **EDIT**: `configs/mongodb/example-voyage.yaml` — default to `voyage-3.5-lite` for storage-friendly sweeps

### Key Design Decisions
| Decision | Why |
|---|---|
| `datetime.now(timezone.utc)` everywhere | JSON `Z` suffix; browsers parse elapsed correctly |
| `started_at` on first run, not submission | ETA/duration reflect actual pipeline time |
| Atlas tier via `resolve_tier_specs()` | Reuses Admin API; RAM/vCPU/cost not exposed by Atlas |
| ETA with 1% margin | Small buffer on linear projection |
| Single control button location (header) | Removes duplicate pause/resume/cancel from progress and paused banners |

### Acceptance Criteria
- [x] Running experiment progress shows elapsed + ETA after first run completes
- [x] Duration stat shows — while running or paused
- [x] Vector DB stats panel shows tier/provider/region when Atlas API configured
- [x] New timestamps are timezone-aware UTC
- [x] Debug scripts removed (`test_atlas_api.py`, `test_time_calc.html`, one-off migration scripts)
- [x] Documentation updated

---

## Dashboard Polling + API Responsiveness ✅

**Status**: ✅ COMPLETE | **Started**: 2026-05-19 | **Completed**: 2026-05-23 | **Target**: ~1 h

### Goal
Keep the dashboard responsive during active sweeps and expensive Mongo aggregations; document per-screen poll intervals.

### What Changed
- **NEW**: `server/core/executors.py` — `SWEEP_EXECUTOR` + `HEAVY_READ_EXECUTOR` thread pools
- **EDIT**: `server/api/experiments.py` — sweeps and db-stats on dedicated pools; batched vector-db-stats aggregations
- **EDIT**: `frontend/src/constants.ts` — `EXPERIMENTS_POLL_MS` (2 s), `VECTOR_DB_STATS_POLL_MS` (60 s), `EXPLORE_POLL_MS` (15 s); fetch timeouts 30 s / 90 s
- **EDIT**: `frontend/src/components/ExperimentsScreen.tsx` — decoupled list vs stats polling
- **EDIT**: `frontend/src/components/SearchExplorerScreen.tsx` — 15 s explore poll while experiment running
- **EDIT**: `frontend/src/components/PollingIndicator.tsx` — `showDelayMs` / `minVisibleMs` to reduce sync-badge flicker
- **EDIT**: `docs/user-guide/dashboard-guide.md`, `docs/contributor-guide/architecture.md`

### Acceptance Criteria
- [x] Experiment list loads within a few seconds during an active sweep
- [x] Vector DB stats may lag but do not block the list
- [x] Search Explorer refreshes every 15 s while sweep is running
- [x] Dashboard guide polling table matches `constants.ts`

---

## Slice 6: Additional Chunkers + Retrieval Methods ✅

**Status**: ✅ COMPLETE | **Started**: 2026-05-17 | **Completed**: 2026-05-17 | **Target**: ~45 min

### Goal
Implement the 4 stubbed chunkers (fixed, token, sentence, semantic), add sparse/hybrid retrieval, create 5 new example configs covering every advertised feature.

### What Changed
- **IMPL**: `server/core/chunkers/fixed.py` — character-window slicing with configurable overlap
- **IMPL**: `server/core/chunkers/token.py` — LangChain `TokenTextSplitter` (cl100k_base encoding)
- **IMPL**: `server/core/chunkers/sentence.py` — NLTK `sent_tokenize` with character-budget grouping and overlap
- **IMPL**: `server/core/chunkers/semantic.py` — sentence-transformers cosine similarity grouping; chunk_size as hard cap; overlap ignored (semantic boundaries decide splits)
- **EDIT**: `server/core/retriever.py` — added `sparse_search()` (Atlas $search BM25), `hybrid_search()` (RRF merge, k=60), `search()` dispatcher, `_to_search_results()` helper
- **EDIT**: `server/core/orchestrator.py` — use `search()` dispatcher; conditionally embed query (only for dense/hybrid); import `RetrievalMethod`
- **NEW** *(later replaced — see config reorganisation below)*: `configs/example-voyage-all-models.yaml`, `example-chunking-methods.yaml`, `example-retrieval-methods.yaml`, `example-full-sweep-local.yaml`, `example-full-sweep-voyage.yaml`
- **EDIT**: `docs/user-guide/configuration.md` — Config File Index table, fixed hybrid description
- **EDIT**: `CLAUDE.local.md` — Atlas Full Text Search index setup
- **EDIT**: `README.md` — updated Quick Start config references

### Key Design Decisions
| Decision | Why |
|---|---|
| semantic chunker always uses `all-MiniLM-L6-v2` | Provider-agnostic chunking; keeps chunking independent of embedding config |
| semantic `overlap` param ignored | Semantic boundary is the split signal; character overlap would break topic coherence |
| RRF k=60 | Standard value from original RRF paper; softens rank-1 advantage |
| sparse/hybrid require Atlas Full Text Search index | Atlas $search is the BM25 engine; documented as manual prerequisite |
| `query_embedding` optional in `search()` dispatcher | Sparse doesn't need embedding; avoids wasted API call |

---

## Deferred

- Parallel sweep concurrency *(Slice 16 — [`docs/plan/slices/SLICE-16-PARALLEL-SWEEP-RUNS.md`](SLICE-16-PARALLEL-SWEEP-RUNS.md))*
- All SHOULD/COULD slices
- Error handling (basic only in Slice 1)
- Logging structure (prints for now)
- Type safety everywhere (pragmatic shortcuts OK)

---

## Decision Log

| Date | Slice | Decision | Why |
|------|-------|----------|-----|
| 2026-07-28 | 45 | Scripts theme folders (`ci`/`docker`/`release`/`security`) + flat shims — DECISIONS #159 | Leave scripts flat / delete shims immediately |
| 2026-07-28 | 45 | FE shared test helpers (`frontend/src/test/helpers/*`) — DECISIONS #158 | Leave duplicated builders / invent factories only for new tests |
| 2026-07-28 | 45 | FE components folder split (`screens`/`chrome`/`experiment`/`stats`) — DECISIONS #157 | Leave flat components/ / move screens only |
| 2026-07-28 | 45 | FE screen SLAP extracts (detail hook + chrome, list labels, explore panels) — DECISIONS #156 | Folder-move screens first / leave god screens |
| 2026-07-28 | 45 | FE shared primitives extracted (Pagination/StatTile/feed/completionReason) — DECISIONS #155 | Defer until after components folder split / leave Rule-of-3 copies |
| 2026-07-28 | 45 | Mirror `tests/` under server/cli/scripts + split Slice 16 mega-suite; `repo_root_from()` for nested path depth — DECISIONS #154 | Keep flat tests / invent `tests/unit/` only |
| 2026-07-27 | 44 | Coverage floor: Before-Check lines 50.18% → after Should ~64.75%; thresholds ratcheted to lines≥64 / branches≥58 / functions≥61 / statements≥62 — DECISIONS #138; mutation waived | Invent floor / keep ungated bare vitest |
| 2026-07-27 | 45 | Land `core/guards/` first with shim re-exports; retarget test patches to canonical paths | Keep sys.modules alias / big-bang rewrite all server.core imports |
| 2026-07-27 | 45 | Park FE Code Complete craft debt on Slice 45 Should/Could (shared UI primitives, screen SLAP, shared test helpers; Won't: higher floors / TanStack / mutation) — expand estimate (later raised with BE) | Bundle into Slice 44 coverage PR / invent Slice 44B |
| 2026-07-27 | coverage | Shared FE+BE floors **#142** — FE 95/90/95/95; BE **95/90/n/a/95** via `fail_under=95` + `scripts/ci/check_backend_coverage_floors.py` (TOTAL ≈97.7%) | Keep BE at 90 / soft 92/85 policy |
| 2026-07-27 | coverage | Fair floors **#141** — FE 95/90/95/95; BE fail_under=90 + policy 92/85/n/a/90 | Keep flat FE 90 / invent BE branch≥90 without tests |
| 2026-07-27 | coverage | Uniform **≥90%** product floor — BE `--cov-fail-under=90` + FE thresholds 90/90/90/90 (DECISIONS #140); postgres module gate stays 95 | Keep FE 95 / BE 80 asymmetry |
| 2026-07-27 | 44 | Phase B reopen: FE gate → **≥95%** lines/stmts/funcs + **≥90%** branches (option 1; reopen 44 not 44B) — DECISIONS #139 | Keep Phase A 64% as permanent bar / new Slice 44B |
| 2026-07-27 | 44 | Phase B mop-up ✅ — measured 98.21/92.89/99.7/99.61; 252 tests / 20 files; former near-miss modules (ExperimentsScreen branches, Detail/ControlButtons/devLog) ≥95/90 | Leave per-file gaps under floor / lower thresholds |
| 2026-07-27 | 44 | Phase B ✅ — measured 96.84/90.96/97.92/98.85 (stmts/br/fn/lines); thresholds 95/90/95/95 + `all: true`; 229 tests / 20 files | Stop at Phase A floor / invent literal 100% without exclusions |
| 2026-07-27 | 44/45 | nw-review remediations APPLIED (#137) — 44 DoR APPROVED for execution; 45 architect APPROVED; coverage Must still PLANNED | Leave review NEEDS_REVISION / CONDITIONAL without stub edits |
| 2026-07-27 | sync-docs | CHANGELOG / CLAUDE / development / AGENTS / ARCHITECTURE stub aligned to theme map (**IMPLEMENTED**); coverage gate still **PROPOSED** — DECISIONS #136 | Agent + release surfaces lagged plan-tracker updates |
| 2026-07-27 | 44/45 | Structure taxonomy audit = Slice 44 Should (§3); filesystem moves deferred to Slice 45 Could — DECISIONS #135; theme map + canvas + SLICE-45 stub published | Bundle audit into 44 hygiene; keep SLAP — moves are a different abstraction |
| 2026-07-26 | 38 | ADR-004 Accepted (dual-backend Postgres/Supabase + Mongo); ADR-003 Superseded; default remains mongodb until local comparison — DECISIONS #127 | Flip default without quality gates |
| 2026-07-26 | 38 | Parked **all** non-100%-Yes Before/After items onto Slice 43 residuals (#126); 38 After-Checks = local comparison + ADR + no-flip (#130) + slice-38.json + mutation waive + PROGRESS/TRAIL/CHANGELOG only | Leave nuanced/sync-docs items as Slice 38 COMPLETE blockers |
| 2026-07-26 | 38 | Parked unrealistic Before/After gates onto Slice 43 residuals (hosted production-claim matrix, PRD §9/docs audit, 100% shell coverage, Graphiti/date spelling); Slice 38 COMPLETE gates on local dual-backend only — DECISIONS #125 | Keep hosted matrix as Slice 38 COMPLETE blocker |
| 2026-07-26 | 38 | Accounted branch work: remediations (#114–#119) + Atlas Local `8.3.3` / pgvector `0.8.5-pg16` pins (#120) + FCV/invalid-RS recovery (#121); comparison/ADR/flip still open | SLICE-38 “Landed on this branch” table; PR #118 checkpoint only |
| 2026-07-26 | 38 | Path A Resume — review remediations landed (Mongo export + placeholder reject); no silent default change without explicit decision | BLOCKER-1/4 from nw-platform-architect-reviewer; #119 remediations; fail-safe reading corrected by #129 |
| 2026-07-26 | 38 | **Won't** default flip (#130) — code default stays `mongodb` permanently; remove flip gate/residual; dual-backend is operator select only | Keep a deferred/optional default-flip commitment or post-flip smoke residual |
| 2026-07-26 | 38 | Slice 38 ✅ COMPLETE — ADR-004 + comparison + CI; default stays `mongodb` with no flip (#130) | Keep Slice 38 open waiting on a default flip |
| 2026-07-26 | 38 | Local dual-backend comparison VERIFIED — mirrored 120-run grids; QUERYING latency ≤2× PASS; top-3 overlap recorded informational (dense 92.9% / overall 45.7%); mismatch OK under #129 | Treat cross-DB rank mismatch as cutover FAIL / require a default flip |
| 2026-07-26 | 38 | Mongo ⟂ Postgres are independent backends — neither is a fail-safe for the other; comparison = quality/latency evidence for operator A/B — DECISIONS #129 | Read “fail-closed keep mongodb” as Mongo protecting Postgres |
| 2026-07-26 | 37 | sync-docs (post nw-review): CLAUDE/development shellcheck scope + unit counts 317/16; DECISIONS #109 generic Unknown option retained, #110 start-services shellcheck gate; gate-evidence follow_ups for resolver isolation — evidence **VERIFIED** | Post-review quality-gate + quantitative claims were stale vs measured truth |
| 2026-07-26 | 37 | sync-docs: remove `--local`/`-l`/`--postgres`/`-p` from current operator/agent surfaces; DECISIONS #108; PRD operator contract + `.env.example` + skip hints use canonical flags only — evidence **IMPLEMENTED** (unit reject) + **VERIFIED** (resolver smoke exit 2) | Short flags now fail as unknown options; leaving them in setup/checklist/test skip copy would mislead |
| 2026-07-26 | 37 | `SUPABASE_URI` optional alias for `DATABASE_URL` + live hosted Supabase smoke PASSED (`49c23d41-…`, `storage_mode=postgres-cloud`) — DECISIONS #107 | User requested product-named URI + real Path B verification; reverses earlier Won't on URI aliases (still no `POSTGRES_URI`) |
| 2026-07-26 | 37 | Slice 37 → ✅ COMPLETE — Docker VM DiskFull cleared (~28GB prune); matching one-run smoke `1903dc76-…` complete with `storage_mode=postgres-local`; mismatch 422 live; hosted Path B initially documented skip (later upgraded — see #107); `gate-evidence/slice-37.json` | Verify-slice was BLOCKED only on volume/VM full, not product defect; After-Checks closed |
| 2026-07-26 | 37 | sync-docs: operator + agent + release surfaces aligned to four-flag vocabulary, supabase→postgres normalize, config↔server 422, Engine × Location — evidence **IMPLEMENTED** (unit); VERIFIED withheld pending live four-mode / gate-evidence | `/sync-docs` after Must+Should code; stale `--local`/`--postgres` / supabase-label claims would mislead operators |
| 2026-07-26 | 37 | Captured pending vocabulary into SLICE-37: product-wording map (Atlas cloud/Local, Supabase-hosted, local pgvector), `configuration.md` Engine × Location subsection, Should-rename `collect_search_index_snapshot` | Informational Qs from post-36 review must not stay only in chat; operator docs must never treat Atlas as cloud-only without Local qualifier |
| 2026-07-26 | 37 | Path A Resume — TRAIL/PROGRESS/SLICE-37 → 🔨; platform review CONDITIONALLY APPROVED after 422/post-start templates | User asked start Slice 37 after enhanced-flow-planner + nw review |
| 2026-07-26 | 37 | Drift sync vs main (36/43): foundations table; bare `.env` STORAGE_BACKEND Must; Won't URI aliases + example-cloud.yaml; Should CLI/pause/boot tests; distinct config 422 vs catalog 422; execution order 1–6 | enhanced-flow-planner continuation before execute; Gate Status no longer “wait for 36 merge” |
| 2026-07-26 | 37 | Absorbed Slice 36 close leftovers into SLICE-37 §Absorbed (flags, compose spelling, supabase label/`vector_db_id`, axes docs); configs folder rename non-blocker | Keeps Slice 36 COMPLETE without open vocabulary After-Checks; operator DX slice already owned the flag grid |
| 2026-07-26 | 36 | Slice 36 → ✅ COMPLETE — live `/healthz` `storage_mode=postgres-local`; vector-db-stats four-value tokens; mutation waived DECISIONS #101; `gate-evidence/slice-36.json` | Runtime VERIFIED after compose rebuild; YAML `database_provider: supabase` and compose `local-postgres` remain Slice 37 vocabulary leftovers |
| 2026-07-26 | 36 | sync-docs: `/healthz` `storage_mode` + Postgres preflight documented as IMPLEMENTED across cli-reference, troubleshooting, postgres-setup, architecture, development, local-environment, CLAUDE.md, AGENTS.md, CHANGELOG | Public 422 contract and health body changed, so user + agent surfaces had to move in the same slice; VERIFIED is withheld until the live dashboard smoke on Postgres runs |
| 2026-07-26 | 36 | Postgres preflight extends `search_index_plan.py` + `search_index_guard.py` with a catalog-introspection branch — no `postgres_index_guard.py`, no `IndexBackend` Protocol | Postgres has no Atlas Admin API, quota, or reconcile step; a second module (or a Protocol for two known backends) would add indirection without a third implementation to justify it (YAGNI; supersedes the IndexBackend idea deferred from #110) |
| 2026-07-26 | 36 | Four-value `storage_mode` (`mongodb-local` \| `mongodb-cloud` \| `postgres-local` \| `postgres-cloud`) on `/healthz` and db-stats; `supabase` / `local-postgres` kept as import-level aliases only, never emitted | Mode strings must equal the Slice 37 flag names so operators read one vocabulary end to end; aliases keep in-flight callers compiling without leaking the old words to users |
| 2026-07-26 | 43 | Close Slice 43 after the recommended Supabase config completed on local Postgres: experiment `dd107437-be69-4d62-a549-003b743ed841`, 16/16 runs complete, all four retriever types produced result rows | This supplies the missing operator-path evidence without overstating hosted Supabase verification; hosted smoke and config↔server rejection remain owned by Slice 37 |
| 2026-07-26 | naming | Canonical `STORAGE_BACKEND=mongodb` (legacy alias `mongo` → normalize); health `storage_backend` key matches; `database_provider` already used `mongodb` | Operator/docs/env were split between short `mongo` and label `mongodb`; Slice 37 already planned the rename — land the token now with alias so existing `.env` values keep working |
| 2026-07-26 | 43 | sync-docs: §2–§5 operator-doc acceptance marked IMPLEMENTED; slice status → 🔨; §1 live smoke remains the DoD gate | Docs rewritten + `mongodb` token landed; completion still requires recorded supabase CLI smoke |
| 2026-07-26 | 43 | Collated deferred/open items from PR bodies #109–#113 into SLICE-43 §6 (in-scope vs elsewhere-owned) | Bodies cited: #113 `_id`/provider/ADR-004 deferrals; #112 SPLADE + Slice 38 equivalence; #111 config split, HNSW recall, operator contract→37; #110 32C/32B open gates + IndexBackend→36; #109 Gap 8→41B/41C — code-review-graph bot tables excluded |
| 2026-07-26 | 43 | Recorded Mongo↔Postgres env asymmetry as Slice 43 residual §3 (document now; aliases/infer → 37) | `MONGODB_URI` (+ default mongo) vs `DATABASE_URL` + required `STORAGE_BACKEND=postgres`; folder/YAML say `supabase` while runtime token is `postgres`; no `SUPABASE_URI` — operator FAQ from 2026-07-26 |
| 2026-07-26 | 43 | New Could slice for supabase example-config live smoke + operator QoL; does not block 36–38 | Sanity check found configs structurally correct; residual risks are unverified E2E, env-vs-YAML confusion, and hosted large-grid guidance — SPLADE→22, 422 mismatch→37, quality matrix→38 |
| 2026-07-26 | hygiene | Experiment detail resolves a storage backend only when it must load runs or persist reconciliation; Bayesian summary is built either way | `ensure_storage_ready()` raises without `MONGODB_URI`, so the unit tier failed in CI while passing locally off `.env`; the detail path already had its run rows and needed no backend |
| 2026-07-26 | hygiene | Unit tier ignores live DB suites; session-scoped `live_postgres_pool` + schema advisory lock for live jobs | Interleaved contract+dense/sparse fixtures called `close_pool()` per test → DDL deadlocks / FK races; CI unit job must stay DB-free while postgres/mongo jobs own live coverage |
| 2026-07-26 | hygiene | Boundary hygiene, no folder moves: rename agnostic `mongo_*` API helpers to port verbs; `retriever.py` → `retriever_mongo.py`; Mongo-only docstring markers in place | Ports already load-bearing; physical `server/db/mongo/` split would collide with open 32/33 work; naming was the real leak |
| 2026-07-26 | hygiene | Shared live `StorageBackend` contract suite (`tests/contract/`) + `tests/conftest.py` skip helpers; CI `mongo-integration` job (Atlas Local) mirrors `postgres-integration` | Mongo acceptance was mocked, Postgres was live-only — nothing asserted both adapters answer the port identically (Slice 38 prerequisite) |
| 2026-07-26 | hygiene | Documented, not closed: `_id` leak (Postgres synthesises it); `database_provider` YAML is metadata (Slice 37 owns 422 mismatch); configs/mongodb vs supabase near-duplicates (managed by `test_config_examples`); quality-gates omit postgres coverage (32B); ADR-004 missing (38); no supabase screenshots | Confirmed scope — close inside existing slices, not a parallel restructure |
| 2026-07-26 | hygiene | `ensure_storage_ready()` at lifespan + store_factory; CLI `indexes` exits for non-mongo; `pre-push-gates` still `unset STORAGE_BACKEND` (re-examine later) | Fail boot with one URI message; Atlas CLI must not run against Postgres; unit suite still assumes mongo ambient backend |
| 2026-07-26 | 33–38 | Operator vocabulary is `--<db-type>-local` / `--<db-type>-cloud` (`mongodb` \| `postgres`); mode values match flags; single `postgres-setup.md` SSOT; Slice 37 owns rename + hosted ensure_env + **low-friction two-command switching** + config↔server 422 gate | Symmetric grid is guessable from either axis; today's two booleans cannot express hosted Postgres; YAML `database_provider` is metadata today and can silently disagree with `STORAGE_BACKEND` — reject mismatch before writes; same postgres YAML works local and cloud |
| 2026-07-25 | 33 | Hybrid schema: promote queryable fields to columns, keep the rest in a `doc` JSONB column (`experiments`, `run_status`, `results`); `chunks` fully columnar | `StorageBackend` is dict-in/dict-out over documents whose shape is owned by Pydantic models and sweep metadata; JSONB preserves them without a migration per added field, while promoted columns keep filters and sorts indexable. Chunks are columnar because retrieval indexes them directly |
| 2026-07-25 | 33 | Do not store Mongo's `_id`; synthesise it from the primary key on the two reads that use it (`find_experiment_by_id`, `find_running_experiments`) | `_id` is a Mongo implementation detail, but boot reconciliation reads `doc["_id"]`; deriving it avoids persisting the same value twice and keeps the port contract identical across adapters |
| 2026-07-25 | 33 | Postgres finders return whole documents where Mongo applies projections | Verified every call site reads named keys via `.get()`, so a superset is safe; projections are a Mongo bandwidth optimisation, not part of the `StorageBackend` contract |
| 2026-07-25 | 33 | Extract shared stats maths into `server/db/stats_common.py`; `mongo_stats` and `postgres_stats` supply only backend identity and their own aggregation SQL | Both adapters must produce byte-identical db-stats dict shapes for one dashboard; duplicating the assembly maths would let them drift silently |
| 2026-07-25 | 33 | Host port **5433** for the local pgvector container, not 5432 | A developer's own Postgres on 5432 keeps working; avoids a port conflict that would look like a broken container |
| 2026-07-25 | 33 | Integration tests hit a live pgvector and skip when absent; CI sets `RAG_REQUIRE_POSTGRES=1` to turn absence into failure | The SQL, JSONB/datetime fidelity, and FK cascade are exactly what mocks would hide; without the CI flag a broken service container would report green forever |
| 2026-07-25 | 33 | Widen `DatabaseProvider` to `mongodb \| postgres \| supabase`; both Postgres values route to one adapter | Configs must be able to declare the backend, and db-stats labels the cluster differently for local vs hosted — but the SQL is identical, so a second adapter would be duplication |
| 2026-07-25 | 33 | No `embedding_sparse` column yet; unsupported widths raise a `ValueError` naming Slice 35 | PRD lists sparse storage as optional in 33 and Slice 35 owns sparse/hybrid; failing loudly beats silently dropping SPLADE vectors (YAGNI without the silent-loss risk) |
| 2026-07-25 | 34 | Set `hnsw.iterative_scan = strict_order` on every pooled Postgres connection; warn and continue on pgvector < 0.8 | HNSW cannot filter inside the index, so the mandatory `experiment_id`/`embedding_model`/`run_id` filters post-filter its candidate set. Measured with iterative scan off: a `LIMIT 20` query returned **3 rows** (39 removed by filter). Silent truncation would change the scores this tool exists to compare. Two tests pin it; reverting the setting drops recall to 1 of 20 and fails them |
| 2026-07-25 | 34 | Score dense hits as `1 - cosine_distance / 2` rather than passing pgvector distance through | Atlas `$vectorSearch` reports `(1 + cosine) / 2`; identical retrieval quality must produce identical numbers or the Slice 38 backend comparison is meaningless. Pinned by asserting 1.0 for an identical vector and 0.5 for an orthogonal one |
| 2026-07-25 | 34 | Atlas search-index preflight short-circuits when `STORAGE_BACKEND != mongo` (`preflight_not_applicable()`) | Every step of the guard talks to Atlas, so a Postgres sweep would open a MongoDB connection it never uses — and fail outright where no `MONGODB_URI` exists. Postgres declares its HNSW indexes in `schema.sql`, so there is no quota to negotiate |
| 2026-07-25 | 34 | Sparse/hybrid on Postgres raise `NotImplementedError` naming Slice 35 instead of degrading to dense | A sweep that quietly changed retrieval method would invalidate its own comparison; the error names `dense` and `STORAGE_BACKEND=mongo` as working alternatives |
| 2026-07-25 | 34 | Cross-model isolation test uses a rival model at the *same* 384 width in the *same* run | First version used models of different widths, so the `IS NOT NULL` column guard masked a removed `embedding_model` filter — the mutant survived. Same-width, same-run noise is the only shape that can actually fail |
| 2026-07-25 | 34 | Keep exact KNN (planner's btree+sort choice); defer `chunks` partitioning by `experiment_id` | Exact is correct and fast at current volumes, and it is what makes the Mongo comparison trustworthy. Partition-per-experiment (filter-free HNSW per partition) is the scale-up path if sweeps outgrow exact search — YAGNI today |
| 2026-07-25 | ops | Keep `numpy>=2` (sie-sdk); override `torch>=2.6`; drop Intel-mac from uv environments | `numpy<2` conflicts with sie-sdk; torch 2.2 + numpy 2.5 → `Numpy is not available`; torch≥2.6 has no x86_64 Darwin wheels |
| 2026-07-25 | 32C | Added Must sub-slice 32C (review remediation); keep 32B gate-only; order **32 → 32C → 32B → 33** | Craft/architecture nw-review BLOCKERs (adapter split, port schemas, index deferral, checklist hygiene) are a separate unit from verification gates; 32B stays medium (~1–2 h) |
| 2026-07-26 | 35 | No sparsevec; tsvector keyword sparse; RRF SQL CTEs rrf_k=60; Supabase-mode Host/Table labels | SPLADE storage deferred; Lucene drift → Slice 38 CONDITIONAL; copy hygiene (#90) |
| 2026-07-26 | 35 | Slice 35 → ✅ COMPLETE — verify-slice VERIFIED; quality gates 11/11 (backend 314 @ 96.8% scoped, frontend 12, audits 0 high); mutation waived to nightly CI | All GWT scenarios tested on live pgvector; production wiring reachable; no local backend mutation runner (DECISIONS #95) |
| 2026-07-25 | 32B | Split remaining Slice 32 After-Checks into Must sub-slice 32B (gate closure); Slice 33 Depends on → 32B | Implementation is on PR #110; coverage/mutation/full-gates/nw-review/tracker close-out are a distinct verifiable unit and must not block reading the Protocol work as “done”; keeps 33 gated on COMPLETE evidence |
| 2026-07-25 | 32 | Keep `atlas.py` as connection singleton; put CRUD/search behind `StorageBackend`/`RetrieverBackend` in `mongo_store.py`; factory selects by `STORAGE_BACKEND` | Dual-backend seam for Postgres (33+) without rewriting call sites; Protocol enforces cross-adapter contract (PRD Decision #10 exception) |
| 2026-07-25 | 42 | Renamed `docker` path-filter → `docker_files` (only `docker/**` + `docker-compose*.yml`); docker job trigger expressed as `docker_files \|\| backend \|\| frontend` at job `if:` level | Removes 5 redundant path lines (server/**, cli/**, frontend/**, pyproject.toml, uv.lock) that duplicated `backend` and `frontend` filters; `deps` filter left unchanged — its overlap with backend is load-bearing precision (dep-audit should not fire on source-only edits) |
| 2026-07-25 | 42 | `overrides.brace-expansion=5.0.8` in `package.json` instead of ESLint upgrade | ESLint 8→9/10 requires flat config migration (`.eslintrc.cjs` → `eslint.config.*`); brace-expansion@5 is API-compatible drop-in; npm audit now 0 vulnerabilities without touching ESLint config |
| 2026-07-25 | 42 | Moved `nightly-dependency-audit` + `nightly-full-secrets-scan` from `ci.yml` → `nightly.yml` | Schedule-only jobs in a PR/push workflow; moving restores clear mental model (ci.yml = PR gates, nightly.yml = deep sweeps); `nightly.yml` already has `workflow_dispatch` for manual runs |
| 2026-07-09 | 32–38 | nw-review edits applied | Behavioral ACs; equivalence gates; PRD SSOT; experiment_id contract; Supabase naming; Slice 27→36 |
| 2026-07-18 | 39 | Added demo-ready dashboard polish | User prioritised an impressive list-to-detail presentation; strict ≤2 h visual-only interrupt before resuming Slice 32 |
| 2026-07-18 | 39 | Adopted results-led decision storytelling | ARC-AGI-3 study informed purpose → results → trace hierarchy only; analytical views stay with Slices 30/11/31 and regression budgets protect behavior |
| 2026-07-18 | 39 | Corrected contrast through shared tokens and an explicit polling-indicator tone | Live WCAG inspection found muted and semantic text failures; the smallest presentation-only fix preserved polling cadence and component behavior |
| 2026-07-07 | 22 | Reclassified Slice 22 Should → Must | nw-review: Slice 22 delivers PCTO-critical score/reranking + best-config; both halves of SIE must be Must |
| 2026-07-07 | 30 | Added Slice 30 (Search Explorer UX) | Assessment found 4 untracked UX issues; bundled as Could/~2h |
| 2026-07-07 | 31 | Added Slice 31 (Experiment list filter) | Assessment found navigability gap at scale; Should/~2h |
| 2026-07-06 | 29 | Include padding in `_run_config_key()` tuple after overlap; default 0 for legacy runs | PR #48 added sweep dimension but ranked configs merged runs differing only by padding |
| 2026-06-29 | 21 | Officially close Slice 21; populate HANDOFF.md + update TRAIL.md | All acceptance criteria met; SIE_ENDPOINT rename + preflight + batching refinements landed post-completion |
| 2026-06-29 | 21 | Expand `example-mongodb-sie.yaml` to full chunking/retriever grid + 3 SIE models | Parity with local/voyage examples; bge-m3/stella-v5/splade-v3 are registry top tier |
| 2026-06-29 | 25B | `./start-services.sh --local` single-command switching; cloud URI validation skipped for local mode | Friction after Slice 25: long compose command, manual URI copy-paste, no "switch back" guidance |
| 2026-06-30 | 25/25B | `mongo_client_kwargs()` — TLS only for cloud Atlas URIs | Local `mongodb://` connections failed with SSL handshake when `tlsCAFile` was always set |
| 2026-06-30 | 25B | Compose `--profile` before `up`, not in `up` args | `start-services.sh --local` failed with `unknown flag: --profile` |
| 2026-06-29 | 25B | Consolidate `local-atlas.sh` + dual setup docs into `start-services.sh mongodb` + `mongodb-setup.md` | Single entry point for cloud/local; compose overlay replaced by env-var overrides in `docker-compose.yml` |
| 2026-06-29 | 25 | Implemented `mongodb-atlas-local` as opt-in local backend via `local-atlas` compose profile | Atlas M0 free-tier 500 MB limit hit; local Atlas image supports `$vectorSearch` + `$search` with identical syntax — zero code changes in retriever/indexes; `bootstrap_indexes()` auto-provisions all search indexes for local URI |
| 2026-06-29 | — | Investigating `mongodb/mongodb-atlas-local` Docker image as replacement for Atlas cloud | Atlas M0 free-tier 500 MB limit hit; local Atlas image supports `$vectorSearch` + `$search` with identical syntax — zero code changes required in retriever/indexes |
| 2026-05-27 | 20 | Scoped coverage 80% on four unit-tested modules | Baseline-first (83.6%); whole-repo 28% would force gate off or block merges |
| 2026-05-27 | 20 | pip-audit ML ignores via scripts/pip-audit.sh | torch/transformers CVEs need major sentence-transformers bump — separate slice |
| 2026-05-27 | 20 | Extend pre-commit, not Husky | Python repo already on pre-commit; avoids dual hook systems |
| 2026-05-27 | 20 | Branch chore/slice-20-toolchain-hardening from main | Independent of code-review-graph branch; focused PR |
| 2026-05-02 | 1 | pypdf for PDF parsing | Simpler than pdfminer.six, sufficient for text extraction |
| 2026-05-02 | 1 | voyage-3.5-lite only | Cheapest Voyage model, add others in Slice 7 |
| 2026-05-02 | 1 | RECURSIVE chunker only | Most common method, defer others to Slice 6 |
| 2026-05-02 | 1 | BackgroundTasks not Celery | No queue infrastructure needed for MVP |
| 2026-05-02 | 1 | Tailwind local install | No CDN per spec; postcss + autoprefixer for build pipeline |
| 2026-05-02 | 1 | Hand-mirror TS types | No codegen (typeshare/quicktype); 5 types + 3 enums manageable |
| 2026-05-02 | 1 | Hardcoded query in Slice 1 | Defer persona JSON parsing to Slice 5 for skateboard speed |
| 2026-05-02 | 1 | Atlas vector index manual | Pymongo doesn't support vector index creation; requires Atlas UI |
| 2026-05-02 | 1 | Placeholder chunkers | Create stub files with NotImplementedError to avoid import errors |
| 2026-05-02 | 7 | sentence-transformers for local models | Same package provides SentenceTransformer + CrossEncoder; no extra dep |
| 2026-05-02 | 7 | Explicit `provider` field in YAML config | Config drives routing end-to-end; eliminates runtime model-name lookup failures |
| 2026-05-02 | 7 | Provider passed through RunParams → orchestrator → embedder/reranker | Explicit routing; stale server code can't misroute to wrong provider |
| 2026-05-02 | 7 | Separate vector indexes per dimension | Atlas requires exact numDimensions match; vector_index_1024 + vector_index_384 |
| 2026-05-02 | 7 | all-MiniLM-L6-v2 as first local model | Well-known, fast, 384-dim, proves the abstraction |
| 2026-05-02 | 7 | numpy<2 compatibility pin | torch compiled against NumPy 1.x ABI; 2.x breaks with _ARRAY_API errors |
| 2026-05-17 | 6 | semantic chunker always uses all-MiniLM-L6-v2 | Provider-agnostic chunking; chunking and embedding phases remain independent |
| 2026-05-17 | 6 | RRF k=60 for hybrid retrieval | Standard value from original RRF paper; robust default, smooths rank-1 outliers |
| 2026-05-17 | 6 | sparse/hybrid require text_search_index | Atlas $search is the BM25 engine; full-text + vector indexes can coexist on same collection |
| 2026-05-17 | 6 | query_embedding optional in search() dispatcher | Avoids embedding API call for sparse retrieval runs |
| 2026-05-17 | — | Reorganise configs: 1 file per DB×provider | Replaced 7 single-purpose example files with `example-mongodb-local.yaml` and `example-mongodb-voyage.yaml`; each covers all embedding models, all chunking methods, and all retrieval methods for that DB+provider |
| 2026-05-17 | — | Slice 16 spec for parallel sweep runs | Formalized deferred work: bounded in-process parallelism vs Celery; honor `execution.parallelism`; specs in [`docs/plan/slices/SLICE-16-PARALLEL-SWEEP-RUNS.md`](SLICE-16-PARALLEL-SWEEP-RUNS.md) |
| 2026-05-17 | 10 | Slice 10 spec for run recovery | In-place retry for FAILED runs (`--include-interrupted` optional); reuse `run_id`; delete stale `chunks`/`results` for that run only; config from Mongo `experiments.config`; boot recovery scoped to INTERRUPTED only; spec in [`docs/plan/slices/SLICE-10-RUN-RECOVERY.md`](SLICE-10-RUN-RECOVERY.md) |
| 2026-05-17 | 8 | Dual loading indicators (panel + polling badge) | Full LoadingFeedbackPanel for initial loads provides detailed progress; subtle PollingIndicator for background refreshes avoids visual noise |
| 2026-05-17 | 8 | fetchWithProgress with ReadableStream | Byte-level progress via `response.body.getReader()` enables real-time progress bars; better UX than spinners for large payloads |
| 2026-05-17 | 8 | Shared DashboardShell + AppPageChrome components | Unified header/nav/layout across all screens; DRY principle, consistent UX, easier to maintain |
| 2026-05-17 | 8 | Pagination defaults 10 (lists) / 5 (configs) | Prevents DOM overload and cognitive fatigue; configs more verbose so lower per-page count |
| 2026-05-17 | 8 | initialLoadDone flag per screen | Polling indicator only shows after first load completes; avoids visual confusion during hydration |
| 2026-05-18 | 8 | ExperimentProgressCard reusable component | Extracted circular progress pattern from detail screen; enables consistent progress visualization across screens; separates network progress (LoadingFeedbackPanel) from execution progress (ExperimentProgressCard) |
| 2026-05-19 | — | Boot orphan reconciliation always on | BackgroundTasks die on reload; Mongo `running` must be corrected without waiting for Slice 10 retry |
| 2026-05-19 | — | Run outcome buckets in dashboard | successful + failed + interrupted + not started must sum to `run_count`; fixes misleading partial UI |
| 2026-05-19 | — | Atlas storage quota via Admin API | Avoid hardcoded M0 512 MB; optional manual `MONGODB_STORAGE_LIMIT_MB` override |
| 2026-05-19 | — | Pause/resume cooperative sweep control | `_SweepControl` threading events; `resume_sweep()` skips completed param signatures; status `paused` non-terminal |
| 2026-05-19 | — | voyage-context-3 segment splitting | Contextualized API 32K window; tiktoken cl100k_base sizing; standard Voyage models unchanged (`embed()` path) |
| 2026-05-19 | — | Expanded Voyage model registry | voyage-4 series, domain models, voyage-context-3, voyage-3 legacy; `contextualized` flag drives embedder dispatch |
| 2026-05-23 | — | Timezone-aware UTC timestamps | Fix browser elapsed/duration misparse; PyMongo `tz_aware=True` |
| 2026-05-23 | — | `started_at` on first run | Exclude queue time from duration and ETA |
| 2026-05-23 | — | Atlas tier specs in db-stats | `resolve_tier_specs()` — instance size, provider, region; shared-tier storage fallback |
| 2026-05-23 | — | Progress elapsed + ETA | Linear estimate from completed runs; 1% margin |
| 2026-05-23 | — | Search index preflight before sweeps | Derive required indexes from config; check M0 3-index cluster quota; HTTP 422 / fail fast — no wasted embedding |
| 2026-05-23 | — | `indexes list\|reset` CLI | Inspect known vs unknown cluster-wide; drop unknown or rebuild chunks indexes |
| 2026-05-23 | — | Option A scoped logging | Unified `[rag-params-finder] [Scope] …` in server, CLI, dashboard dev console |
| 2026-05-23 | — | Dedicated sweep + heavy-read thread pools | Default executor starved `GET /experiments` during long sweeps and db-stats aggregations |
| 2026-05-23 | — | Decoupled dashboard poll intervals | List 2 s, vector DB stats 60 s, Search Explorer 15 s while running — constants in `frontend/src/constants.ts` |
| 2026-05-23 | — | Search Explorer `PollingIndicator` anti-jitter | `showDelayMs=600`, `minVisibleMs=1000` — badge no longer flickers on fast explore polls |
| 2026-05-23 | 18 | One retriever per run (corrected) | Each `retrievers` list entry is one sweep dimension; runs never chain retrievers. Reranker runs fetch dense candidates internally (implementation detail only). Supersedes prior "auto-prepend dense" / chaining decisions. |
| 2026-05-23 | 18 | Unified retriever configuration | Treat all retrieval strategies (dense/sparse/hybrid + rerankers) as unified `retrievers` list for sweep expansion |
| 2026-05-23 | 18 | Auto-migrate old retrieval config format | Pydantic `@model_validator` converts `methods` + `retrieval_provider`/`retrieval_model` to separate `retrievers` sweep entries |
| 2026-05-23 | 18 | Maintain old fields indefinitely | Keep `retrieval_method`, `retrieval_provider`, `retrieval_model` in DB — synthesized from single retriever for backward compat |
| 2026-05-23 | 19 | Slice 19 spec for storage quota guard | M0 hit 515/512 MB; writes blocked (cancel/delete deadlock); `dbStats` understated cluster usage; mirror search-index preflight pattern — spec in [`SLICE-19-STORAGE-QUOTA-GUARD.md`](SLICE-19-STORAGE-QUOTA-GUARD.md) |
| 2026-05-27 | 20 | Docs synced to toolchain + test reality | pytest count corrected (was 39); Kimchi on integration branch only; `quality-gates.sh` in interrupt recovery; CI/bandit/gitleaks documented |
| 2026-05-27 | 20 | Repo lint in CI + pre-commit | shellcheck (`scripts/*.sh`), actionlint, markdownlint; `scripts/repo-lint.sh`; pragmatic `.markdownlint.json`; CI `repo-lint` job (4 jobs total) |
| 2026-05-28 | — | Docs navigation (playgroup-style) | Root `QUICKSTART.md`; `docs/README.md` index; `PROGRESS.md` lives under `docs/plan/slices/` beside slice specs |
| 2026-05-28 | 20 | Pre-push = fast gates (`--quick`) | `git push` → `pre-push-gates.sh` (repo lint, ruff, mypy, bandit, pytest, frontend verify, gitleaks); commit hook stays staged pre-commit only |
| 2026-07-24 | chore | Idempotent hooks: testmon at commit, push-only coverage | Pre-push was calling `quality-gates.sh --full` — duplicated everything from commit stage; replaced with `pre-push-gates.sh` (push-specific: full pytest+cov, pip-audit, vitest, npm audit); added `pytest-testmon` to commit hook so only changed-module tests run (~1.7s warm); supersedes 2026-05-28 pre-push decision |
| 2026-07-24 | chore | T4 tier: nightly.yml (mutmut, Stryker, TruffleHog-full, SBOM, Meterian, container scan) | Deep checks too slow for CI (~15–60 min); scheduled nightly 02:00 UTC (`0 2 * * *`) + `workflow_dispatch` for manual runs; Meterian added as separate job (SCA + license, API-key-gated); container-scan skips if no Dockerfile (step-output guard, not job-level hashFiles — actionlint requirement); Trivy SBOM scan now `exit-code: 1` (consistent gate with container scan) |
| 2026-07-27 | chore | Meterian `.meterian` SCA exclusions (Trivy parity) | Documented waivers for aim (no installable 4.x), langchain CVE-2024-7774 (JS-only), transformers CVEs (ST&lt;4), langsmith 0.8.0 (sie-sdk websockets&lt;15). Compensating controls in each `description`. Revisit when TRAIL ML stack / sie-sdk websockets constraints lift. |
| 2026-07-27 | chore | `.trivyignore` langsmith blocker corrected | **SUPERSEDES** 2026-07-24 langsmith “langchain-core pre-release only” rationale. Actual lock blocker is sie-sdk `websockets&lt;15` vs langsmith≥0.8.18 `websockets≥15` (langchain-core 1.4.x already locked). Aligned with `.meterian` / `pip-audit.sh` / TRAIL deferred rows. |
| 2026-07-27 | chore | Meterian nightly: OSS path + Python/Node pin + report archive | **SUPERSEDES** 2026-07-24 Meterian “API-key-gated” / “no local artifacts” notes for GHA. Public MIT → `oss: true` (no `METERIAN_API_TOKEN`); fix input to `cli_args`; pin `--enabled-scanners=python,nodejs` (non-Java); archive HTML/JUnit/SARIF + Meterian SBOM (`.cdx.json` + `.csv`) beside Anchore CycloneDX for vendor comparison. Local `scripts/security-scan.sh --meterian` still token-gated. |
| 2026-07-24 | chore | dmypy daemon at commit stage | `mypy` hook replaced with `dmypy run` — daemon persists across commits; warm runs ~0.5s vs 2.2s cold; first run after fresh checkout ~60s (map build); `.dmypy.json` added to `.gitignore` |
| 2026-07-24 | chore | Frontend verify split: tsc at commit, vite build at push | `frontend-verify` hook (tsc + vite build ~12s) split into `frontend-typecheck` (tsc --noEmit ~3s) at commit + `npm run build` in `pre-push-gates.sh` when frontend changed; saves ~8s per frontend commit |
| 2026-07-24 | chore | actionlint already runs locally via pre-commit managed binary | Tested: ~620ms at commit via `rhysd/actionlint` hook (downloads own binary); no PATH install needed; detection latency gap closed — not only in CI |
| 2026-07-24 | chore | Stryker runner: jest-runner → vitest-runner | nw-review blocking finding: Stryker was wired to `@stryker-mutator/jest-runner` (a Jest-specific runner) while the frontend project uses Vitest; mutation test results would be silently invalid; fixed in nightly.yml |
| 2026-07-24 | chore | Chalk vs CycloneDX SBOM: complementary, not competing | CycloneDX (OWASP `anchore/sbom-action`) = dependency inventory document ("what packages are present?"); Chalk (Crash Override `setup-chalk-action`) = build-time artifact attestation ("is this the exact binary CI produced?" via Sigstore keyless signing). Both retained: SBOM for license/vuln scanning, Chalk for supply-chain integrity. Chalk uses `id-token: write` for GitHub OIDC keyless signing. |
| 2026-07-24 | chore | BACKEND_CHANGED: dedicated variable for backend source file detection | `BACKEND_LOCK_CHANGED` only tracked lockfile changes (gates pip-audit). pytest was running unconditionally on push regardless of what changed. `BACKEND_CHANGED` tracks `server/\|cli/\|tests/\|pyproject.toml\|uv.lock` — matching `ci.yml` `backend` paths-filter. Symmetric with `FRONTEND_CHANGED` gating vitest. Conservative fallback sets all 4 vars to 1 so no checks are silently skipped. |
| 2026-07-24 | chore | Nightly action pinning: @main/@master → stable version tags | nw-review finding: TruffleHog @main and trivy-action @master are floating pointers on the default branch — supply-chain risk and non-reproducible CI; pinned to @v3 (TruffleHog), 0.29.0 (trivy-action ×2), @v0.17.0 (sbom-action); consistent with existing project style (major version tags) |
| 2026-07-24 | chore | Trivy CVE suppression: ignore-unfixed + .trivyignore (3 Python CVEs) | Container scan found 101 OS CVEs (unfixable: linux-libc-dev, perl toolchain from build-essential — no Debian patch; root fix = Slice 42 multi-stage Dockerfile) and 3 Python CVEs with fixes: langsmith GHSA-f4xh-w4cj-qxq8 (fix: >=0.8.18, blocked: langchain-core>=1.4.0 pre-release only, uv lock unsatisfiable) and transformers CVE-2026-4372/CVE-2026-5241 (fix: >=5.5.0, blocked: sentence-transformers<4.0.0 constraint, ML stack upgrade deferred). Compensating controls: langsmith file-read not reachable from user input; transformers RCE mitigated by model-registry allowlist in model_registry.py. All suppressions documented in .trivyignore with blocker, control, and unblock condition. |
| 2026-07-24 | chore | pre-push-gates.sh: conservative fallback on empty change detection | nw-review medium finding: if `git diff` returns empty (shallow clone, first-ever push, unusual git state), all change gates defaulted to 0 → tests silently skipped; fixed to run all checks when CHANGED is empty |
| 2026-06-27 | 21 | embedder_factory.py as single dispatch point | Factory pattern over Protocol/ABC (Decision #10); orchestrator never does provider if/elif; each provider module exports embed_docs_fn + embed_query_fn |
| 2026-06-27 | 21 | SIEClient per call (no module-level cache) | Module-level client cache caused test state leakage between test runs; per-call instantiation ensures isolation |
| 2026-06-27 | 21 | Minimal FastAPI app in sweep tests | Importing server.main chains into voyageai → torch → OpenMP abort in sandbox; sweep router mounted standalone avoids the crash |
| 2026-06-27 | 21 | SIE health endpoint is /healthz not /health | SIE Docker exposes /healthz; check_sie_health() and CLAUDE.md updated accordingly |
| 2026-05-27 | 14 | Docker Compose (AIE7-adapted) | 2-service stack (no local vector DB); host CLI; prod default + `docker-compose.dev.yml`; `/healthz` MongoDB ping; `hf_cache` volume |
| 2026-05-27 | 14 | Dev overlay vs Compose profiles | `docker-compose.dev.yml` merge (not named profiles) — avoids port conflicts between prod/dev frontends |
| 2026-05-27 | 20 | Pre-push (superseded 2026-05-28) | Was `pre-commit --all-files` on push — replaced by `quality-gates.sh --quick` for pytest + frontend verify |
| 2026-07-28 | 45 | Close Slice 45 — gate-evidence + mutation waive #160 | Must+Should+scripts Could verified; optional FE docstring / drift-guard / BE GWT Could deferred; PR #130 |
| 2026-07-28 | 45 | Land Slice 45 Could leftovers (#161) | FE Scenario/Slice docstrings; coverage threshold drift guard; BE GWT-on-touch on moved suites |
| 2026-07-28 | 44 | Nightly Stryker residual after suite growth (#163) | Narrow mutate to utils/services/hooks; StrykerJS `ignoreStatic` + exclude `StringLiteral`; concurrency+progress; timeout 90 + pin 9.6.1; NIT artifact@v5 — restores #138/#160 nightly signal; Won't full-screen mutate. Owned on SLICE-44 Residual §4 (not a new slice). **IMPLEMENTED** locally (~8m); Nightly VERIFIED pending |
| 2026-07-28 | 40 | Slice theme folders numbered by delivery wave (#162) | Specs → `01-core-pipeline` … `07-quality-craft`; PROGRESS + gate-evidence stay flat; no date folders; keep 32/32C/32B together |
---

## Blockers & Issues

| Slice | Issue | Severity | Status | Resolution |
|-------|-------|----------|--------|------------|
| 19 | Atlas M0 storage quota blocks all writes; cancel/delete deadlock when cluster full | 🟡 Workaround exists | 📋 Spec written | Delete **complete** experiments to free space; then cancel works. Force-delete + preflight planned in Slice 19. Incident: `example-mongodb-local` 60-run sweep + voyage experiment on one M0 cluster. |

**Severity**: 🔴 Blocker | 🟡 Workaround exists | 🟢 Minor

---

## Slice 21: SIE Skateboard ✅

**Status**: ✅ COMPLETE | **Started**: 2026-06-27 | **Completed**: 2026-06-27 | **Target**: ~4–6 h

### Goal
Integrate SIE (Superlinked Inference Engine) as a third embedding provider, add Aim experiment logging, and expose a new `POST /api/v1/sweep` endpoint for Tier 1 ranked sweeps. Corpus is supplied by the caller via the `corpus: list[str]` field; falls back to the topic string when empty.

### Acceptance Criteria
- [x] `POST /api/v1/sweep` returns ranked retrieval methods with scores
- [x] `GET /health` includes `sie` and `version` fields
- [x] SIE models (BGE-M3, Stella-v5, SPLADE-v3) registered in `model_registry.py`
- [x] `embedder_factory.py` dispatches voyage/local/sie without orchestrator if/elif
- [x] `SweepRequest.corpus` accepts caller-supplied chunks; falls back to topic string when empty
- [x] `aim_logger.py` logs run params to Aim (no-op on failure — non-fatal)
- [x] 58 tests pass, coverage ≥80% threshold
- [x] ruff: 0 errors, mypy: 0 errors, frontend: 0 errors

### Files Created / Modified
| File | Change |
|---|---|
| `server/core/sie_embedder.py` | NEW — SIE BGE-M3/Stella-v5 embedding functions |
| `server/core/aim_logger.py` | NEW — Aim experiment run logging wrapper (no-op on fail) |
| `server/core/embedder_factory.py` | NEW — Provider dispatch factory (voyage/local/sie) |
| `server/api/sweep.py` | NEW — `POST /api/v1/sweep` + health helper functions |
| `server/core/model_registry.py` | SIE models added (bge-m3, stella-v5, splade-v3) |
| `server/models/config.py` | `Provider` Literal extended with `sie` |
| `server/models/status.py` | `Provider` Literal extended with `sie` |
| `server/core/embedder.py` | Voyage functions renamed to `embed_*_voyage`; dispatch removed |
| `server/core/orchestrator.py` | Uses `embedder_factory.get_embedder()` + `AimLogger.log_run()` |
| `server/main.py` | Sweep router mounted + enhanced `/health` endpoint |
| `pyproject.toml` | Added `sie-sdk`, `aim` dependencies |
| `tests/test_sie_embedder.py` | NEW — 5 GWT tests |
| `tests/test_embedder_factory.py` | Rewritten — 6 GWT tests (sys.modules mocking) |
| `tests/test_sweep_endpoint.py` | NEW — 9 GWT tests (minimal FastAPI app) |
| `configs/mongodb/example-sie.yaml` | NEW — CLI full-pipeline SIE sweep (120 runs, bge-m3/stella-v5/splade-v3) |
| `tests/test_config_examples.py` | NEW — example YAML load/expand/index-plan validation |

---

## Forward Roadmap

| Slice | Goal | Priority | Est. |
|-------|------|----------|------|
| ~~6 — Additional chunkers~~ | ~~Implement fixed, token, sentence, semantic~~ | ~~Should~~ | ✅ Done |
| ~~8 — SPARSE/HYBRID retrieval~~ | ~~BM25 + hybrid RRF via Atlas FTS~~ | ~~Should~~ | ✅ Done (merged into Slice 6) |
| 9 — Search Explorer dashboard | Best-params card, ranked configs, per-query results view | Should | ~30 min |
| 10 — Run recovery | Spec: [`SLICE-10-RUN-RECOVERY.md`](SLICE-10-RUN-RECOVERY.md) — `recover` CLI + `POST /experiments/{id}/recover`; per-`run_id` scrub + retry (**FAILED** default; **INTERRUPTED** opt-in); **`RECOVER_ON_BOOT`** retries **INTERRUPTED** only *(not all FAILED)* | Could | ~1–2 h |
| 11 — Dashboard-triggered runs | Submit experiments from the React UI, not just CLI | Could | ~45 min |
| 28 — Results export | Spec: [`SLICE-28-RESULTS-EXPORT.md`](SLICE-28-RESULTS-EXPORT.md) — CSV/JSONL download; [#49](https://github.com/neomatrix369/rag-params-finder/issues/49) | **Must** | 📋 PLANNED — @cschanhniem (~1.5 h) |
| 32–38 — Supabase/pgvector | Dual-backend Protocol → Postgres cutover + ADR-004 — [`PRD`](../plan/PRD-supabase-pgvector-migration.md) | **Must** | 📋 PLANNED — core team next |
| 12 — SSE live updates | Replace 2 s polling with Server-Sent Events | Could | ~20 min |
| 13 — Experiment cleanup CLI | `rag-params-finder cleanup --older-than 30d` | Could | ~15 min |
| 19 — Storage quota guard | Atlas M0 guard — **📦 DEFERRED**; Postgres stats in Slice 36 | Should | deferred |
| 26 — Local MongoDB docs | **📦 DEFERRED** — re-scope after Postgres local path (37) | Should | deferred |
| 27 — MongoDB mode indicator | **📦 DEFERRED** — absorbed into Slice 36 four-value storage_mode | Should | deferred |
| ~~14 — Docker Compose~~ | ~~One-command local setup~~ | — | ✅ Delivered in Slice 14 |
| ~~15 — CI/CD~~ | ~~GitHub Actions~~ | — | ✅ Delivered in Slice 20 |
| 16 — Parallel sweep (`parallelism` > 1) | Bounded concurrent `_run_single` (+ optional Celery upgrade path); Atlas/Voyage-rate-limit aware | Should | ~2–4 h |
| 30 — Search Explorer UX fixes | Spec: [`SLICE-30-SEARCH-EXPLORER-UX.md`](SLICE-30-SEARCH-EXPLORER-UX.md) — tab switch latency, zero-score noise, BM25 score labels, VDB card default-expanded | Could | ~2 h |
| 31 — Experiment list filter | Spec: [`SLICE-31-EXPERIMENT-LIST-FILTER.md`](SLICE-31-EXPERIMENT-LIST-FILTER.md) — status dropdown + name/ID search above experiments table | Should | ~2 h |
| 43 — Supabase config verification | Spec: [`SLICE-43-SUPABASE-CONFIG-VERIFICATION.md`](SLICE-43-SUPABASE-CONFIG-VERIFICATION.md) — live smoke of supabase examples; `STORAGE_BACKEND` vs YAML provider docs; hosted short-config guidance | Could | ~1–2 h |
| 44 — Frontend coverage gate | Spec: [`SLICE-44-FRONTEND-COVERAGE-GATE.md`](SLICE-44-FRONTEND-COVERAGE-GATE.md) — Must: embed coverage table/floor in quality-gates + pre-push + CI (**VERIFIED**); Should: FE tests + structure taxonomy (§3) — ✅ COMPLETE 2026-07-27; Residual §4 Nightly Stryker **IMPLEMENTED** (#163; Nightly artifact VERIFIED pending) | Should | ✅ + residual IMPL |
| ~~45 — Module theme separation + FE/BE craft~~ | Spec: [`SLICE-45-MODULE-THEME-SEPARATION.md`](SLICE-45-MODULE-THEME-SEPARATION.md) — hotspots 1–5 + FE/BE craft + scripts themes; mutation #160 — ✅ COMPLETE 2026-07-28 · [`slice-45.json`](../gate-evidence/slice-45.json) · [PR #130](https://github.com/neomatrix369/rag-params-finder/pull/130) | Could | ✅ Done |

---

## Release Cadence

**Current version**: v0.11.0 ([CHANGELOG.md](../../CHANGELOG.md))

**Versioning strategy**: [Semantic Versioning](https://semver.org/) with hybrid approach:
- **Minor** (0.x.0) — Major slice completion, new features, provider additions
- **Patch** (0.x.y) — Bug fixes, polish, documentation improvements, logging enhancements

**When to release**:
- ✅ **After slice completion** — When a numbered slice (10, 11, 16, 19, etc.) is marked ✅ COMPLETE
- ✅ **After significant features** — Multi-slice work like pause/resume, search index preflight
- ✅ **After polish sprints** — Dashboard UX improvements, scoped logging, etc.
- ❌ **Not for every commit** — Bundle related changes; release when value is deliverable

**Release workflow**:
```bash
# After marking slice complete in this file:
./scripts/release/release.sh minor    # For slice completion or new feature
./scripts/release/release.sh patch     # For bug fixes or polish

# The script will:
# 1. Bump version in pyproject.toml, frontend/package.json
# 2. Prompt for CHANGELOG.md update
# 3. Create annotated git tag with changelog excerpt
# 4. Optionally push and create GitHub release
```

**See**: [docs/contributor-guide/release-process.md](../contributor-guide/release-process.md) for complete workflow.

**Reminder**: Update CHANGELOG.md **during** development, not at release time. Move items from `## [Unreleased]` to the new version section when ready.

---

## Skill Execution Log

Tracks skill runs across slices and sessions. Appended automatically by `/verify-slice`, `/sync-docs`, `/update-pr`, and other skills. Read this first when resuming a session to know exactly where the slice stands.

| Date | Branch | Skill | Slice | Outcome | Notes |
|---|---|---|---|---|---|
| 2026-07-28 | main | /sync-docs | 44 Residual §4 / #163 | APPLIED | Feature-delta for documented Nightly Stryker timeout: `development.md` honest residual note; CHANGELOG Unreleased Changed (**DECIDED**, not IMPLEMENTED); `slice-44.json` mutation + lifecycle residual; HANDOFF Where We Are. Trackers (PROGRESS/TRAIL/DECISIONS/SLICE-44) already had §4. No user-guide. CLAUDE.md Nightly claims absent — no change. |
| 2026-07-27 | chore/project-hygiene | /sync-docs | Meterian `.meterian` exclusions | APPLIED | Feature-delta sync: `.meterian` already present; corrected stale `.trivyignore` langsmith blocker (sie-sdk websockets&lt;15; SUPERSEDES “core pre-release”); TRAIL deferred rows for ST4/transformers, langsmith, aim; `development.md` SCA suppressions triad; `pip-audit.sh` + `security-scan.sh` (`-w /workspace`) parity comments; CHANGELOG Security + TRAIL link. No user-guide. Evidence **IMPLEMENTED**; **VERIFIED** pending Meterian nightly. |
| 2026-07-27 | chore/project-hygiene | (manual) | Meterian `.meterian` exclusions | APPLIED | Root `.meterian` + `nightly.yml` comment + `development.md` pointer + PROGRESS/CHANGELOG. Waives aim CVE-2025-51464/5321, langchain CVE-2024-7774, transformers CVE-2026-4372/5241/1839, langsmith 0.8.0 (GHSA-f4xh). **IMPLEMENTED**; **VERIFIED** pending Meterian nightly. |
| 2026-07-27 | chore/project-hygiene | /sync-docs | Meterian nightly OSS + artifacts | APPLIED | `development.md`: nightly Meterian described as OSS (`oss: true`), Python/Node pin, archived reports + dual SBOM; local script still token-gated. `PROGRESS.md`: maintenance + decision rows (SUPERSEDES API-key-gated / no-artifacts). `CHANGELOG` Unreleased Changed. No user-guide changes (CI internals). Evidence: **IMPLEMENTED** in `nightly.yml`; not **VERIFIED** until a nightly run succeeds. |
| 2026-07-26 | main | /nw-review (nw-documentarist-reviewer) | Slice 43 closure | APPROVED | No technical blockers; reviewer validated live evidence, operator docs, honest hosted-Supabase deferral, and owned-elsewhere routing. Required tracker housekeeping applied before PASSED. |
| 2026-07-26 | main | /slice-workflow | Slice 43 closure | COMPLETE | `/healthz` Postgres healthy; config tests 25 passed; experiment `dd107437-be69-4d62-a549-003b743ed841` completed 16/16; full quality gates passed (276 backend, 16 frontend, 96.8% scoped coverage, audits clean). |
| 2026-07-24 | chore/project-hygiene | /sync-docs | CVE suppression (PR #105) | APPLIED | PROGRESS.md: 1 decision row (Trivy CVE suppression strategy, compensating controls, blockers). No user-guide, CHANGELOG, or contributor-guide changes — CI internals only; no user-visible behavior change. |
| 2026-07-24 | chore/project-hygiene | /sync-docs (round 3) | hygiene chore | APPLIED | `development.md`: Chalk added to nightly job lists (2 locations); BACKEND_CHANGED gating noted in pre-push description; push/nightly table rows updated. `PROGRESS.md`: 4 maintenance rows (Chalk, artifact audit, cron fix, BACKEND_CHANGED); 2 decision rows (Chalk vs CycloneDX, BACKEND_CHANGED design). No user-guide or CHANGELOG changes warranted (tooling chore). |
| 2026-07-24 | chore/project-hygiene | /sync-docs + /clean-commit | hygiene chore (round 2) | APPLIED | PROGRESS.md updated with nw-review findings, frontend JUnit, action pinning decisions; 3 new decision log rows; 4 new skill log rows |
| 2026-07-24 | chore/project-hygiene | /nw-review (nw-platform-architect-reviewer) | PR #103 workflows + scripts | NEEDS_REVISION → FIXED | 2 blockers + 3 criticals + 2 highs + 1 medium fixed in e7740dc; push gates fallback hardened; branch now 10 commits ahead of main |
| 2026-07-24 | chore/project-hygiene | /update-pr | PR #103 (after frontend coverage) | UPDATED | Body updated with frontend JUnit + v8 coverage table (47.45% stmt, 46.42% branch); 10 vitest tests pass; backend unchanged |
| 2026-07-24 | chore/project-hygiene | feat(frontend): JUnit + v8 coverage | PR #103 | COMMITTED | @vitest/coverage-v8 + JUnit reporter in vite.config.ts; test:coverage + test:ci scripts; .test-results/ and .reports/ gitignored; commit 5a3ef50 |
| 2026-07-24 | chore/project-hygiene | /update-pr | PR #103 | UPDATED | https://github.com/neomatrix369/rag-params-finder/pull/103 — pushed 4 new commits (0372411..318bec4); PR title + body refreshed; 217/0 tests, 96.7% coverage; prerequisites met |
| 2026-07-24 | chore/project-hygiene | /clean-commit | hygiene chore | COMMITTED | `.dmypy.json` added to `.gitignore` (daemon socket reference); branch clean (no AI attribution trailers); 6 commits ahead of main |
| 2026-07-24 | chore/project-hygiene | /sync-docs | toolchain docs | APPLIED | `CLAUDE.md` hook descriptions; `development.md` hook table, CI job count (4→5), nightly section; no user-guide or CHANGELOG changes needed |
| 2026-07-24 | chore/project-hygiene | nw-agent-builder-reviewer | PR #103 scripts + workflows | APPROVED with P2 fix | P2 (fixed): Trivy SBOM `exit-code: 0→1`; P3 (noted): comment clarity in `pre-push-gates.sh`; idempotency and safety verified clean |
| 2026-07-24 | chore/project-hygiene | gate-timing-analysis | commit/push/CI durations | COMPLETE | Timing table: commit ~25s, push ~30–43s, CI backend ~112s. Three opts applied (dmypy, tsc split, actionlint already wired). All gate placements justified. |
| 2026-07-24 | chore/project-hygiene | /project-hygiene | hygiene audit | APPLIED | nightly.yml, code-review-graph.yml, .prettierignore, .testmondata*, idempotent hooks, pytest-testmon; PR #103 opened |
| 2026-07-24 | docs/plan-slice-42-docker-build | /sync-docs | nightly.yml action version fixes | APPLIED | Fixed 3 broken GitHub Actions refs causing nightly CI failures. `trivy-action@0.29.0→@v0.35.0` (×2): missing `v` prefix + security-critical upgrade (tags v0.0.1–v0.34.2 compromised in supply chain attack March 2026, v0.35.0 confirmed safe). `trufflehog@v3→@v3.95.9`: pinned floating major tag that stopped resolving. `meterian-github-action@v1→@v1.0.17`: same. No docs or user-guide changes needed (CI internals). |
| 2026-07-22 | docs/plan-slice-42-docker-build | /nw-review + /sync-docs | Slice 42 spec review | APPLIED | Ran nw-agent-builder-reviewer + nw-platform-architect-reviewer (via /nw-review). Both returned NEEDS_REVISION. Applied 3 blocking fixes: B1 spike command narrowed to uv sync --frozen only; B2 GWT Should-10 added (nginx SPA fallback curl test); B3 mkdir -p /root/.npm added to frontend Dockerfiles. Plus 4 non-blocking refinements (SLICE-14 cross-ref, PYTHONPATH location, continue-on-error removal criteria, image size threshold). Committed to docs/plan-slice-42-docker-build. |
| 2026-07-22 | main | /enhanced-flow-planner + /sync-docs | Slice 42 planning | COMPLETE | Plan health: 0 gaps. Added Slice 42 (Docker Build Optimisation): SLICE-42 spec, TRAIL.md row, PROGRESS.md rows, DECISIONS.md #70, GAP_ANALYSIS.md gap row, HANDOFF.md. User confirmed nginx:alpine for frontend runtime. |
| 2026-07-24 | chore/project-hygiene | /sync-docs | nightly.yml action version fixes | APPLIED | Fixed 3 broken GitHub Actions refs causing nightly CI failures. `trivy-action@0.29.0→@v0.35.0` (×2): missing `v` prefix + security-critical upgrade (tags v0.0.1–v0.34.2 compromised in supply chain attack March 2026, v0.35.0 confirmed safe). `trufflehog@v3→@v3.95.9`: pinned floating major tag that stopped resolving. `meterian-github-action@v1→@v1.0.17`: same. No docs or user-guide changes needed (CI internals). |
| 2026-07-22 | main | /enhanced-flow-planner | Slice 41B plan addition | COMPLETE | Added PARKED Slice 41B (Bayesian Advanced); created SLICE-41B spec; updated TRAIL/PROGRESS/DECISIONS; sync-docs + clean-commit + PR follow |
| 2026-07-21 | main | /sync-docs | Slice 16 completion sync | COMPLETE | Fixed Quick Status inconsistency (`PLANNED` → `✅ COMPLETE`) for Slice 16; confirmed spec + addendum complete; manual demo blockers unchanged and documented |
| 2026-07-20 | main | /enhanced-flow-planner | Slice 39 | COMPLETE | Continuation check reviewed pending/planned slices; no migration needed this pass beyond confirming Slice 39's status alignment |
| 2026-07-20 | main | /sync-docs | 39 plan sync | COMPLETE | Added Skill Execution Log entries for this sync/session and confirmed `TRAIL.md` and `PROGRESS.md` now align on Slice 39 completion state |
| 2026-07-19 | slice/39-demo-ready-dashboard-polish-implementation | /nw-review | Slice 39 iteration 2 | APPROVED | Both prior blockers cleared: unrelated MongoDB scope removed; 7 rendered lifecycle component scenarios wired into local gates and CI |
| 2026-07-18 | slice/39-demo-ready-dashboard-polish-implementation | /browser:control-in-app-browser | Slice 39 | COMPLETE | In-app connection unavailable; standalone Playwright fallback verified 1440×900 and 390×844 list/detail, six lifecycle states, async states, keyboard focus, zero contrast violations, and unchanged 2 s GET cadence |
| 2026-07-09 | docs/supabase-migration-plan | /update-pr | plan 32–38 + gap bridge | CURRENT | https://github.com/neomatrix369/rag-params-finder/pull/72 — branch up-to-date; PR title/body unchanged; prerequisites: bypassed (docs-only plan PR) |
| 2026-07-09 | docs/supabase-migration-plan | /update-pr | plan 32–38 + gap bridge | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/72 — gap-bridge + nw-review polish commits; prerequisites: bypassed (docs-only plan PR) |
| 2026-07-09 | docs/supabase-migration-plan | /update-pr | plan 32–38 | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/72 — doc matrix commit reflected; prerequisites: bypassed (no /verify-slice, no /sync-docs; docs-only plan PR) |
| 2026-07-06 | slice/29-padding-propagation | /update-pr | Slice 29 | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/63 — rebased docs footprint; PR already current; prerequisites: bypassed (no /verify-slice, no /sync-docs) |
| 2026-07-06 | slice/29-padding-propagation | /update-pr | Slice 29 | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/63 — docs footprint commit + PR refresh; prerequisites: bypassed (no /verify-slice, no /sync-docs) |
| 2026-07-06 | slice/29-padding-propagation | /update-pr | Slice 29 | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/63 — rebased footprint row; PR already current; prerequisites: bypassed (no /verify-slice, no /sync-docs) |
| 2026-07-06 | slice/29-padding-propagation | /update-pr | Slice 29 | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/63 — gate-cache gitignore + skill footprints committed; prerequisites: bypassed (no /verify-slice, no /sync-docs) |
| 2026-07-06 | slice/29-padding-propagation | /update-pr | Slice 29 | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/63 — run_id retrieval scoping + pathway tests; prerequisites: bypassed (no /verify-slice, no /sync-docs; pre-push gates passed) |
| 2026-07-06 | slice/29-padding-propagation | /update-pr | Slice 29 | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/63 — Atlas Local volume fix + padding propagation; prerequisites: bypassed (quality-gates --quick passed in session) |
| 2026-07-07 | main | /sync-docs | plan review + nw-review | STAGED | T1-2: PROGRESS.md (Slices 30/31 added, Slice 22 Must, header updated, decision log); DECISIONS.md rows 37-38 (reclassification + AC rewrite); TRAIL.md Slice 22 Must; SLICE-30 ACs rewritten (behavioral only) |
| 2026-07-06 | main | plan sync | Slice 28 status | STAGED | PLANNED (not immediate); active work 22; planning on main via PR #55/#59 |
| 2026-07-06 | main | plan sync | prereq clearance | STAGED | HANDOFF + PROGRESS + slice Before-Checks; #47/#48/#59 merged |
| 2026-07-05 | docs/plan-gap-analysis-jul4 | /update-pr | plan gap analysis | MERGED | https://github.com/neomatrix369/rag-params-finder/pull/59 — footprint backfilled post-merge (commit landed after merge) |
| 2026-07-05 | fix/pr47-review-suggestions | /update-pr | PR #61 follow-up | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/61 — CI all green, mergeState CLEAN; prerequisites: bypassed (no /verify-slice) |
| 2026-07-05 | fix/pr47-review-suggestions | /update-pr | PR #61 follow-up | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/61 — merge commit + conflict resolution reflected; prerequisites: bypassed (no /verify-slice; quality-gates --quick passed in session) |
| 2026-07-05 | fix/pr47-review-suggestions | /sync-docs | PR #61 follow-up | STAGED | T1-2: CHANGELOG (#47/#48/#60/#61), CLAUDE+development+docs/README (97 tests); configuration.md already on branch; no slice status changes |
| 2026-07-01 | chore/toolchain-prettier-security-scan | /update-pr | Toolchain extension | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/46 — main sync, uv.lock + pip-audit fixes; prerequisites: bypassed (no /verify-slice on branch) |
| 2026-07-01 | slice/21-25b-sie-and-atlas-local | /sync-docs | 21/24/25/25B audit | STAGED | Full branch audit: CHANGELOG ✅, CLAUDE ✅, development.md + docs/README (78 tests), configuration.md SIE callout, QUICKSTART --local, README path row, HANDOFF 25B fix; user-guide mongodb/sie already current |
| 2026-07-01 | slice/21-25b-sie-and-atlas-local | /update-pr | 21/24/25/25B | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/52 — SIE screenshot crop + maxkb 1200; prerequisites: met (verify-slice COMPLETE 2026-06-30) |
| 2026-07-01 | slice/21-25b-sie-and-atlas-local | /update-pr | 21/24/25/25B | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/52 — screenshots + Atlas Local docs + pre-commit limit; prerequisites: met (verify-slice COMPLETE 2026-06-30) |
| 2026-07-01 | slice/21-25b-sie-and-atlas-local | /update-pr | 21/24/25/25B | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/52 — prerequisites: met (verify-slice COMPLETE 2026-06-30) |
| 2026-06-30 | slice/21-25b-sie-and-atlas-local | /verify-slice | 21/24/25/25B closing tests | COMPLETE | 78 pytest pass; local+cloud smoke OK; SIE sweep 200; fixes: compose profile + local TLS; docs synced |
| 2026-06-29 | slice/21-25b-sie-and-atlas-local | /verify-slice | Unified MongoDB Entry Points | COMPLETE | 12/12 criteria; quick gates 75 pass; CLI/compose smoke OK; docs current |
| 2026-06-29 | slice/21-25b-sie-and-atlas-local | /update-pr | 21/24/25/25B | PUSHED | https://github.com/neomatrix369/rag-params-finder/pull/52 — prerequisites: met (verify-slice COMPLETE) |
| 2026-06-29 | slice/21-25b-sie-and-atlas-local | /verify-slice | Unified MongoDB Entry Points | PARTIAL | 12/12 plan criteria; ruff/mypy/pytest 75 pass; smoke OK; PROGRESS 25B row + CHANGELOG stale |
| 2026-06-29 | slice/21-25b-sie-and-atlas-local | /sync-docs | Unified MongoDB Entry Points | STAGED | PROGRESS.md ✅, CHANGELOG ✅, CLAUDE ⏭, user-guide ⏭ |

**Outcome values**: `COMPLETE` · `PARTIAL` · `STAGED` · `PUSHED` · `FAILED` · `SKIPPED`

---

## Interrupt Recovery Checklist

Use this when resuming a session mid-slice:

```
[ ] Read the Skill Execution Log above — last skill run tells you where to resume
[ ] Read docs/plan/slices/PROGRESS.md — note current slice and last known state
[ ] Git hooks installed: bash scripts/ci/install-git-hooks.sh (once per machine)
[ ] Run quality gates to confirm no regressions:
      ./scripts/ci/quality-gates.sh          # full CI mirror before PR
      # git push runs ./scripts/ci/pre-push-gates.sh (full gates) when hooks installed
[ ] Check git status — any uncommitted changes?
[ ] Read the current slice spec in docs/plan/slices/SLICE-XX-*.md
[ ] Resume from the last incomplete acceptance criterion
[ ] Verify after every change before moving to the next criterion
```
