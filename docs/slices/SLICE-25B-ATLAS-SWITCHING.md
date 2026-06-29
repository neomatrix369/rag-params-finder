# SLICE 25B — Seamless Atlas Backend Switching

**MoSCoW:** SHOULD *(Slice 25 added local Atlas; this slice makes cloud ↔ local switching a single-command operation)*
**Target time:** ~1 h
**Status:** ✅ COMPLETE — 2026-06-29
**Depends on:** [Slice 25 — Atlas Local Dev Mode](SLICE-25-ATLAS-LOCAL.md)

---

## Goal

A developer should be able to switch between Atlas cloud and MongoDB Atlas Local with a single flag change — no `.env` edits, no compose file surgery, no manual URI management. The two backends must be interchangeable: same CLI commands, same configs, same dashboard URL.

---

## Problem (before this slice)

After Slice 25 the local Atlas container worked, but switching required:
- Remembering a long `docker compose -f … -f … --profile local-atlas up -d` command
- Manually setting `MONGODB_URI` in `.env` or shell for the CLI
- No guidance on when/how to switch back

---

## Acceptance Criteria

- [x] `./start-services.sh --local` starts the full stack (server + dashboard + local Atlas) in one command
- [x] `RAG_LOCAL_ATLAS=1 ./start-services.sh` is the env-var equivalent (CI/script-friendly)
- [x] `./start-services.sh` (no flag) is unchanged — still starts the cloud stack, same as before
- [x] `./scripts/local-atlas.sh start` starts only the MongoDB container (for native server/frontend dev)
- [x] `./scripts/local-atlas.sh stop|reset|status` manage the container lifecycle
- [x] `--local` prints the CLI `MONGODB_URI` to the terminal at the end (no need to look it up)
- [x] `--local` skips the cloud Atlas URI validation in `.env` (overlay provides the URI for the server)
- [x] Port 27017 is included in the port-conflict check when `--local` is active
- [x] `./scripts/quality-gates.sh` passes — 0 ruff / mypy / pytest regressions
- [x] `docs/user-guide/local-atlas-setup.md` updated with switching table + URI detection explanation

---

## What Changed

| File | Change |
|------|--------|
| `start-services.sh` | `--local` / `-l` flag + `RAG_LOCAL_ATLAS=1` env var; compose overlay + profile applied automatically; URI validation skipped for local mode; port 27017 checked; success output shows CLI URI and switch-back hint |
| `scripts/local-atlas.sh` | **NEW** — standalone container manager: `start\|stop\|reset\|status`; waits for healthy; prints connection string |
| `docs/user-guide/local-atlas-setup.md` | Switching section: command table, `RAG_LOCAL_ATLAS=1` form, host-native dev URI, auto-detect explanation |
| `CLAUDE.md` | Docker commands section updated; backend switching table; `local-atlas.sh` + `docker-compose.local-atlas.yml` added to Key Files |

---

## Switching Reference (canonical)

| Goal | Command |
|------|---------|
| Full stack — local Atlas | `./start-services.sh --local` |
| Full stack — Atlas cloud | `./start-services.sh` |
| Local Atlas only (container) | `./scripts/local-atlas.sh start` |
| Stop local Atlas | `./scripts/local-atlas.sh stop` |
| Wipe local data | `./scripts/local-atlas.sh reset` |
| Status + connection string | `./scripts/local-atlas.sh status` |

**CLI URI for local backend:**
```bash
export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"
```

**Nothing else changes** when switching: configs, CLI commands, dashboard URL, experiment IDs — all identical across both backends.

---

## Key Design Decisions

| Decision | Why |
|----------|-----|
| `--local` flag on `start-services.sh` (not a new script) | Single entry point for all stack variants — mirrors existing `RAG_DEV_STACK=1` / `--force-build` pattern |
| `RAG_LOCAL_ATLAS=1` env-var equivalent | CI pipelines and `Makefile` targets can set env vars without flag parsing |
| Skip cloud URI validation when `LOCAL_ATLAS=1` | Server URI comes from `docker-compose.local-atlas.yml` overlay, not `.env`; rejecting placeholder URI would be a false block |
| Print CLI URI in success output | Eliminates "what's the connection string again?" friction — it's right there at the end of `start-services.sh --local` |
| Port 27017 in conflict check only when `--local` | Avoids false conflict warnings on cloud-only starts where 27017 may be in use for other reasons |
| `local-atlas.sh` as standalone utility | When iterating fast (native server + native frontend), a dedicated container manager is cleaner than a full compose invocation |
| `reset` command wipes the named volume | Gives a clean escape hatch when index state gets corrupted; named volume (`mongodb_local_data`) is explicit so it can't silently remove unrelated volumes |

---

## Verification

```bash
# 1. Full local stack
./start-services.sh --local
# → expect "Local Atlas enabled" on startup line
# → expect CLI URI printed at the end

# 2. Run sweep against local Atlas
export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"
rag-params-finder run --config configs/example-mongodb-local.yaml

# 3. Switch back to cloud (no --local)
./start-services.sh
# → expect no mongodb-local container, normal Atlas cloud hints

# 4. Standalone container manager
./scripts/local-atlas.sh start
./scripts/local-atlas.sh status   # shows connection string
./scripts/local-atlas.sh reset

# 5. Quality gates
./scripts/quality-gates.sh
```

---

## Migration Guide (cloud → local for active development)

1. Stop the current cloud stack: `docker compose down`
2. Start local stack: `./start-services.sh --local`
3. Set CLI URI: `export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"`
4. Run sweeps as normal — all configs, CLI commands, and dashboard are identical.

**Reverting:**
1. Stop local stack: `docker compose -f docker-compose.yml --profile local-atlas down`
2. Start cloud stack: `./start-services.sh` (reads `MONGODB_URI` from `.env`)
3. Unset or restore the CLI URI.

Local data is preserved in the `mongodb_local_data` Docker volume until you run `./scripts/local-atlas.sh reset`.
