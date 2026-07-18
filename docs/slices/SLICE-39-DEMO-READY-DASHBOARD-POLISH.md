# Slice 39 — Demo-Ready Dashboard Polish

**Status**: 🔨 IN PROGRESS

**Branch**: `slice/39-demo-ready-dashboard-polish-implementation`

**Estimated time**: ≤2 h

**MoSCoW**: Should — a time-boxed demo interrupt; resume Slice 32 afterward

**Depends on**: none

## Problem

The dashboard is functionally mature, but its first-impression journey does not yet present that maturity as clearly as the underlying product deserves. The experiment list and experiment detail screens contain the right data and controls, yet their visual hierarchy, spacing, status emphasis, and responsive presentation can make the interface feel denser and less cohesive than the workflow it represents.

The two screens are also high-degree, currently untested frontend hotspots. A broad redesign or dependency migration would therefore create more risk than this demo time-box permits.

## Goal

Make the existing list-to-detail demo journey feel coherent, intentional, and presentation-ready while preserving every current behavior, API contract, polling interval, and experiment control.

The visual-direction prompt supplied before implementation is an input to the look and feel. It may refine colour, typography, surface, and composition choices, but it must not expand the scope or weaken the acceptance criteria below.

## Implementation direction

The promised visual-direction prompt was not present in project artifacts when implementation started. The bounded fallback direction is **editorial scientific instrument**: a warm paper canvas within an ink/navy application frame, precise teal and cobalt accents, compact evidence labels, and restrained state colour. This direction preserves the existing product character while making the evidence path easier to scan.

| Token concern | Constraint |
|---------------|------------|
| Palette | Ink/navy frame, warm paper canvas, white surfaces, teal/cobalt action accents, semantic lifecycle colours only for status evidence |
| Typography | Local serif display face, local humanist sans body face, and system monospace for identifiers; no font download or runtime request |
| Spacing | 4 px base with an 8/12/16/24/32 px working rhythm; denser metadata stays subordinate to status and outcome |
| Surfaces | Fine borders, low-elevation shadows, restrained corner radii, and one subtle grid texture; no glassmorphism or decorative gradients in content cards |
| Motion | CSS-only colour, opacity, and transform transitions; no animation dependency; `prefers-reduced-motion` disables non-essential motion |
| Stack | Existing React 19 + Tailwind 3 only; no component, state, chart, icon, font, or animation dependency |

## Baseline evidence — 2026-07-18

- **Source**: clean `main` at `1647164` before implementation.
- **Quality**: `./scripts/quality-gates.sh` passed; 116 backend tests passed, scoped coverage was 83.0%, and frontend lint, typecheck, build, and audit passed.
- **Bundle**: `dist/assets/index-B2cakIdP.js` 316.88 kB / 90.21 kB gzip; `dist/assets/index-DFeJVCRg.css` 43.12 kB / 7.50 kB gzip; HTML 0.72 kB / 0.40 kB gzip.
- **Network contract**: list and running-detail polls remain 2 s; vector-database stats remain 60 s; standard and storage timeouts remain 30 s and 90 s. The production calls remain `GET /experiments`, `GET /experiments/{id}`, `GET /experiments/vector-db-stats`, `GET /experiments/{id}/db-stats`, `POST` pause/resume/cancel, and `DELETE /experiments/{id}`.
- **State and navigation contract**: `App.tsx` remains the list → detail → explorer router and carries the cached experiment, storage summary, page state, and persisted collapse keys across the journey.
- **Visual evidence limitation**: the in-app browser had no active browser connection. Existing repository screenshots were reviewed as historical context, but current-main desktop/mobile capture and live DevTools network comparison remain open verification items.

## Research input: evidence-led results storytelling

The independent ARC-AGI-3 cold-solve results site supplied during planning is a **presentation reference, not a product dependency or visual template**. Its transferable thesis is that an evaluation interface becomes compelling when it connects a clear question to comparative evidence, depth, and a traceable case study.

For this project, that narrative maps to the existing product without importing ARC-specific mechanics:

| Priority | Adopt for `rag-params-finder` | Treatment in Slice 39 |
|----------|-------------------------------|-----------------------|
| **Must** | Thesis-first framing | State the decision the dashboard supports: finding an evidence-backed RAG configuration for a corpus and query set |
| **Must** | Evidence ladder | Present existing summary → experiment → configuration/run evidence in a deliberate visual order |
| **Must** | Traceability | Keep experiment identity, lifecycle state, configuration facts, and run outcomes connected and accurately labelled |
| **Must** | Progressive disclosure | Lead with decision-critical evidence; preserve collapsible detail for operational and secondary data |
| **Should** | Guided case-study path | Make list → selected experiment → existing deeper evidence feel like one coherent demo journey |
| **Could** | Editorial rhythm | Use section labels and restrained visual pacing where existing content already supports them |
| **Won't** | ARC mechanics and unverified lineage | Do not add game metaphors, scratch files, action budgets, Firebase assumptions, external-repo claims, or unresolved source-code claims |
| **Won't** | New analytical capabilities | Do not add ablation charts, model-sweep charts, heatmaps, replay, or new aggregation in this slice |

