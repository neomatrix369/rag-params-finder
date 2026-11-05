# SLICE-66 — Live Cross-Store Compare and Leaderboard

**Status:** 🔨 IN PROGRESS (partial: compare endpoint + Compare sweeps button; footprint note and delete guard deferred)
**MoSCoW:** Should
**Depends-on:** SLICE-65 (single SQLite source of truth; must be cutover first)
**Estimated effort:** ~12–16 h (full slice)
**Planned date:** TBD (after 65B ships)

---

## Built so far (2026-11-05)

**Endpoint implementation** (`server/api/compare.py` + `server/core/compare.py`):
- `GET /api/v1/compare` groups runs by **same dataset + questions file (name+sha) + config** (ignoring `database_provider`), keeps latest per (store, group), ranks each group via `analyze_results` with min-max normalization within a group only
- Response: `{groups: [{group_id, runs[]}], stores, group_count, run_count, cross_store_group_count}`
- Reads run state only — works with no vector store healthy

**Dashboard** (on ExperimentsScreen; in progress, see PROGRESS.md for verification state):
- Added 'Compare sweeps' button; clicking calls the endpoint and renders a new compare view
- Reuses `CrossStoreLeaderboard` with loading/error/empty states
- Wired on click only (not on page load)

**Not built yet** (deferred):
- Detail screen: footprint unavailable note when `database_provider` ≠ active store
- Delete guard: warning about orphaned chunks in mismatched store
- Gate evidence: `docs/plan/gate-evidence/slice-66.json` (not created)
- SLICE-65C exporter retirement (blocks on this slice's full closure)

**Note:** A second spec `SLICE-66-REDIS-PER-RUN-CAPACITY-GUARD` shares the number 66 on branch `slice/66-redis-capacity-guard` — owner to renumber before merging.

---

## Context

After SLICE-65 unifies run state into one DB, all 23 experiments (from multiple vector stores) are visible to the server. This slice surfaces that in the dashboard: a cross-store compare view that groups like-for-like runs (same config except `database_provider`, `data_paths`, `queries_file`, and questions-file sha) and ranks them using `analyze_results`.

This also covers what the exporter's bundle gave Slice 56: per-run replay data and the leaderboard, now served live from the API. SLICE-65C retires the exporter once this slice ships.

Non-goals:
- Merging or migrating vector-store chunk data.
- Showing footprint/db-stats for stores not currently active.
- Offline / server-off mode (trade-off recorded in DECISIONS; a static snapshot can be re-added later).

---

## Output contract

- New `GET /api/v1/compare` endpoint: groups runs by config key (minus `database_provider` + `data_paths` + `queries_file` + questions-file sha), calls `analyze_results` per group (scores min-max normalised within a set, never across different datasets/questions), returns ranked groups.
- Dashboard cross-store leaderboard renders from `/compare` with no vector store running.
- Detail screen: footprint panel shown only when the experiment's `database_provider` matches the server's active `VECTOR_STORE_BACKEND` from `/healthz` and that store is healthy; otherwise a one-line note: "footprint unavailable: run on `<store>`, active store is `<x>`".
- Delete guard: when `database_provider` differs from the active store, delete removes run state but warns that chunks in the other store are orphaned.

---

## Acceptance criteria (draft)

- **Given** the unified DB holds experiments from multiple stores **when** `GET /api/v1/compare` is called **then** runs are grouped by like-for-like config and each group is ranked, with no vector store running.
- **Given** a detail screen for a Redis experiment **when** the server is configured for MongoDB **then** the footprint panel shows the "footprint unavailable" note, not an error.
- **Given** a delete request for an experiment whose `database_provider` differs from the active store **then** the response warns about orphaned chunks before proceeding.

---

## Closing Gates

- [ ] `nw-at-completeness-check` — AT completeness audit
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data flow review (compare endpoint, footprint rule, delete guard)
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions → `docs/plan/gate-evidence/slice-66.json`
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE

---

## Notes

Reuses the exporter's grouping rule (same config-key logic as `scripts/walkthru/export_walkthru_results.py`). After this slice ships, SLICE-65C removes the exporter and switches `frontend/src/walkthru/leaderboard.ts` and `replayAdapter.ts` to the live API.
