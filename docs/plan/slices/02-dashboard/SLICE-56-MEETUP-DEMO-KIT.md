# SLICE 56 — Meetup Demo Kit: About box, Walkthru, replay and cross-store leaderboard (Phase 0)

**MoSCoW:** MUST (parts A, C1, B, C2, C3, D, H) · COULD (part J, blocked)
**Target time:** ~8 h total (A 1 h · C1 1 h · B 1.5 h · C2 2 h · C3 1 h · D 0.5 h · H 0.75 h · buffer 0.25 h); stop and ask if any part overruns its budget by more than 50%.
**Status:** 📋 PLANNED
**Depends on:** **55** (SQLite run state is the export source) · soft: **53** (Redis vector store; the Step 0 sweep needs it healthy)
**Branch:** `slice/56-meetup-demo-kit` — one branch, one commit per part, review stop after each part, one PR to `main`
**Feature:** Redis London meetup (Thu 5 Nov 2026, host Samuel Agbede): in-app About box → guided Walkthru, replayed run on Redis 8, "what the best settings changed" story, cross-store leaderboard — all offline from bundled data of existing runs on the Fed Loan (Pell Grant) corpus.

> **Source:** "Phase 0 Master Prompt v3" (pasted by owner, 2026-11-04), reshaped by the evidence below. Planning record: `~/.claude/plans/lets-apply-enhanced-flow-planner-to-cozy-pelican.md`.
> **Method expansion** (more chunkers / retrievers) is deliberately **not** here → [SLICE-57](../01-core-pipeline/SLICE-57-METHOD-CATALOGUE-EXPANSION.md), queued after the meetup.

---

## Context

The host's brief: state the problem as a question; quick demo of finding the best settings on Redis 8; show how the best parameters improved the application; ~5 minutes; 3–4 slides outside this repo. This slice builds everything inside the repo: the About box, the Walkthru, the bundled demo data and the release the QR code points at.

- **Depends-on outputs:** Slice 55 `get_sqlite_storage()` / `SQLiteStorageBackend` (read-only access to experiments, runs, results) · Slice 53 Redis vector store (`VECTOR_STORE_BACKEND=redis`) · `server/core/results_analyzer.py::analyze_results()` (the single canonical ranking) · existing dashboard components `PhaseIndicator`, `BestParamsCard`, `DetailedResultsTab`, `CollapsibleCard`, `AppPageChrome`.
- **Invariants pointer:** `docs/plan/invariants.md` · `docs/plan/DECISION-OWNERSHIP.md` (frontend floors 95/90/95/95 are locked; merge/release is Human-owned; no bypass flags).

### Evidence that reshaped the prompt (2026-11-05 exploration)

