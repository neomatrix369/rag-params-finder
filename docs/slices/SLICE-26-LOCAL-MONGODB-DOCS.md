# Slice 26 — Local MongoDB: Smooth Path Documentation + Script Feedback

**Status**: 📋 PLANNED
**Branch**: `slice/26-local-mongodb-docs`
**Estimated time**: ~1.5 h

## Problem

End-to-end testing with `./start-services.sh --local` exposed three issues not covered
by existing docs or scripts:

1. **Docker daemon not running** — `start-services.sh` checks `command -v docker` but not
   whether the daemon is responding. Cryptic socket errors with no guidance.
2. **Stale Docker volume** — prior interrupted run leaves the MongoDB container `unhealthy`
   (`Unable to acquire security key[s]`). The wait loop times out silently; no hint to reset.
3. **NONINTERACTIVE port conflict** — `NONINTERACTIVE=1` exits on port 27017 conflict with
   no hint that the mongodb-local container itself may already be running.

## Goal

Make the scripts emit clear, actionable messages at each failure point, and make
`docs/user-guide/mongodb-setup.md` Path B self-sufficient — a user following it step by
step should never hit a surprise.

**Key discovery**: `./start-services.sh mongodb start` already calls
`wait_for_mongodb_local_healthy()` — it blocks until the container is healthy. Docs
delegate to the script rather than duplicating the wait loop.

## Acceptance Criteria

- [ ] `./start-services.sh mongodb start` with Docker daemon down prints actionable error and exits
- [ ] `./start-services.sh --local` with Docker daemon down prints actionable error and exits
- [ ] `wait_for_mongodb_local_healthy` prints progress dots during wait
- [ ] `wait_for_mongodb_local_healthy` exits early with a reset hint when container is `unhealthy`
- [ ] `NONINTERACTIVE=1` with port 27017 in conflict prints mongodb-specific hint before exiting
- [ ] Path B prerequisites have Docker pre-flight callout (already added — keep)
- [ ] Native dev wait-for-healthy note delegates to the script (no raw `until` loop)
- [ ] `## Switching backends` table has a reset callout after it
- [ ] `troubleshooting.md` has `## MongoDB Atlas Local — Docker` section before `## 👉 See Also`
  covering: unhealthy/stale-volume, Connection reset by peer (non-fatal), NONINTERACTIVE port conflict
- [ ] README persona row (line 59) and task row (line 92) cover both cloud and local paths

## Files Changed

| File | Change |
|------|--------|
| `start-services.sh` | Docker daemon check in mongodb subcommand path + full-stack path; port 27017 NONINTERACTIVE hint |
| `scripts/lib/compose.sh` | `wait_for_mongodb_local_healthy()` — progress dots + early exit on `unhealthy` |
| `docs/user-guide/mongodb-setup.md` | Replace verbose `until` callout with script-delegate note; add reset callout |
| `docs/user-guide/troubleshooting.md` | New `## MongoDB Atlas Local — Docker` section (3 symptom/fix rows) |
| `README.md` | Fix cloud-only framing on lines 59 and 92 |

## Commits

```
fix(slice-26): docker daemon check + unhealthy container feedback in scripts
docs(slice-26): smooth Path B onboarding + local MongoDB troubleshooting
```
