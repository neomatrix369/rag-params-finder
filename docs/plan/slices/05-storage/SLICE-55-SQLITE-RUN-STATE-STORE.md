# SLICE 55 — SQLite Central Run-State Store

**MoSCoW:** MUST
**Target time:** ~8–10 h
**Status:** 📋 PLANNED
**Depends on:** [49A](SLICE-49-VECTOR-STORE-PORT-SPLIT-REGISTRY.md) (`StorageBackend`/`VectorStore` port split, `store_factory.py`), [49B](SLICE-49B-VECTOR-STORE-DATA-PATH-REWIRE.md) (pairing rule (ii), two-store `/healthz`)
**Branch:** `slice/55-sqlite-run-state-store`
**Feature:** SQLite run-state store (ADR-008) — **default-flip clause is PROVISIONAL**, see Non-goals

> **Origin (2026-09-29):** operator request to stop storing run/experiment metadata inside whichever engine hosts vectors — switching or scaling the vector backend currently drags run history with it, and Atlas free-tier quota is shared with non-vector data. Slices 49A/49B already split the *port* for run state (`StorageBackend`) from the port for vectors (`VectorStore`); this slice adds a new, dedicated, run-state-**only** provider (SQLite) behind the existing `StorageBackend` port — the mirror of how Slice 50 added Elasticsearch as a vector-**only** provider. Interview + four-reviewer (`nw-solution-architect-reviewer`, `nw-system-designer-reviewer`, `nw-troubleshooter-reviewer`, `nw-documentarist-reviewer`) desk-check captured in the approved plan at `/Users/swami/.claude/plans/currently-the-experiment-run-snoopy-bubble.md`.

---

## Context

`server/db/ports/storage.py`'s `StorageBackend` Protocol (experiment/run/result CRUD, cascade delete, boot reconciliation, dashboard stats helpers) is already independent of `server/db/ports/vector_store.py`'s `VectorStore` Protocol. `server/db/ports/store_factory.py::get_storage_backend()` resolves `STORAGE_BACKEND` via a small if/elif (`mongodb` → `MongoStorageBackend`, `postgres` → `PostgresStorageBackend`); this slice adds a third branch (`sqlite` → `SQLiteStorageBackend`) and flips the default.

- **Depends-on outputs:** 49A's `StorageBackend`/`store_factory` seam; 49B's pairing rule (ii) and two-store `/healthz` shape (this slice extends both, it does not replace them).
- **Invariants pointer:** `docs/plan/invariants.md` § Vector store / split-store — this slice adds a run-state-only provider row to that section (mirroring the vector-only Elasticsearch row).
- **ADR:** [`ADR-008-sqlite-central-run-state-store.md`](../../adr/ADR-008-sqlite-central-run-state-store.md) — records the decision and the partial supersession of ADR-004/DECISIONS #130.

## Non-goals

- No change to `VECTOR_STORE_BACKEND`'s provider registry, the vector-store pairing rule for engines that *can* host run state (mongodb/postgres as vector stores), or any vector-store adapter. Chunks/vector data are never touched by this slice's migration or drop step.
- No removal of `StorageBackend` method implementations from `MongoStorageBackend`/`PostgresStorageBackend` — separate follow-up cleanup, tracked in Forward Roadmap, not this slice.
- No formal deprecation of `mongodb`/`postgres` as `STORAGE_BACKEND` choices — they remain fully supported, explicit, non-default choices after this slice.
- **The default-flip itself is PROVISIONAL.** This slice ships `STORAGE_BACKEND` defaulting to `sqlite` (per ADR-008), but a follow-up slice must confirm or revisit that default once it has real-world mileage — this slice's Gate Status must not be read as "the sqlite default is permanent."
- No multi-process/multi-replica run-state story — SQLite here assumes one server process (see ADR-008 Consequences).

## Output contract

### New provider: `sqlite` (run-state-only, mirror of Elasticsearch's vector-only)

