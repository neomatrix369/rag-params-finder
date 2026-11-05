# SLICE-65 — Single SQLite Run-State Source of Truth

**Status:** 📋 PLANNED
**MoSCoW:** Must (65-0, 65A, 65B, 65D) · Must-after-66 (65C)
**Depends-on:** SLICE-55 (SQLite StorageBackend), SLICE-56 merged (PR #258)
**Estimated effort:** ~16–24 h across all sub-slices
**Planned date:** 2026-11-05

---

## Context

Two SQLite run-state files exist:
- **Docker named volume** `rag-params-finder_sqlite_run_state` mounted at `/app/data` — written by the containerised server; holds the Redis sweep experiments.
- **Host file** `data/run_state.db` — written by host `uvicorn` runs; holds 21 experiments / 1163 run_status rows / 86,779 results (~530 MB).

The dashboard (served from Docker) cannot see the host experiments. Slice 56 worked around this with a multi-DB exporter (`scripts/walkthru/export_walkthru_results.py`, DECISIONS #278). The goal of this slice is **one DB file, read and written by every component, no second copy ever created**.

DECISIONS governing this slice start at **#301**. The spike sub-slice (65-0) records the architecture decision before any code changes.

Non-goals:
- Merging vector stores (each store is independent; run state is the only target).
- Upgrading the SQLite storage schema (structural changes are a separate concern).
- Running the merge while any sweep is active.

---

## Sub-slices (execution order: 65-0 → 65A → 65B → 65D → 66 → 65C)

### 65-0 · Spike + human decision (Must, first)

On this Mac, run a container writer and a host reader against a bind mount (`./data:/app/data`) with `PRAGMA integrity_check` after a `kill -9`; record Docker Desktop version and backend (virtiofs/gRPC-FUSE). Then record in DECISIONS one of:

- **(a)** Bind mount + one-server rule: `./data:/app/data`, WAL OK on this Mac.
- **(b) Recommended:** Keep the DB in the named volume; merge the host DB into it; host tools access via `docker exec` backup API + `docker cp`. Safe for WAL.
- **(c)** Bind mount with a non-WAL journal under Docker (needs an ADR-008 amendment).

**Oracle:** DECISIONS row with spike evidence (Docker Desktop version, backend, `integrity_check` result under concurrent load and after kill -9).

---

### 65A · Verified backups + merge script (Must)

#### Backups (B1 — before merge, B2 — inside cutover)

**B1 — watcher + automatic backup when the Redis sweep completes:**
Poll `GET localhost:8001/experiments/08313427-4ee6-4c66-9841-e944fbf8bb33` until terminal (complete, failed, partial, cancelled). Require two consecutive terminal polls 30 s apart before backing up. Hard 6 h timeout with explicit "watcher timed out, no backup taken" message. Run the backup inside the container with the SQLite backup API into `/tmp`, then `docker cp` to `~/backups/rag-params-finder-run-state-<YYYYMMDD-HHMMSS>/volume_run_state.db`. Delete the `/tmp` copy. Nothing is kept inside the container. No copy under `data/` (a bind mount would expose it in the container build context; `data/` goes in `.dockerignore` in 65B).

Verification order on each backup:
1. `PRAGMA journal_mode=DELETE` on the copy.
2. `PRAGMA integrity_check` = ok.
3. Row counts (experiments / run_status / results) equal the live source counts at the same moment (stable after the sweep ends).
4. Write `MANIFEST.txt` (source, timestamp, counts, experiment ids) and `SHA256SUMS`.
5. Only then `chmod a-w`.

Host DB: make a fresh copy into the same timestamped folder with the backup API (not a plain `cp`; a host uvicorn may have it open), with its own manifest.

Hard rule: the original host file and the Docker volume are **never** deleted or overwritten by any step. Dropping the volume is a final manual step the user triggers.

**B2 — final backups inside the cutover:** repeat B1 for both DBs at the start of the maintenance window. The merge script refuses to run without a verified manifest for both.

#### Merge script

New `scripts/migrate/merge_run_state_dbs.py`. Dry-run default, `--execute`, `--backup-manifest PATH`.

Design:
- **Host DB is the base**: copy it to `run_state.merged.db` with the backup API.
- `ATTACH` the verified volume copy.
- Move only the volume's experiments (whole-experiment granularity in one transaction, `foreign_keys=ON`).
- Do not copy results via a Python loop (`doc` column totals ~425 MB). Use `INSERT INTO … SELECT … FROM attached.*` in SQL.
- Explicit column lists, never `SELECT *`. Never copy `result_id` (autoincrement, no natural key).
- Collision rule: if an `experiment_id` exists in both: equal content digest → skip; different → abort (uuid4 collisions are practically impossible, so any collision is a hard stop).
- Schema parity: assert `PRAGMA table_info` equality for all three tables on both sources and the target. Older volumes may lack columns such as `vector_store_snapshot`; fail with a clear message rather than silently skipping.
- Idempotency: second run with the same inputs is a no-op.
- Precondition: no experiment with `status = 'running'` (stop the server first).
- Done = exactly 23 experiments with per-experiment run/result counts matching the sources.
- Excludes `*_backup*.db`, `*.merged.db` from source scanning.
- Does not import `_drop_source_*` helpers from the existing migrate script. No `--drop-source` flag.

Promotion step (separate `--promote` flag):
- `wal_checkpoint(TRUNCATE)` and `journal_mode=DELETE` on the merged file.
- Move the old `.db`, `-wal`, `-shm` together to a timestamped folder.
- Move the merged file in. Nobody deletes `-wal`/`-shm` by hand.

**Oracle (65A):** dry-run report correct; second run changes nothing; target has exactly 23 experiments with source-matching per-experiment counts; refuses to run without a verified manifest.

---

### 65B · Cutover + compose + guard + static test (Must)

#### Cutover runbook (one maintenance window)

1. `docker compose stop server` (not `down`, never `down -v` / `volume prune`: that destroys the only copy of the volume DB).
2. Take the final backups (B2) with `docker run --rm -v rag-params-finder_sqlite_run_state:/d:ro` plus a host-mounted `~/backups` path and a pinned python image: copy the volume triplet to scratch, open the copy read-write so SQLite recovery applies the WAL, `wal_checkpoint(TRUNCATE)`, `integrity_check`, then the backup API. Same for the host DB. Verify manifests.
3. Merge (dry-run, then `--execute`), verify counts and key hashes.
4. `--promote`; update compose; `up`; verify `/experiments` count and `find / -name 'run_state*.db'`.
5. Rollback: until the first post-cutover write, revert compose and restore the renamed originals. After that, roll forward only. Keep the old volume undropped for N days.

#### Compose change (chosen option from 65-0)

For **option B (bind mount):**
- `./data:/app/data` replaces the named volume in `docker-compose.yml`.
- `stop_grace_period: 30s` added so SIGTERM allows WAL checkpoint before SIGKILL.
- `SQLITE_DB_PATH=/app/data/run_state.db` set explicitly in the compose env.
- Concurrency rule: host tools refuse to open the DB while the server is up (non-empty `-wal` check). Only one process writes at a time.
- Linux ownership note: container runs as root; create `data/` as the host user first (`mkdir -p data && touch data/.gitkeep`).
- Soak test: concurrent writer (server) + host reader, `kill -9`, `integrity_check` — recorded in DECISIONS.

For **option A (volume stays):**
- Named volume unchanged. `SQLITE_DB_PATH=/app/data/run_state.db` explicit in compose.
- Host tools access via `docker exec` / `docker cp` only. Docs updated accordingly.

#### Duplicate-prevention guard

The real duplicate-creation hole is the relative default `./data/run_state.db`, which resolves against the working directory (running `uvicorn` elsewhere silently creates a second DB).

Changes:
- Anchor the default in `server/settings.py` to the repo root: `Path(__file__).resolve().parents[1] / "data" / "run_state.db"`.
- Set `SQLITE_DB_PATH=/app/data/run_state.db` explicitly in compose (all variants).
- No sibling-DB heuristic (would misfire on backups and test overrides).
- Optional opt-in guard: `RUN_STATE_DB_MUST_EXIST=1` (set by `start-services.sh` after init) makes `server/main.py` fail closed instead of creating the file, with a test.
- Boot log: resolved path, inode, journal mode, DB and `-wal` size, `quick_check`, counts. Surface in `/healthz` → `stores.run_state`.

#### Shutdown checkpoint

`lifespan` shutdown hook: fresh connection, `wal_checkpoint(TRUNCATE)`. `stop_grace_period: 30s` in compose (today nothing checkpoints or closes).

#### Static "no duplicate DB" test

`tests/scripts/test_run_state_single_source.py` (PyYAML already a dependency):
- Parses all `docker-compose*.yml`: no extra top-level volume named `*sqlite*`/`*run_state*` beyond the chosen option's one; `/app/data` target defined once, not redefined in the dev overlay; `SQLITE_DB_PATH` only `/app/data/run_state.db`.
- Scoped text scan of compose, `start-services.sh`, `scripts/**`, `scripts/lib/*.tsv`, workflows for `sqlite_run_state` / `docker volume (create|rm).*sqlite`; allowlist only the merge script.
- Docs/ADR/DECISIONS excluded.
- States its limit: static only; runtime check is `find / -name 'run_state*.db'` (host and container) plus the boot log.

#### `.dockerignore`

Add `data/` to `.dockerignore` (not present today). The static test asserts `data/` is in both `.gitignore` and `.dockerignore`, and `git ls-files | grep -E '\.db(-wal|-shm)?$'` is empty.

**Oracle (65B):** `/healthz` shows the one DB path and `quick_check: ok`; `find / -name 'run_state*.db'` (host and container) finds only the expected file(s); static test fails if a second volume or path appears.

---

### 65D · Docs sweep (Must)

Using the real reference set only:

| File | Change |
|---|---|
| `docker-compose.yml:57,266` | Reflect option A or B from 65B |
| `docs/user-guide/sqlite-setup.md:61-76` | Replace `docker cp` advice (misses `-wal`) with `.backup` recipe; add Linux vs macOS row |
| `docs/adr/ADR-008-sqlite-central-run-state-store.md` line 29 | Update volume / mount note |
| `docs/plan/slices/05-storage/SLICE-55-SQLITE-RUN-STATE-STORE.md` line 3 | Cross-reference to SLICE-65 |
| `docs/plan/slices/02-dashboard/SLICE-56-MEETUP-DEMO-KIT.md` lines 31, 100, 164 | Note superseded by SLICE-65 where relevant |
| `docs/plan/DECISIONS.md` #278/#285 | Annotate as superseded by #301+ |
| `docs/plan/slices/PROGRESS.md` line ~781 | Add 65/66 rows |
| `docs/plan/HANDOFF.md` line ~14 | Reflect unified DB |
| `CLAUDE.md` ~line 78 | Update volume/mount note |

History files are annotated, not rewritten. `docs/contributor-guide/local-environment.md`, `CLAUDE.local.md`, `start-services.sh` need no change (grep-verified on main).

65D must **not** touch exporter docs (`scripts/walkthru/export_walkthru_results.py:10,15`, SLICE-56 exporter lines); those go in 65C.

**Oracle (65D):** `grep -r 'sqlite_run_state\|docker cp' docs/ scripts/ CLAUDE.md` hits only allowed history files and the unrelated `scripts/docker/aim-ui.sh:35`.

---

### 66 · Live cross-store compare and leaderboard (Should, prerequisite for 65C)

> See `SLICE-66-LIVE-CROSS-STORE-COMPARE.md` (stub, to be created).

Summary: one unified SQLite DB shows all 23 experiments (from multiple vector stores); the dashboard groups runs by config key (excluding `database_provider` + `data_paths` + `queries_file` + questions-file sha), calls `analyze_results` per group, and renders a cross-store leaderboard. No vector store needs to be running to view it.

**Detail screen rule (verified in code):** `GET /experiments/{id}`, `/results`, and `/explore` read run state only, so the Details tab always works. Only `GET /{id}/db-stats` (the "stored footprint" panel) and delete-cascade call `get_vector_store()`. Show the footprint panel only when the experiment's `database_provider` equals the server's active `VECTOR_STORE_BACKEND` (from `/healthz`) and that store is healthy; otherwise show a one-line note: "footprint unavailable: run on `<store>`, active store is `<x>`". Guard delete when the provider differs from the active store (removes run state but leaves chunks orphaned in the other store).

Known trade-off (record in DECISIONS): About/replay/leaderboard no longer work with the server off after 65C; a static snapshot can be re-added if an offline kit is needed again.

**Oracle (66):** `GET` compare endpoint ranks like-for-like groups with no vector store running; footprint panel hidden/noted when provider differs; delete is guarded.

---

### 65C · Retire the exporter (Must, after 66)

User decision 2026-11-05: the unified DB plus slice 66 replace the exporter.

Do NOT touch the exporter while 56 is in flight (already merged, so this gate is lifted).

Steps:
- Remove `scripts/walkthru/export_walkthru_results.py` and its test (`tests/scripts/test_export_walkthru_results.py`).
- Remove the `docs/about/walkthru-results.json` bundle step and the repeated-`--db` / `docker cp` guidance from docs.
- Supersede DECISIONS #278 (the multi-DB exporter decision).
- Update the Slice 56 spec to note superseded by 65C.
- Switch `frontend/src/walkthru/leaderboard.ts`, `replayAdapter.ts`, and the matching components in `frontend/src/components/walkthru/` from the bundled JSON to the live API data from 66.

**Oracle (65C):** `grep -r export_walkthru_results` returns nothing; leaderboard and replay render from the API.

---

## Output contract

- One `run_state*.db` path visible from both host and container after 65B.
- `/healthz` `stores.run_state` shows the resolved path, journal mode and `quick_check: ok`.
- Static test `tests/scripts/test_run_state_single_source.py` passes.
- After 65C: no exporter in the repo; leaderboard and replay render from the unified DB via the API.

---

## Closing Gates

- [ ] `nw-at-completeness-check` — AT completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline review (slice close gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data flow review (gate #9, parallel; covers merge script, WAL safety, duplicate-prevention guard, shutdown hook, options A/B)
- [ ] `nw-platform-architect-reviewer` — compose and Docker changes (65B)
- [ ] `nw-data-engineer-reviewer` — SQLite merge script correctness (65A)
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass → `docs/plan/gate-evidence/slice-65.json`
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)

Gate evidence at `docs/plan/gate-evidence/slice-65.json` per `GATE_CONTRACT.md`. Update PROGRESS.md, TRAIL.md, GROWTH.md at close.

---

## Not covered here

Planning Quality Lens (18 checks), AT oracle authoring (`nw-distill`), skill-proposer, harness-scout. These run at the start of the 65 branch execution.

---

## Verification (after all sub-slices)

1. `pytest tests/scripts tests/server/db -q`, `./scripts/ci/quality-gates.sh`.
2. `docker volume ls` shows no new `*sqlite_run_state*`; the old orphan volume remains until the user drops it. `curl localhost:8001/experiments` and the dashboard show 21 + 2 experiments (minus overlap).
3. Submit a small sweep; the new row appears in the one DB; `find / -name 'run_state*.db'` (host and container) finds only the expected file(s).
4. Until 65C runs: the exporter still works against the unified DB (two runs, identical bytes). After 65C it no longer exists.