The ARC study's reported results, harness, hosting, authorship, and repository investigation must not appear as claims in the product UI. The source code is not public at planning time, so no implementation may depend on or claim lineage from it. This plan adopts only the information-design principles described above.

### Ownership of deferred analytical ideas

| Research pattern | Existing project owner |
|------------------|------------------------|
| Model/configuration comparison visualization | Slice 11 — Search Explorer visualization + query filtering |
| Score semantics and zero-match clarity | Slice 30 — Search Explorer UX |
| Experiment archive discovery | Slice 31 — status filter + name/ID search |
| Per-query depth or heatmap views | Future scope only after Slice 11 data and performance are verified |
| Full reasoning-style replay | Won't for Slice 39; no equivalent event contract exists today |

## Scope boundary

| In scope | Out of scope |
|----------|--------------|
| Lightweight visual tokens using the existing Tailwind/CSS foundation | New UI, state-management, chart, or animation libraries |
| Shared dashboard shell and page chrome | Dark mode or theme switching |
| Experiment list presentation and its existing states | New filters or search — Slice 31 |
| Experiment detail above-the-fold hierarchy | Search Explorer behavior — Slices 30 and 11 |
| Responsive layout, focus visibility, and contrast | Backend, API, model, storage, or polling changes |
| Existing reusable cards, badges, and controls where needed for consistency | Component architecture refactors or new product capabilities |

## Acceptance criteria

### Cohesive visual language (Must)

- [ ] The experiment list and experiment detail screens use a consistent palette, typography hierarchy, spacing rhythm, corner treatment, and surface treatment.
- [ ] Shared shell, page chrome, cards, badges, and primary actions appear as parts of one interface rather than independently styled regions.
- [ ] The supplied visual-direction prompt is translated into a small set of reusable tokens; component files do not introduce scattered one-off colour values.
- [ ] A side-by-side review at 1440 × 900 shows a material improvement over the captured `main` baseline without hiding or removing existing information.

### Experiment list first impression (Must)

- [ ] On initial load, a user can identify the page purpose, experiment status, progress/outcome, and available primary action without opening a row.
- [ ] Existing loading, empty, error, polling, pagination, expansion, deletion, and vector-database-stat states remain visible and usable.
- [ ] Dense experiment metadata remains readable without competing visually with status and progress.

### Experiment detail hierarchy (Must)

- [ ] At 1440 × 900, the first viewport clearly presents experiment identity, current status, progress/outcome, and valid controls before secondary run details.
- [ ] Running, paused, complete, partial, failed, and cancelled states remain distinguishable by text as well as colour.
- [ ] Existing pause, resume, cancel, delete, navigation, pagination, and collapsible-card behavior is unchanged.

### Evidence narrative and product truth (Must)

- [ ] The dashboard's first viewport states the concrete decision it supports without claiming automatic optimization, best-config selection, or other planned capabilities as implemented.
- [ ] The list-to-detail sequence visually progresses from experiment overview to existing configuration/run evidence without adding, transforming, or reinterpreting metrics.
- [ ] Experiment IDs, provider/model names, retrieval methods, statuses, counts, scores, and durations remain sourced from their existing fields and retain their current units and semantics.
- [ ] An unfamiliar reviewer can identify the product purpose, the selected experiment's state, and the next available action from the desktop first viewport in a five-second comprehension check.
- [ ] Existing deeper-evidence navigation remains discoverable, but no Search Explorer content or behavior changes in this slice.

### Regression budget (Must)

- [ ] The same user actions produce the same API calls, request parameters, polling cadence, timeouts, and mutations before and after the visual changes.
- [ ] List → detail → back navigation preserves the same selected experiment, cached handoff, pagination state, and collapsible-card persistence behavior.
- [ ] No lifecycle status, action-visibility rule, score, count, duration, or storage statistic changes solely because presentation changed.
- [ ] The production build contains no new runtime dependency; JavaScript and CSS output sizes are recorded before and after, and any increase above 5% is removed or explicitly justified before completion.
- [ ] A regression matrix covers running, paused, complete, partial, failed, cancelled, empty, loading, polling, and error presentations.

### Responsive and accessible presentation (Must)

- [ ] At 390 × 844 and 1440 × 900, the list-to-detail journey has no unintended horizontal page scrolling, clipped controls, or overlapping content.
- [ ] Interactive elements retain visible keyboard focus, meaningful labels, and a minimum 44 × 44 px touch target where space permits.
- [ ] Normal text meets WCAG AA contrast (4.5:1); large text and essential UI boundaries meet at least 3:1.
- [ ] Information conveyed by colour is also conveyed by text, iconography, or position.

### Optional polish (Could — only after all Must criteria pass)

- [ ] Add restrained transitions using existing browser/CSS capabilities, with reduced-motion respected.
- [ ] Apply the same visual language to one additional reusable card that appears in the list-to-detail journey.

## Behavioral scenarios