| # | Finding | Consequence |
|---|---|---|
| 1 | **No phase-transition history is stored.** `run_status` keeps the current `phase`, `created_at`, `updated_at`, `elapsed_ms` (`sqlite_store.py:279-298` overwrites in place). | Prompt rule "exclude runs without a recorded timeline" would exclude every run. **Decision (#274):** the replay steps through the fixed pipeline stages with no per-stage durations; shows only recorded totals; labelled "stage sequence; only total time was recorded". Nothing invented. |
| 2 | **The only Redis data is a 4-run smoke test on `sample.pdf`.** All other stores ran `The_Federal_Pell_Grant_Program.pdf`. `configs/redis/example-local.yaml` has the same 120-run grid as `configs/mongodb/example-local.yaml` but points at `sample.pdf`. | **Decision (#275):** run the full 120-run Redis sweep on the Pell PDF (overrides the prompt's "no new sweep") as **Step 0**, from a temp copy of the config (no repo config change). |
| 3 | **No expected sources / ground truth** in `configs/questions.example.json` (77 questions across personas, `text` + `focus` only). No Ragas code or dependency in repo. | Improvement story uses **similarity-score spread only**, never "correct" or "hit" language. Expected-sources derivation deferred. **Part J blocked** until a `<RAGAS_CODE_PATH>` is supplied. |
| 4 | **One canonical ranking:** `analyze_results()` sorts by `(-max_score, -query_avg_score, chunk_size, overlap, padding)`; score = `rerank_score` else `dense_score`; min-max normalised across the inputs it is given. Config key includes `database_provider`. | Exporter calls `analyze_results` **once over the union** of exported runs; scores labelled "normalised across this export". Cross-store group key = config key **minus** `database_provider` + `data_paths` + `queries_file` + sha256 of the questions file at export time (runs stored only the path). |
| 5 | Local `data/run_state.db` holds 21 experiments / 1163 runs; 90 of 192 config keys (approximate key: dataset, questions file, embedding, chunking, size, overlap, padding, retrieval method; complete runs only) already span >1 store; `vector_store_snapshot` is NULL everywhere → store = `run.doc.database_provider`. | Pick the **latest completed experiment per (store, config key)**, tie-break by run id; rule recorded in the manifest. |
| 6 | **The Docker server keeps run state in a named volume** (`sqlite_run_state` → `/app/data`), **not** the host `data/run_state.db`. A sweep submitted to the Docker server lands in the volume. | Exporter accepts **repeated `--db`** (union; manifest lists each file + sha) so volume-copied and host DBs can be combined. Step 0 Before-Check inspects where the Redis runs landed (`docker cp` the volume DB out; do not write into the volume). |
| 7 | Frontend: no light/dark toggle (only per-component `tone`), no modal primitive, no Markdown renderer, no `data-tour`; `CollapsibleCard` open state is internal; the within-store runs table is inline JSX with no ranking; the ranked view is `HyperparametersTab` / `BestParamsCard` (pure props). | Build a small `Dialog` primitive; light tokens only; add an `open` override to `CollapsibleCard`; feed existing components by props through a pure adapter (no `apiClient` change). |
| 8 | JWLB (`neomatrix369/japanese-work-life-balancer`) has **no root LICENSE/NOTICE**; same author; README credits Risako for the idea. | **Decision (#276):** port with the owner's permission; attribution in CHANGELOG, About box, file headers. Port the pattern only; **do not port** voice/TTS (`tts-plugin.ts`, `voice.ts`, `useTourVoice`, `VoicePicker`, `VoiceToggle`, `.tts-cache`, `warm-voice`), `theme.css`, `design-system/`. |
| 9 | `docs/` is outside the Vite root; no `?raw` usage; Docker frontend build context unverified. | Part C1 Before-Check; fallback is a `prebuild` copy into `frontend/src/demo/` (no new dependency). |
| 10 | Release is `./scripts/release/release.sh minor` → `release/v0.13.0` PR; tag + GitHub release after merge; merge/release is Human-owned. | The QR/link 404s until Mani merges and tags. Part H ends with that HITL step. |

## Non-goals

- Any backend change beyond `scripts/demo/export_demo_results.py` (no new API, no phase-event recording, no orchestrator change).
- New chunking or retrieval methods → SLICE-57.
- Retrieval-quality metrics (Recall@k, MRR, nDCG), expected-sources derivation → Phase 2.
- Production concerns (latency, false positives) → a possible future full talk; only a "Coming next" line.
- A global dark mode or theme system; voice/audio/TTS; the Mermaid "how it works" diagram (Phase 1).
- Choice steps on lists other than the cross-store leaderboard (configs, results, golden-master questions).
- A frontend schema-validation test for `demo-results.json`, choice steps on other lists, the in-app Mermaid diagram → [SLICE-58](SLICE-58-PHASE0-LEFTOVERS.md) (`schema_version` is recorded now).
- Later phases from the prompt: docs reader paths → [SLICE-59](../07-quality-craft/SLICE-59-PHASE1-DOCS-READER-PATHS.md), relevance metrics → [SLICE-60](../01-core-pipeline/SLICE-60-PHASE2-RETRIEVAL-QUALITY-METRICS.md), store as sweep dimension → [SLICE-61](../05-storage/SLICE-61-PHASE3-VECTOR-STORE-AS-SWEEP-DIMENSION.md), setup manager → [SLICE-62](../03-platform/SLICE-62-PHASE4-SETUP-MANAGER.md), WCAG AA → [SLICE-63](SLICE-63-PHASE5-UIUX-WCAG-AA.md).
- Ranking stores by speed. Timings, if shown, are labelled indicative.

## Output contract

- **Baseline:** `git ls-files docs/about scripts/demo` → empty; `grep -rn "data-tour" frontend/src` → empty; no About button in the header.
- `docs/about/demo-results.json` exists, deterministic (two exports → identical bytes), with a manifest (inputs + sha, ranking field/direction, selection rule, exclusions with reasons, `schema_version`).
- An **About** button in the app header opens a dialog with the 10 sections in order, rendered from `docs/about/*.md`, working with the network off.
- **▶ Start Walkthru** runs 5 steps with Next/Back/Space/Esc, Autoplay **off** by default, Esc restores the UI state.
- The cross-store leaderboard renders offline, groups same-config runs across stores, sorts by score, filters by store; picking a run drives the replay.
- `docs/about/RECORDING.md` exists; a Next-by-Next recording is kept by the owner.
- `release/v0.13.0` PR open; CHANGELOG `[Unreleased]` promoted; issue templates and README rows present.
- `./scripts/ci/quality-gates.sh` green, frontend coverage floors 95/90/95/95 unchanged.

## Reuse ledger

| Need | Existing code | Action |
|---|---|---|
| Read experiments/runs/results | `get_sqlite_storage()`, `load_explore_source()`, `find_run_statuses()`, `list_results_for_experiment()` | **Reuse** (bypasses `ensure_storage_ready`, which demands `VECTOR_STORE_BACKEND`) |
| Ranking | `analyze_results()` in `results_analyzer.py` | **Reuse** once over the union; do not re-implement |
| Config key | `_run_config_key` | **Compose** a provider-less key from it; do not copy |
| Script pattern | `scripts/migrate/migrate_run_state_to_sqlite.py` | **Mirror** (argparse, typed, `from __future__ import annotations`) |
| Phase / results UI | `PhaseIndicator`, `BestParamsCard`, `DetailedResultsTab` | **Reuse** via props; no network |
| Ranked rows | `HyperparametersTab` row markup | **Extract** the row piece if inline; do not copy |
| Collapsible panels | `CollapsibleCard` | **Extend** with an `open` override |
| Tour mechanics | JWLB `steps.ts`, `useTour.ts`, `TourOverlay.tsx` | **Port** the pattern, voice and theme code removed |
| Release | `scripts/release/release.sh`, `docs/contributor-guide/release-process.md` | **Reuse** |

## Slice Workflow Bundle

Order and cut rules (from the consolidated priority, owner-confirmed):

| Rank | Part | MoSCoW | Budget |
|---|---|---|---|
| 0 | **Step 0** Redis Pell sweep (data prep, no code) | Must | background; start first |
| 1 | **A** demo data export | Must | 1 h |
| 2 | **C1** About box | Must | 1 h |
| 3 | **B** run replay (stepper) | Must | 1.5 h |
| 4 | **C2** Walkthru engine | Must | 2 h |
| 5 | **C3** cross-store leaderboard + choice step | Must, with fallback (renders whatever overlaps and states the limits) | 1 h |
| 6 | **D** fallback recording doc | Must (insurance) | 0.5 h |
| 7 | **H** release v0.13.0 (+I issue templates, +F README) | Must | 0.75 h |
| 8 | **J** golden-master resources | Could, blocked | — |

If time slips, cut Walkthru **step 4 then step 5** first (keep leaderboard, replay, improvement). Review stop after every part.

---

## Spec (GWT)

### Step 0 — Redis sweep on the Pell PDF (data prep)

- **Given** the stack is up (`/healthz` reports `vector_store_backend=redis`, `run_state_mode=sqlite-local`) **when** a temp copy of `configs/redis/example-local.yaml` with `data_paths: ./input_data/pdfs/The_Federal_Pell_Grant_Program.pdf` is submitted with `--detach` **then** an experiment reaches `complete` with ~120 runs, and its config keys overlap Mongo/Postgres/Elasticsearch keys.
- **Given** the Docker server writes run state to the `sqlite_run_state` volume **when** the exporter is later run **then** the volume DB is copied out (`docker cp`) and passed as a second `--db`; nothing is written into the volume.
- **Given** Redis `maxmemory` is 256 MB with `volatile-lru` **when** the capacity preflight estimates the sweep **then** a 422 is reported rather than a silent eviction (fail closed); the owner is told before any setting is changed.

### Part A — Demo data export

- **Given** one or more `--db` files and a `--questions` file **when** the exporter runs **then** `docs/about/demo-results.json` has a manifest (inputs + sha256, ranking `max_score` DESC → `query_avg_score` DESC → chunk_size/overlap/padding ASC → run id, selection rule, exclusions, `schema_version`).
- **Given** Redis 8 runs and the same configs on other stores **when** exported **then** every Redis 8 run is present, each exported config key also carries its runs on every other store (same dataset + questions + config only), and each other store contributes best / median (`floor((n-1)/2)`) / worst.
- **Given** no Redis 8 run is exportable **when** the exporter runs **then** it fails with a clear message.
- **Given** the output would exceed the size cap (default 5 MB / 600 runs) **when** exporting **then** it stops and asks for a selection rule; no run is silently dropped.
- **Given** the export **when** the improvement story is built **then** it reports best / median / worst similarity scores and spread on the Fed Loan questions, picks the question with the largest top-1 score gap, exports both runs' top chunks for it (chunk text ≤200 chars), and **prints the question** for the owner to confirm or swap.
- **Given** two runs of the exporter on the same inputs **when** compared **then** the output bytes are identical.

### Part C1 — About box

- **Given** the app header **when** the user clicks About **then** a dialog opens with the 10 sections in order (problem as a question, how it works, the improvement, Redis 8, evals-underway banner, coming next, try it + repo + QR + MIT, feedback, thanks to Samuel Agbede and Redis, golden-master link only if Part J shipped).
- **Given** the dialog is open **when** Esc is pressed **then** it closes and focus returns to the About button; focus is trapped while open.
- **Given** the evals banner **when** removed **then** one line or block change removes it.
- **Given** the network is off **when** the dialog opens **then** all content renders (Markdown bundled, QR is a committed static SVG).
- **Given** `prefers-reduced-motion` **when** the dialog opens **then** no animation runs.

### Part B — Run replay

- **Given** the bundled export **when** the replay step opens **then** the default run is the Redis 8 run and `PhaseIndicator` steps QUEUED → … → COMPLETE on Next, with the real total `elapsed_ms`, final phase and timestamps shown and the "only total time was recorded" label.
- **Given** a different run is picked **when** the replay restarts **then** it shows that run's stages and results through the existing `BestParamsCard` / `DetailedResultsTab`.
- **Given** Autoplay is off **when** time passes **then** nothing advances; with Autoplay on, steps advance on a timer.
- **Given** the server and Docker are stopped **when** the replay runs **then** no network request is made.

### Part C2 — Walkthru engine

- **Given** the five Markdown step files in `docs/about/walkthru/` **when** parsed **then** front-matter (`id`, `title`, `duration_s`, `route`, `highlight`, `choose`) is read; a malformed file fails the parse test with its name.
- **Given** the Walkthru is running **when** Space / ← / → / Esc are pressed **then** pause / back / next / exit.
- **Given** a step targets a collapsed `CollapsibleCard` **when** the step is entered **then** the card opens and is restored on exit.
- **Given** Autoplay is off (default) **when** a step is shown **then** only Next advances; the Autoplay toggle is visible, and when on advances by each step's `duration_s`.
- **Given** the tour is exited with Esc **when** it closes **then** screen and opened panels are restored.
- **Given** the repo **when** searched **then** no TTS / voice / `warm-voice` / JWLB `theme.css` / `design-system` content is present, and attribution to JWLB (and Risako's credit) is in CHANGELOG and the About box.

### Part C3 — Cross-store leaderboard + choice step

- **Given** the bundled export **when** the leaderboard renders **then** rows show store, model, chunking, size, retrieval, score and rank using the same ranking as the existing explorer, grouped by config key.
- **Given** runs differ in dataset, questions or config **when** grouped **then** they are never paired.
- **Given** timings are shown **when** rendered **then** they carry "indicative — runs were not timing-controlled" and no ordering by speed exists.
- **Given** the choice step **when** reached **then** Redis 8 runs are highlighted as the suggested pick; with Autoplay on, the suggestion is taken; the choice drives Part B.
- **Given** the sweep produced few overlapping configs **when** rendered **then** the leaderboard still renders and states the limit (fallback).

### Part D — Fallback

- **Given** `docs/about/RECORDING.md` **when** followed **then** a Next-by-Next recording is produced at the stated resolution and zoom from the seeded state; a copy is kept on a USB stick (owner action).

### Part H — Release v0.13.0 (+I, +F)

- **Given** all parts reviewed **when** the release is cut **then** `release.sh minor` produces `release/v0.13.0` and a PR; CHANGELOG `[Unreleased]` is promoted; `.github/ISSUE_TEMPLATE/{meetup-feedback,idea}.yml` exist and are linked from README and the About box; README "Built With" lists Redis and Elasticsearch and "Who is this for?" has a "Take the tour" row.
- **Given** the PR **when** the owner merges and tags `v0.13.0` **then** the QR/link resolves (Human step; never automated).

### Part J — Golden-master resources (blocked)

- **Given** a `<RAGAS_CODE_PATH>` is supplied **when** the doc is written **then** `docs/about/golden-master.md` explains how the Fed Loan golden master was built, states plainly that Ragas used an LLM once offline and sweeps stay zero-LLM, and About section 10 links it.
- **Given** no path is supplied **when** the slice closes **then** Part J is deferred and About section 10 is omitted.

---

## Before-Checks [GATE]

- [ ] On branch `slice/56-meetup-demo-kit`; `git status` clean; quality gates green on the starting commit.
- [ ] `docs/plan/invariants.md` and `DECISION-OWNERSHIP.md` re-read; owner confirmed JWLB reuse permission (#276).
- [ ] **Step 0:** `/healthz` OK; Pell PDF visible in the container (`/app/input_data/pdfs/`); inspect the volume DB (`docker cp rag-params-finder-server:/app/data/run_state.db <scratch>` read-only) to see which experiments it holds; Redis `maxmemory` headroom judged.
- [ ] **C1:** Docker/CI frontend build can read `docs/about/` (or the `prebuild` copy fallback is chosen); `marked` pinned to an exact version ≥2 weeks old and `npm audit` result recorded in DECISIONS, or the in-repo renderer fallback is chosen.
- [ ] **C2:** JWLB source files re-read at the commit being ported; list of files to port vs not port confirmed.

## After-Checks [GATE]

- [ ] All GWT scenarios above have ≥1 test (Specification coverage); essential error paths covered.
- [ ] `./scripts/ci/quality-gates.sh` green; frontend coverage 95/90/95/95 unchanged; backend floors unchanged.
- [ ] `ruff check .` and `ruff format --check .` pass on `scripts/demo/` (mypy/xenon/vulture do not cover `scripts/`).
- [ ] Complexity evidence: policy **reporting** for frontend (ESLint) and the export script; local report command and reviewer-summary location recorded in PROGRESS; baseline recorded.
- [ ] Browser at 1280 px and 390 px with Docker and the server stopped: About renders, Walkthru runs 5 steps by Next, Autoplay off by default, Esc restores, **no network requests**.
- [ ] `grep -ri "tts\|voice\|warm-voice" frontend/src/walkthru` → empty; attribution present.
- [ ] Export twice → identical bytes; manifest lists inputs, exclusions, ranking.
- [ ] Docs updated: CHANGELOG, README rows, `docs/README.md` index, this spec's Gate Status, PROGRESS.md, DECISIONS.md; Abstraction Views Delta appended to `docs/plan/GROWTH.md`.

### Closing Gates

- [ ] `nw-at-completeness-check` — AT completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline review (slice close gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data-flow review (gate #9, parallel): export reads run state only, no vector-store import; demo adapter has no network path
- [ ] `nw-documentarist-reviewer` — About copy is honest (similarity score, not correctness; "planned", not shipped)
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass (`docs/plan/gate-evidence/slice-56.json`)
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)

## Doc Audit

CHANGELOG `[Unreleased]` per part; README (Built With, Who is this for?, Issues link); About box attribution; `docs/about/RECORDING.md`; N/A with reason: `configuration.md` (no config change).

## Gate Status

📋 PLANNED — not started. Gate evidence will be `docs/plan/gate-evidence/slice-56.json` (do not create a `PASSED` stub before the executor writes real evidence).
