# Slice 27 — MongoDB Mode Indicator (Cloud vs Local)

> **📦 DEFERRED / SUPERSEDED (2026-07-09):** Standalone Mongo cloud vs local indicator is **absorbed into Slice 36** (`storage mode`: `mongo` | `local-postgres` | `supabase`). Keep this spec as historical scope; implement mode visibility in [`SLICE-36-POSTGRES-PREFLIGHT-STATS.md`](SLICE-36-POSTGRES-PREFLIGHT-STATS.md). Re-open 27 only if post-cutover Mongo-only operators need a badge without Postgres modes.

**Status**: 📦 DEFERRED *(superseded by Slice 36)*
**Depends on**: 25B
**Branch**: `slice/27-mongodb-mode-indicator`
**Estimated time**: ~2 h

## Problem

No surface in the system clearly tells the operator whether they are connected to
MongoDB Atlas cloud or Atlas Local Docker — except `VectorDbStatsPanel`, which only
appears after an experiment has run. If the server is accidentally pointed at the
wrong backend, there is no fast feedback path.

## Goal

Every surface a developer touches during a session clearly shows the active backend
mode — without requiring a completed experiment.

## Single Source of Truth

`get_mongodb_mode(uri: str) -> Literal["cloud", "local"]` in
`server/db/mongodb_uri.py`, wrapping the existing `is_atlas_uri()`. All other changes
read from this one function. `cluster_name` is derived via the existing
`parse_atlas_cluster_name()` from the same file.

## Storage Limit — Local Mode

**Problem** (confirmed from screenshots): The Experiments page shows "91.2 MB free / of 512 MB
cluster quota" even for `localhost:27017` (the manual `MONGODB_STORAGE_LIMIT_MB` override
leaks through). The per-experiment Vector Database panel shows no free-storage figure at all.

**Correct source of truth**: MongoDB's own `dbStats` command returns `fsTotalSize` and
`fsUsedSize` — the total and used bytes of the filesystem that backs `/data/db`. For the
`mongodb_local_data` Docker volume (see `docker-compose.yml:118`), this reflects the Docker
volume's filesystem capacity, not the host Mac's disk. No Docker API calls or `shutil` needed.

**Fix**:

- `resolve_tier_specs()` (`atlas_storage.py`) — when `not is_atlas_uri()`, return a signal dict
  `{"instance_size": "local", "tier_type": "local", "storage_mb": None, ...}` instead of `None`.
  **Skip the manual override for local mode** — the override is Atlas-specific.

- `_mongodb_cluster_storage_mb()` (`experiments_shared.py`) — when `tier_type == "local"`:
  use `fsTotalSize`/`fsUsedSize` from the already-fetched `dbStats` dict:
  `database_storage_limit_mb = fsTotalSize / 1024²`, `database_free_mb = (fsTotalSize - fsUsedSize) / 1024²`

- `VectorDbStatsPanel.tsx` — when `cluster_tier_type === "local"`, use local-specific copy:
  - `'of X MB cluster quota'` → `'of X MB volume filesystem'`
  - `'Cluster storage'` → `'Local disk storage'`
  - `label="Cluster quota"` → `label="Volume size"`

## Acceptance Criteria

- [ ] `GET /healthz` returns `{"ok": ..., "mongodb": ..., "mongodb_mode": "cloud"|"local", "cluster_name": str|null}`
- [ ] `GET /health` returns the same two new fields
- [ ] Experiment `sweep_summary` stored in MongoDB includes `mongodb_mode`
- [ ] Submit response (`POST /experiments`) includes `mongodb_mode`
- [ ] CLI submit banner shows `Database: Atlas Local (Docker)` or `Database: Atlas Cloud`
- [ ] CLI final result summary shows `Database:` row in Metadata section
- [ ] Dashboard header shows a mode badge on all screens (green `Local` / blue `Cloud (cluster)`)
- [ ] Badge is absent/hidden when `/healthz` fetch fails (no crash, graceful degradation)
- [ ] `VectorDbStatsPanel` (Experiments page) shows storage bar in local mode backed by Docker volume filesystem (`dbStats.fsTotalSize`)
- [ ] Per-experiment Vector Database panel shows free-storage in local mode
- [ ] Labels say "Local disk storage" / "Volume size" / "of X MB volume filesystem" (not "cluster quota")
- [ ] Manual `MONGODB_STORAGE_LIMIT_MB` override does NOT affect local mode display
- [ ] All existing tests pass; `ruff`, `mypy`, frontend typecheck, build all clean

## Files Changed

| File | Change |
|------|--------|
| `server/db/mongodb_uri.py` | + `get_mongodb_mode()` |
| `server/main.py` | + `mongodb_mode` + `cluster_name` in `/healthz` + `/health` |
| `server/api/experiments.py` | + `mongodb_mode` in `sweep_summary` + submit response |
| `server/core/atlas_storage.py` | `resolve_tier_specs()` — return `{"tier_type":"local",...}` instead of `None`; skip manual override for local mode |
| `server/api/experiments_shared.py` | + local-mode `fsTotalSize`/`fsUsedSize` path in `_mongodb_cluster_storage_mb()` |
| `frontend/src/components/VectorDbStatsPanel.tsx` | local-mode label copy: "Volume size", "Local disk storage", "of X MB volume filesystem" |
| `cli/main.py` | + Database row in submit banner + `_print_summary()` (mode label only, no cluster name) |
| `frontend/src/types/index.ts` | + `HealthResponse` (with `cluster_name: string \| null`); + `mongodb_mode?` on `SweepSummary` |
| `frontend/src/services/apiClient.ts` | + `getHealth()` |
| `frontend/src/App.tsx` | + fetch health on mount, pass `mongoDbMode` + `clusterName` as props |
| `frontend/src/components/MongoDbModeBadge.tsx` | new — pill badge (green Local / blue Cloud) |
| `frontend/src/components/ExperimentsScreen.tsx` | pass badge to `AppPageChrome` `topRight` |
| `frontend/src/components/ExperimentDetailScreen.tsx` | pass badge to `AppPageChrome` `topRight` |

## After-Checks

- [ ] `./scripts/quality-gates.sh` pass
- [ ] Specification coverage: every acceptance criterion has ≥1 test; badge graceful-degradation path covered
- [ ] Branch coverage: 100% target for `get_mongodb_mode()` and storage-limit branching; exclusions documented (test-writing-craft-quality.mdc §12)
- [ ] Mutation testing: survival budget met if slice is feature-complete (§23)
- [ ] Manual: start `--local` → badge shows "Local"; start without `--local` → badge shows "Cloud"

## Commits

```
feat(slice-27): add mongodb_mode to health endpoints + experiment surfaces
feat(slice-27): mongodb mode badge in dashboard header
```
