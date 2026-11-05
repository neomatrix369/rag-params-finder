# SLICE 58 — Phase 0 leftovers (post-talk): demo hardening and deferred Walkthru features

**MoSCoW:** COULD
**Target time:** ~6–8 h (to be sized)
**Status:** 📋 PLANNED — **backlog stub** (from the Phase 0 master prompt's "later phases"; needs a short interview/sizing before execution)
**Depends on:** **56** merged
**Branch:** `slice/58-phase0-leftovers`
**Feature:** Finish what the meetup demo kit deliberately deferred.

---

## Context

SLICE-56 shipped the About box, Walkthru, replay and cross-store leaderboard for a 5-minute talk. Several items were deferred to keep that scope: a schema test for the bundled data, choice steps on other lists, the in-app Mermaid diagram, golden-master resources and derived expected sources.

- **Depends-on outputs:** `docs/about/walkthru-results.json` (with `schema_version`), `frontend/src/walkthru/*`, the `Dialog` primitive, the cross-store leaderboard.

- **Invariants pointer:** `docs/plan/invariants.md`; `docs/plan/DECISION-OWNERSHIP.md` (ceiling raises and gate-topology changes are Human-owned).

## Non-goals

- New retrieval-quality metrics (→ SLICE-60).
- A global theme or dark mode (→ SLICE-63).
- New chunking/retrieval methods (→ SLICE-57).

## Output contract

- A frontend test fails when `walkthru-results.json` does not match its `schema_version` shape.
- Choice steps work on configs, results and golden-master questions using the same `choose` front-matter mechanism.
- The in-app 'how it works' diagram renders offline (Mermaid or a static SVG, dependency audited).
- `docs/about/golden-master.md` exists if a Ragas code path is supplied (SLICE-56 Part J).

## Spec (GWT) — outline, to be completed at sizing

- Given a malformed `walkthru-results.json` when the frontend test runs then it fails naming the field.
- Given a choice step on configs when reached then the presenter can pick one and the next step uses it.
- Given the About box when opened offline then the diagram renders.

## Before-Checks [GATE]

- [ ] SLICE-56 merged and `v0.13.0` tagged.
- [ ] Decide Mermaid library vs pre-rendered SVG (dependency audit) — Human decision if a new runtime dep.
- [ ] Re-read SLICE-56 deferrals list.

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

📋 PLANNED — stub. Gate evidence (`docs/plan/gate-evidence/slice-58.json`) is written by the executor, never pre-created.
