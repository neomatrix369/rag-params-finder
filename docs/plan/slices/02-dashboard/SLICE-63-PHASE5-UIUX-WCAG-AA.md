# SLICE 63 — Phase 5: UI/UX pass to WCAG AA

**MoSCoW:** COULD
**Target time:** ~10–14 h (to be sized)
**Status:** 📋 PLANNED — **backlog stub** (from the Phase 0 master prompt's "later phases"; needs a short interview/sizing before execution)
**Depends on:** **56** · **58** (soft: 59)
**Branch:** `slice/63-wcag-aa`
**Feature:** Bring the dashboard, About box and Walkthru to WCAG AA.

---

## Context

Exploration found: no global light/dark theme (only per-component `tone`), the only modal before SLICE-56 had no Esc handling or focus trap, and tests select by role/text (no `data-testid`). The SLICE-56 `Dialog` primitive is the starting point. Scope: contrast, keyboard operation, focus order and visible focus, reduced motion, landmarks/labels, error announcements, 1280 px and 390 px layouts, and a decision on a global theme/dark mode.

- **Depends-on outputs:** `frontend/src/components/chrome/Dialog.tsx`, Walkthru overlay, `index.css` tokens.

- **Invariants pointer:** `docs/plan/invariants.md`; `docs/plan/DECISION-OWNERSHIP.md` (ceiling raises and gate-topology changes are Human-owned).

## Non-goals

- New product features.
- Mobile app or native clients.
- Rebranding.

## Output contract

- An accessibility checklist run (automated + keyboard-only) is recorded with zero AA failures on the main screens, About box and Walkthru.
- A decision record on global theming/dark mode.
- `/browser-ui-qa` evidence at 1280 px and 390 px.

## Spec (GWT) — outline, to be completed at sizing

- Given the keyboard only when using the dashboard then every control is reachable and visibly focused.
- Given a screen reader when the About box opens then focus moves into the dialog and returns on close.
- Given contrast checks when run then text/background pairs meet AA.

## Before-Checks [GATE]

- [ ] Run the existing `/browser-ui-qa` and a contrast audit to baseline failures.
- [ ] **Human decision:** adopt a global theme system (touches every screen).
- [ ] Frontend coverage floors still apply.

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

📋 PLANNED — stub. Gate evidence (`docs/plan/gate-evidence/slice-63.json`) is written by the executor, never pre-created.