| # | Surface | Behaviour |
|---|---|---|
| 1 | `server/settings.py::_KNOWN_STORAGE_BACKENDS` | Adds `"sqlite"` |
| 2 | `server/settings.py::storage_backend` | Default changes `"mongodb"` → `"sqlite"` |
| 3 | `server/settings.py` (new) | `sqlite_db_path: str = "./data/run_state.db"` |
| 4 | `server/settings.py::vector_store_backend_pairing_rule()` | New `_RUN_STATE_ONLY_BACKENDS = frozenset({"sqlite"})`. When `storage_backend` is in that set and `vector_store_backend` was left empty, raise a specific error naming the requirement to set `VECTOR_STORE_BACKEND` explicitly — instead of falling through to the generic "unknown vector store" message |
| 5 | `server/settings.py::ensure_storage_ready()` / `_ensure_backend_uri_present()` | `sqlite` branch: no required env var (working default path); ensures the parent directory is creatable/writable |
| 6 | `server/db/ports/store_factory.py::get_storage_backend()` | New `sqlite` branch returning `SQLiteStorageBackend`; error message on the fallback `ValueError` lists `sqlite` alongside `mongodb`/`postgres` |
| 7 | `server/core/guards/health_check.py` | New `_is_sqlite_backend()` — **direct string comparison (`backend == "sqlite"`), not `resolve_adapter()`-based**, because SQLite is never registered in the vector-store registry and `resolve_adapter("sqlite")` would raise. New `sqlite_health_status()` (ok if the file/directory is writable — no network ping). Both wired into `_probe_store()` / `resolve_storage_mode()` / `_storage_mode_for()` |
| 8 | `docker-compose.yml` (+ `docker-compose.dev.yml` if it overrides volumes) | Volume mount for the SQLite file path, matching the existing `mongodb_local_data` / `postgres_local_data` pattern |
| 9 | Server boot (`server/main.py` lifespan or equivalent) | New upstream-warning check: if `STORAGE_BACKEND` resolves to `sqlite`, the SQLite file is new/empty, and `MONGODB_URI`/`DATABASE_URL` is present in the environment, log a prominent warning naming the migration script |

### New adapter: `SQLiteStorageBackend`

- `server/db/sqlite/sqlite_store.py` — implements every `StorageBackend` Protocol method (`server/db/ports/storage.py:19-167`), following `PostgresStorageBackend`'s promoted-columns-plus-JSON-blob pattern (`server/db/postgres/postgres_store.py`, `server/db/postgres/postgres_docs.py`). SQLite has no native JSONB, so non-promoted fields are a `TEXT` column via `json.dumps`/`json.loads`.
- `server/db/sqlite/sqlite_docs.py` — row↔doc mapping, mirroring `postgres_docs.py`.
- `server/db/sqlite/schema.sql` — `experiments`, `run_status`, `results` tables only (**no `chunks` table** — SQLite never hosts vectors), same promoted-column shape as `server/db/postgres/schema.sql`. Every connection applies `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000` (required — see concurrency note below).
- Reuses `server/db/ports/stats_common.py` for the backend-agnostic parts of `get_experiment_db_stats`/`get_vector_db_stats_grouped`, same as Postgres does.

### Concurrency (correction from `nw-system-designer-reviewer`)

The server process is the sole writer (CLI talks to it over HTTP; ADR-001), but *within* that process `SWEEP_EXECUTOR` (background sweep thread) and `HEAVY_READ_EXECUTOR` (concurrent-read pool) both touch run state concurrently today, even with `parallelism: 1`. SQLite's default rollback-journal mode serializes writers and can raise `SQLITE_BUSY` under this pattern — WAL mode + `busy_timeout` is a correctness requirement for this slice, not an optimization.

### Migration script

`scripts/migrate/migrate_run_state_to_sqlite.py`:

