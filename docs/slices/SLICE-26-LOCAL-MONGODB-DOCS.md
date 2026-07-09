# Slice 26 — Local MongoDB: Smooth Path Documentation + Script Feedback

**Status**: 📦 DEFERRED — re-scope after Postgres local/cloud path (Slice 37) and cutover (38). Mongo-only smooth-path docs are low value while **32–38** is the critical path.
**Depends on**: 25B *(Atlas Local must exist before doc polish)*
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

## Before-Checks [GATE] *(when re-activated post-cutover)*

- [ ] Slice **38** cutover complete or Mongo path explicitly still primary
- [ ] Slice **25B** ✅ complete
- [ ] `./start-services.sh --local` smoke passes on `main`

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

## After-Checks

- [ ] `./scripts/quality-gates.sh` pass
- [ ] Specification coverage: every acceptance criterion has ≥1 test or manual verification step; essential error paths covered
- [ ] Branch coverage: 100% target for any new Python functions; exclusions documented (test-writing-craft-quality.mdc §12)
- [ ] Mutation testing: survival budget met if slice adds testable logic (§23)
- [ ] Manual: follow Path B in mongodb-setup.md step-by-step from a clean state; no surprises

## Commits

```
fix(slice-26): docker daemon check + unhealthy container feedback in scripts
docs(slice-26): smooth Path B onboarding + local MongoDB troubleshooting
```
