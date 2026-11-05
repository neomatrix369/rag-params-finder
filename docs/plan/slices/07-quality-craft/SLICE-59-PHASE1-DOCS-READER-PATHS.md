# SLICE 59 — Phase 1 docs: two reader paths, glossary, four Mermaid diagrams

**MoSCoW:** SHOULD
**Target time:** ~6–8 h (to be sized)
**Status:** 📋 PLANNED — **backlog stub** (from the Phase 0 master prompt's "later phases"; needs a short interview/sizing before execution)
**Depends on:** **56** (soft: 40 docs SSOT, 45 module theme map)
**Branch:** `slice/59-docs-reader-paths`
**Feature:** Make the docs approachable without removing the full index.

---

## Context

Docs today are an index (`docs/README.md`, `docs/TRAVERSAL.md`) plus user and contributor guides. The prompt asks for two reader paths on top of `docs/README.md` — **newcomers to RAG** and **engineers choosing parameters** — with the full index kept below, a glossary with links, and four Mermaid diagrams in this order: **sweep pipeline, experiment lifecycle, system architecture, per-store data flow**.

- **Depends-on outputs:** `docs/README.md`, `docs/TRAVERSAL.md`, `docs/contributor-guide/architecture.md`, `docs/contributor-guide/module-theme-map.md`, the `docs-parity` gate from Slice 51.

- **Invariants pointer:** `docs/plan/invariants.md`; `docs/plan/DECISION-OWNERSHIP.md` (ceiling raises and gate-topology changes are Human-owned).

## Non-goals

- Rewriting existing guides.
- Animated diagrams (static structures use Mermaid; animated SVG only for temporal flows if needed).
- The in-app diagram (→ SLICE-58).

## Output contract

- `docs/README.md` opens with the two reader paths; the full index remains below.
- A glossary page defines the terms used in the paths, each with links.
- Four Mermaid diagrams render on GitHub in the stated order and match the code (checked against `architecture.md` and the store registry).
- The docs-parity gate still passes.

## Spec (GWT) — outline, to be completed at sizing

- Given a newcomer to RAG when they open docs/README.md then the first screen routes them to a path that starts with the problem, not setup.
- Given an engineer choosing parameters when they follow their path then they reach the configuration reference and the dashboard guide in ≤3 clicks.
- Given a diagram when compared to the code then its labels match module and store names.

## Before-Checks [GATE]

- [ ] Read `~/.cursor/rules/documentation-best-practices.mdc` (diagrams, ADR format, docs-as-code).
- [ ] Confirm which existing diagrams already exist (`docs/architecture-diagrams-*` branch) and reuse them.
- [ ] Confirm the docs CI gate list.

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

📋 PLANNED — stub. Gate evidence (`docs/plan/gate-evidence/slice-59.json`) is written by the executor, never pre-created.