1. **Copy**: reads the *current* `get_storage_backend()` (whatever `STORAGE_BACKEND` resolves to before this slice's default takes effect) via existing Protocol methods (`find_all_experiments`, `find_run_statuses` per experiment, `find_results_for_experiment`); writes each into a target `SQLiteStorageBackend`. Idempotent (skip rows that already exist by primary key) — safe to re-run.
2. **Verify**: compares a hash of primary keys between source and target for all three collections/tables (not a count-only check — a count-only check can't catch a corrupted or partially-written row).
3. **Backup**: writes a timestamped JSON export of the source data to a local backup file — always, independent of the `--drop-source` flag.
4. **Drop (opt-in)**: only if verification passes **and** `--drop-source` is explicitly passed, deletes the source `experiments`/`run_status`/`results` collections (Mongo) or tables (Postgres). `chunks`/vector data is never touched, regardless of flags.

### Operational sequence (what an operator actually runs, per environment)

1. Deploy this slice's code — no behavior change yet if `STORAGE_BACKEND` is already set explicitly in that environment. (If left unset, the new default takes over and the boot warning from row 9 above fires if there's evidence of prior Mongo/Postgres run-state data.)
2. Run the migration script without `--drop-source` — copies + verifies + backs up.
3. Set `STORAGE_BACKEND=sqlite` explicitly and `VECTOR_STORE_BACKEND` explicitly to whichever engine holds vectors; restart the server. All new experiment runs now write run-state to SQLite only; vectors are unaffected.
4. Confirm dashboard/CLI history is identical pre/post cutover.
5. Only after step 4, re-run the migration script with `--drop-source` to drain the old run-state collections/tables (chunks in that same engine are left alone).

## Reuse ledger

| Need | Existing code to reuse/extend | Action |
|---|---|---|
| Port/Protocol | `server/db/ports/storage.py::StorageBackend` | **Reuse** — new adapter implements it unchanged |
| Factory wiring | `server/db/ports/store_factory.py::get_storage_backend()` | **Extend** with a third branch |
| Provider-capability pattern | `server/db/ports/registry.py::_CAN_HOST_RUN_STATE` (vector-only precedent: Elasticsearch) | **Mirror** — SQLite is the run-state-only inverse; new `_RUN_STATE_ONLY_BACKENDS` lives in `settings.py` since sqlite is never a vector-store registry entry |
| Adapter shape | `server/db/postgres/postgres_store.py` + `postgres_docs.py` (promoted columns + JSON blob) | **Reuse pattern**, new module |
| Stats assembly | `server/db/ports/stats_common.py` | **Reuse**, same as Postgres |
| Health probe | `server/core/guards/health_check.py` | **Extend** with a third backend branch |
| Boot reconciliation | `server/core/pipeline/startup_reconciliation.py` | **Reuse unchanged** — works against whatever `get_storage_backend()` resolves to |
| Docker volumes | `docker-compose.yml` (`mongodb_local_data`, `postgres_local_data` patterns) | **Mirror** for the sqlite file path |
| **Net-new (only)** | `SQLiteStorageBackend`, `sqlite_docs.py`, `schema.sql`, migration script, boot upgrade-path warning | Write new |

---

## Slice Workflow Bundle

- Slice name: `slice-55-sqlite-run-state-store`
- Branch: `slice/55-sqlite-run-state-store`
- Order:
  1. **RED:** first commit adds the end-to-end migration-sequence acceptance test (copy → cutover → parity → drop) against a seeded in-memory/test Mongo double, failing because `SQLiteStorageBackend` doesn't exist yet.
  2. Schema + `SQLiteStorageBackend` + `sqlite_docs.py` (GREEN on unit adapter tests).
  3. `store_factory.py` wiring + `settings.py` validator/pairing-rule changes + `health_check.py` wiring.
  4. Migration script (copy, hash-verify, backup, opt-in drop).
  5. Boot upgrade-path warning.
  6. Docker Compose volume mount.
  7. Docs: ADR-008 (already drafted), this slice spec, `docs/user-guide/sqlite-setup.md`, `CLAUDE.md`, `docs/plan/invariants.md`.
  8. GREEN across the full suite; default flip lands last so the bulk of the work is reviewable against the old default.
- Commit pattern: `feat(storage): add SQLite run-state provider; flip STORAGE_BACKEND default (ADR-008)`
- **Doc exit (Must):** `invariants.md` § Vector store / split-store gains a run-state-only row; `CLAUDE.md` backend-switching table adds `sqlite`; `docs/user-guide/sqlite-setup.md` written; `docs/plan/slices/PROGRESS.md` Slice 55 row + Decision Log + Forward Roadmap (PROVISIONAL on the default); `docs/plan/DECISIONS.md` new entries recording the ADR-004 partial supersession.

---

## Spec (GWT)

```
Scenario: A fresh install defaults to SQLite with no external service
  Given no STORAGE_BACKEND set, no MONGODB_URI or DATABASE_URL set
  When the server boots
  Then GET /healthz shows stores.run_state.provider == "sqlite" and ok == true
    And no network dependency is required for the run-state store

Scenario: SQLite cannot default as the vector store
  Given STORAGE_BACKEND=sqlite and VECTOR_STORE_BACKEND unset
  When settings validate
  Then a clear error names the requirement to set VECTOR_STORE_BACKEND explicitly
    (not the generic "unknown vector store" message)

Scenario: SQLite paired explicitly with an existing vector store works
  Given STORAGE_BACKEND=sqlite and VECTOR_STORE_BACKEND=mongodb
  When settings validate and the server boots
  Then experiments write run-state to SQLite and chunks to Mongo, unchanged from before this slice

Scenario: End-to-end migration sequence (copy -> cutover -> parity -> drop)
  Given an existing environment on STORAGE_BACKEND=mongodb with experiments, runs, and results
  When migrate_run_state_to_sqlite.py runs without --drop-source
  Then hash verification passes and a timestamped backup JSON is written
    And the source Mongo collections are untouched
  When STORAGE_BACKEND is then set to sqlite and the server restarts
  Then the dashboard/CLI shows identical experiment history to before cutover
  When migrate_run_state_to_sqlite.py then runs with --drop-source
  Then the source experiments/run_status/results collections are gone
    And the source chunks collection is untouched

Scenario: Migration refuses to drop on a verification mismatch
  Given a migration where the target's primary-key hash does not match the source
  When migrate_run_state_to_sqlite.py runs with --drop-source
  Then it refuses to drop, reports the mismatch, and the source is untouched

Scenario: Upgrade-path warning fires for an existing deployment
  Given STORAGE_BACKEND unset (so it defaults to sqlite), a new/empty SQLite file
    and MONGODB_URI present and pointing at an environment with existing experiments
  When the server boots
  Then a prominent warning is logged naming the migration script

Scenario: Concurrent sweep write and dashboard read do not error
  Given a running sweep (SWEEP_EXECUTOR writing run-state updates)
  When GET /experiments is polled concurrently (HEAVY_READ_EXECUTOR)
  Then no SQLITE_BUSY error occurs and both operations complete

Scenario: Docker Compose persists run-state across a container restart
  Given a server running in Docker Compose with STORAGE_BACKEND=sqlite
  When an experiment is created, the container is stopped and restarted
  Then the experiment is still visible (the sqlite file path is a mounted volume)

Scenario: Explicit mongodb/postgres STORAGE_BACKEND still works unchanged
  Given STORAGE_BACKEND=mongodb (explicitly set)
  When the server boots and an experiment runs
  Then run-state is written to Mongo exactly as before this slice — no behaviour change
    for an operator who does not opt into sqlite
```

---

## Before-Checks [GATE]

- [ ] 49A + 49B ✅ / merged; `StorageBackend`/`store_factory`/pairing-rule code present as described.
- [ ] `docs/plan/DECISIONS.md` next free entry number confirmed (was #259 → this slice starts at #260); ADR number confirmed free (ADR-007 is reserved for Redis per #221 → this slice uses ADR-008).
- [ ] harness-scout `detect_confirm` at slice start (touches settings, store_factory, health_check, boot, Docker Compose).

## After-Checks [GATE]

- [ ] All GWT scenarios above green, including the single end-to-end migration-sequence scenario (not just its individual pieces in isolation).
- [ ] Existing 49A/49B characterization records unchanged for explicit `mongodb`/`postgres` `STORAGE_BACKEND`.
- [ ] Coverage floors hold; complexity per `./scripts/ci/quality-gates.sh`.
- [ ] `docs/plan/gate-evidence/slice-55.json` with coverage/complexity fields.

### Closing Gates

- [ ] `nw-solution-architect-reviewer` — architecture/pattern review (desk-check already run pre-implementation against the plan; re-run against the actual diff)
- [ ] `nw-system-designer-reviewer` — infra/concurrency/Docker review (desk-check already run pre-implementation against the plan; re-run against the actual diff)
- [ ] `nw-troubleshooter-reviewer` — risk/failure-mode review, especially the migration+drop sequence (desk-check already run pre-implementation against the plan; re-run against the actual diff)
- [ ] `nw-documentarist-reviewer` — ADR-008 + this slice spec doc-quality review (desk-check already run pre-implementation against the plan; re-run against the actual diff)
- [ ] `/verify-slice`

## Gate Status

📋 PLANNED — spec authored 2026-09-29 from the approved interview + 4-reviewer desk-check plan (`/Users/swami/.claude/plans/currently-the-experiment-run-snoopy-bubble.md`). No code yet. Default-flip clause is PROVISIONAL (see Non-goals) — a follow-up slice must confirm or revisit it.
