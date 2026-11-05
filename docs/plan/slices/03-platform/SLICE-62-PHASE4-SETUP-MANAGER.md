# SLICE 62 — Phase 4: setup manager (CLI first, then UI wizard)

**MoSCoW:** COULD
**Target time:** ~12–16 h (to be sized)
**Status:** 📋 PLANNED — **backlog stub** (from the Phase 0 master prompt's "later phases"; needs a short interview/sizing before execution)
**Depends on:** **59** (Phase 1 docs) · soft: 14 Docker Compose
**Branch:** `slice/62-setup-manager`
**Feature:** One source of truth for getting a working local setup.

---

## Context

`rag-params-finder setup` becomes the source of truth for configuring and checking a setup; the shell scripts (`start-services.sh` and friends) wrap it. A UI wizard follows the CLI. It may start and stop Docker. **Credentials stay in `.env` — checked, never written.**

- **Depends-on outputs:** `start-services.sh`, `scripts/lib/{compose,storage_mode}.sh`, `scripts/docker/health-check.sh`, `server/core/guards/health_check.py`, `GET /api/stores`.

- **Invariants pointer:** `docs/plan/invariants.md`; `docs/plan/DECISION-OWNERSHIP.md` (ceiling raises and gate-topology changes are Human-owned).

## Non-goals

- Writing secrets or API keys anywhere.
- Cloud provisioning (Atlas clusters, Supabase projects).
- Replacing Docker Compose.

## Output contract

- `rag-params-finder setup` reports what is missing for the chosen store(s) and can start/stop the matching containers.
- The shell scripts delegate to the CLI and behave identically for existing flags.
- The UI wizard shows the same checks and actions; it never displays secret values.

## Spec (GWT) — outline, to be completed at sizing

- Given a missing `.env` key when `setup` runs then it names the key and does not create or edit `.env`.
- Given `--redis-local` when `setup` runs then Redis and the paired run-state store are started and verified via `/healthz`.
- Given the wizard when opened then no secret value is rendered.

## Before-Checks [GATE]

- [ ] **Human decision:** letting the app start/stop Docker is a trust boundary (auth/trust is Human-owned).
- [ ] bash 3.2 compatibility for any script wrappers (see memory note on `storage_mode.sh`).
- [ ] Decide the CLI/UI split and ADR.

## After-Checks [GATE]

- [ ] Every GWT scenario has ≥1 test; backend floors and frontend floors 95/90/95/95 unchanged.
- [ ] `./scripts/ci/quality-gates.sh` green.
- [ ] Docs updated: CHANGELOG, affected user/contributor docs, PROGRESS, DECISIONS.

### Closing Gates

- [ ] `nw-at-completeness-check` — AT completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline review (slice close gate #9)
- [ ] `nw-documentarist-reviewer` — docs currency where docs change
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)

## Gate Status

📋 PLANNED — stub. Gate evidence (`docs/plan/gate-evidence/slice-62.json`) is written by the executor, never pre-created.