```text
Scenario: experiment list communicates the current state at a glance
  Given experiments exist in multiple lifecycle states
  When the dashboard list first renders
  Then status and progress have stronger visual priority than secondary metadata
  And every state remains identifiable without relying on colour alone

Scenario: detail view preserves the operational journey
  Given an experiment is running, paused, complete, or failed
  When the user opens its detail screen
  Then identity, status, progress or outcome, and valid controls appear in the first viewport
  And the user can perform the same actions as before the visual changes

Scenario: compact viewport remains usable
  Given the viewport is 390 by 844 pixels
  When the user navigates from the experiment list to experiment detail
  Then content does not overlap or cause horizontal page scrolling
  And primary controls remain reachable and legible

Scenario: asynchronous states share the visual language
  Given the list is loading, empty, polling, or in an error state
  When that state is displayed
  Then it uses the same typography, surfaces, and spacing as the populated experience
  And its meaning remains explicit in text

Scenario: evidence remains truthful after visual restructuring
  Given an experiment has known configuration, status, score, count, and duration fields
  When the redesigned list and detail views render that experiment
  Then every displayed value retains its original field, unit, and meaning
  And no planned capability is presented as available

Scenario: presentation does not change network behavior
  Given baseline API requests and polling behavior are recorded on main
  When the same list-to-detail journey is repeated after the visual changes
  Then the endpoints, parameters, request cadence, and mutations are unchanged
```

## Expected files

Prefer editing existing foundations. The implementation should stay within this list unless a blocking dependency is demonstrated:

| File | Intended responsibility |
|------|-------------------------|
| `frontend/src/index.css` | Small reusable visual-token layer and global canvas treatment |
| `frontend/tailwind.config.js` | Extend existing theme only if tokens require it |
| `frontend/src/components/DashboardShell.tsx` | Shared application frame |
| `frontend/src/components/AppPageChrome.tsx` | Shared brand and page hierarchy |
| `frontend/src/components/ExperimentsScreen.tsx` | List first impression and existing states |
| `frontend/src/components/ExperimentDetailScreen.tsx` | Above-the-fold detail hierarchy |

Existing reusable primitives such as `ExperimentProgressCard`, `CollapsibleCard`, and control buttons may be edited only when the same small change is required by both target screens.

## Before-checks [GATE]

- [ ] Capture desktop and mobile baseline screenshots from current `main`.
- [ ] Record baseline list-to-detail network activity, polling cadence, valid controls, persisted UI state, and production bundle sizes.
- [ ] Record the supplied visual-direction prompt in this spec or link to its stable project artifact.
- [ ] Reduce that prompt to explicit palette, typography, spacing, surface, and motion constraints.
- [ ] Reduce the evidence-led research input to the adoption table above; do not use external implementation details or unresolved claims.
- [ ] Confirm `npm run lint`, `npm run typecheck`, and `npm run build` pass before editing.
- [ ] Confirm no new runtime dependency is required.

## Two-hour stop line

| Time | Outcome |
|------|---------|
| 0–10 min | Baselines captured; prompt reduced to constraints |
| 10–25 min | Shared tokens, shell, and chrome aligned |
| 25–65 min | Experiment list Must criteria complete |
| 65–95 min | Experiment detail Must criteria complete |
| 95–115 min | Responsive, keyboard, contrast, and behavior verification |
| 115–120 min | Build evidence and final screenshots |

If implementation reaches 95 minutes with any Must criterion incomplete, stop optional styling and finish only the smallest changes needed to pass the Must criteria. Do not borrow time by adding dependencies or changing behavior.

## After-checks

- [ ] `cd frontend && npm run lint`
- [ ] `cd frontend && npm run typecheck`
- [ ] `cd frontend && npm run build`
- [ ] Manual list → detail → back journey passes at 390 × 844 and 1440 × 900.
- [ ] Pause/resume/cancel/delete visibility rules match the pre-change behavior.
- [ ] Before/after network comparison confirms unchanged endpoints, parameters, polling cadence, timeouts, and mutations.
- [ ] Before/after bundle-size comparison meets the 5% regression budget or records an approved justification.
- [ ] Loading, empty, error, polling, pagination, and collapsed/expanded states are manually checked.
- [ ] Lifecycle-state regression matrix passes for running, paused, complete, partial, failed, and cancelled experiments.
- [ ] Keyboard focus and contrast checks pass for every touched interactive primitive.
- [ ] Before/after screenshots demonstrate each visual acceptance criterion.
- [ ] Five-second comprehension check identifies purpose, experiment state, and next action without prompting.
- [ ] No backend, API, polling, or data-model file changed.

## Test strategy

This slice changes presentation without intentionally changing state or data logic. The current frontend has no component-test tier, so this time-box does not introduce one. TypeScript, ESLint, production build, responsive inspection, keyboard navigation, contrast checks, and explicit before/after behavior comparison are the required evidence.

If implementation changes conditional rendering or extracts new behavioral utilities, stop and add focused component/unit coverage before calling the slice complete; that work replaces optional polish rather than expanding the time-box.

## Commit

```text
feat(slice-39): make the dashboard demo journey presentation-ready
```
