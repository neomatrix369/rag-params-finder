# Slice 39 — Demo-Ready Dashboard Polish

**Status**: ✅ COMPLETE — implementation and live regression verification complete

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

The promised visual-direction prompt was not present in project artifacts when implementation started. The bounded fallback direction is **editorial scientific instrument**: a warm paper canvas within an ink/navy application frame, precise teal and cobalt accents, compact result labels, and restrained state colour. This direction preserves the existing product character while making the path from sweep to results easier to scan.

Product copy uses a meaning-specific vocabulary rather than one umbrella term:

| Meaning | Preferred term |
|---------|----------------|
| Experiment output | Results |
| Execution lifecycle | Progress or status |
| Available user action | Next step |
| Vector-database information | Storage metrics |
| Checks that demonstrate the slice passed | Verification |

| Token concern | Constraint |
|---------------|------------|
| Palette | Ink/navy frame, warm paper canvas, white surfaces, teal/cobalt action accents, and semantic lifecycle colours used only to communicate status |
| Typography | Local serif display face, local humanist sans body face, and system monospace for identifiers; no font download or runtime request |
| Spacing | 4 px base with an 8/12/16/24/32 px working rhythm; denser metadata stays subordinate to status and outcome |
| Surfaces | Fine borders, low-elevation shadows, restrained corner radii, and one subtle grid texture; no glassmorphism or decorative gradients in content cards |
| Motion | CSS-only colour, opacity, and transform transitions; no animation dependency; `prefers-reduced-motion` disables non-essential motion |
| Stack | Existing React 19 + Tailwind 3 only; no component, state, chart, icon, font, or animation dependency |

## Baseline verification — 2026-07-18

- **Source**: clean `main` at `1647164` before implementation.
- **Quality**: `./scripts/quality-gates.sh` passed; 116 backend tests passed, scoped coverage was 83.0%, and frontend lint, typecheck, build, and audit passed.
- **Bundle**: `dist/assets/index-B2cakIdP.js` 316.88 kB / 90.21 kB gzip; `dist/assets/index-DFeJVCRg.css` 43.12 kB / 7.50 kB gzip; HTML 0.72 kB / 0.40 kB gzip.
- **Network contract**: list and running-detail polls remain 2 s; vector-database stats remain 60 s; standard and storage timeouts remain 30 s and 90 s. The production calls remain `GET /experiments`, `GET /experiments/{id}`, `GET /experiments/vector-db-stats`, `GET /experiments/{id}/db-stats`, `POST` pause/resume/cancel, and `DELETE /experiments/{id}`.
- **State and navigation contract**: `App.tsx` remains the list → detail → explorer router and carries the cached experiment, storage summary, page state, and persisted collapse keys across the journey.

## Implementation verification — 2026-07-18

- **Results journey**: the list now states the decision the workspace supports, promotes lifecycle and sweep outcome above secondary metadata, and exposes an explicit `View experiment` action. Detail now leads with experiment identity, lifecycle truth, configured/completed run counts, and the next step before configuration, run results, and operational storage context.
- **Shared visual language**: the existing shell, chrome, progress card, collapsible card, and control primitives use the same ink/navy frame, warm paper canvas, local typography, teal action accent, semantic status colours, fine borders, and restrained elevation.
- **Compact layout**: list/detail help rails are hidden on compact screens, detail receives a compact `Back` action, controls wrap, page padding steps down, long identifiers and data-source names wrap, and intentional run-table overflow remains locally scrollable. Search Explorer receives only the responsive width required by the shared shell; its content, state, and actions are unchanged.
- **Accessibility implementation**: touched actions have visible global focus treatment, meaningful text labels, decorative SVGs hidden from assistive technology, and 44 px minimum target height where space permits. Progress exposes native progressbar semantics and reduced-motion disables non-essential animation and transitions. Live contrast inspection led to a darker shared muted token, stronger detail-state text colours, and an explicit light/dark polling-indicator tone without changing polling behavior.
- **Behavior preservation**: a source-diff audit found no changes to API calls, request parameters, polling setup, timeouts, mutations, cache handoff, routing, or action handlers. `App.tsx`, service modules, constants, backend, and data models are unchanged.
- **Automated quality**: `./scripts/quality-gates.sh` passed after the review revision: repository lint, Ruff, mypy, Bandit, 116 backend tests at 83.0% scoped coverage, pip audit, 7 frontend component scenarios, frontend lint/typecheck/build, and frontend audit all passed.
- **Graph review**: the code-review graph rated the presentation change low risk (`0.40`) and found no affected execution flow. Its direct-component-coverage finding is addressed by the focused Slice 39 test tier described below.
- **Branch scope**: the unrelated MongoDB commit was removed from the local-only implementation history. The resulting `main...HEAD` diff contains presentation, component-test, quality-gate, and related documentation files only; no backend, Compose, API-test, or data-model files remain.

| Production asset | Baseline | Implemented | Delta |
|------------------|----------|-------------|-------|
| JavaScript | 316.88 kB / 90.21 kB gzip | 327.57 kB / 92.48 kB gzip | +3.37% / +2.52% gzip |
| CSS | 43.12 kB / 7.50 kB gzip | 39.74 kB / 7.31 kB gzip | -7.84% / -2.53% gzip |
| HTML | 0.72 kB / 0.40 kB gzip | 0.72 kB / 0.40 kB gzip | unchanged |

No runtime dependency was added. The JavaScript change remains below the 5% regression budget.

### Live browser verification

The Docker-served frontend on port 5374 was inspected against the unchanged backend on port 8001. Because the in-app browser had no active connection, a standalone Chromium/Playwright session was used for the same live checks.

- **Responsive journey**: list and detail document widths matched their 1440 px and 390 px viewports exactly, with no unintended horizontal page scrolling, clipped primary controls, or overlapping content.
- **Runtime health**: the four live list/detail viewport checks produced no application console errors or page errors.
- **Keyboard**: list and detail actions remained reachable with visible focus; the shared focus outline rendered as a 3 px teal solid outline, and applicable action targets retained the intended 44 px height.
- **Contrast**: 107 desktop-list, 291 desktop-detail, 98 mobile-list, and 282 mobile-detail non-decorative text samples produced zero WCAG AA failures after the final token corrections. The corrected green, amber, and red detail-state text measured 4.79:1, 4.84:1, and 5.91:1 on their tinted surfaces.
- **Network behavior**: the live journey issued only the expected `GET /experiments`, `GET /experiments/vector-db-stats`, and `GET /experiments/{id}` requests. Repeated list/detail requests measured approximately 1995–2010 ms, confirming the 2 s cadence. Source comparison confirms unchanged parameters, 30/90 s timeouts, 60 s stats cadence, and mutation endpoints; destructive mutations were intentionally not executed for visual verification.
- **State coverage**: live data covered running, complete, and failed presentation during the session. Browser-local intercepted GET responses covered paused, partial, cancelled, loading, empty, error, and 16-item pagination states while all non-GET requests were blocked. Every lifecycle state completed a collapse → expand round trip and exposed the expected text status and valid action labels.
- **Five-second comprehension**: the desktop first viewports expose the RAG decision purpose, selected experiment identity/state, run outcome, and next results or lifecycle action without opening secondary panels.

### Regression matrix

| State | Preserved presentation and actions | Source/automated verification | Live visual verification |
|-------|------------------------------------|---------------------------|----------------------|
| Running | Text status, live progress, Pause, Cancel, and live-results action | ✅ | ✅ Live data |
| Paused | Text status, Resume, Delete, and completed-run results action | ✅ | ✅ Intercepted GET fixture |
| Complete | Text outcome, completed count, Explore, and Delete | ✅ | ✅ Live data + fixture |
| Partial | Explicit preliminary-results copy, counts, Explore, and Delete | ✅ | ✅ Intercepted GET fixture |
| Failed | Text failure status, failed-run details, Explore, and Delete | ✅ | ✅ Live data + fixture |
| Cancelled | Text cancellation outcome, completed count, Explore, and Delete | ✅ | ✅ Intercepted GET fixture |
| Loading / polling | Existing feedback panels, cadence labels, and polling indicators | ✅ | ✅ Delayed fixture + live cadence |
| Empty / error | Existing conditions retained with explicit text and valid first-run command | ✅ | ✅ Intercepted GET fixtures |
| Pagination / collapse | Existing state handlers and persisted collapse keys retained | ✅ | ✅ 16-item fixture + round trips |

## Research input: results-led decision storytelling

The independent ARC-AGI-3 cold-solve results site supplied during planning is a **presentation reference, not a product dependency or visual template**. Its transferable thesis is that an evaluation interface becomes compelling when it connects a clear question to comparative results, depth, and a traceable case study.

For this project, that narrative maps to the existing product without importing ARC-specific mechanics:

| Priority | Adopt for `rag-params-finder` | Treatment in Slice 39 |
|----------|-------------------------------|-----------------------|
| **Must** | Thesis-first framing | State the decision the dashboard supports: choosing a RAG configuration from observed sweep results for a corpus and query set |
| **Must** | Results hierarchy | Present existing summary → experiment → configuration/run results in a deliberate visual order |
| **Must** | Traceability | Keep experiment identity, lifecycle state, configuration facts, and run outcomes connected and accurately labelled |
| **Must** | Progressive disclosure | Lead with decision-critical results; preserve collapsible detail for operational and secondary data |
| **Should** | Guided case-study path | Make list → selected experiment → existing deeper results feel like one coherent demo journey |
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

- [x] The experiment list and experiment detail screens use a consistent palette, typography hierarchy, spacing rhythm, corner treatment, and surface treatment.
- [x] Shared shell, page chrome, cards, badges, and primary actions appear as parts of one interface rather than independently styled regions.
- [x] The bounded fallback visual direction is translated into reusable CSS/Tailwind tokens; component files do not introduce scattered one-off colour values.
- [x] A live review at 1440 × 900 shows a material improvement over the `main` baseline without hiding or removing existing information.

### Experiment list first impression (Must)

- [x] On initial load, a user can identify the page purpose, experiment status, progress/outcome, and available primary action without opening a row.
- [x] Existing loading, empty, error, polling, pagination, expansion, deletion, and vector-database-stat states remain visible and usable.
- [x] Dense experiment metadata remains readable without competing visually with status and progress.

### Experiment detail hierarchy (Must)

- [x] At 1440 × 900, the first viewport clearly presents experiment identity, current status, progress/outcome, and valid controls before secondary run details.
- [x] Running, paused, complete, partial, failed, and cancelled states remain distinguishable by text as well as colour.
- [x] Existing pause, resume, cancel, delete, navigation, pagination, and collapsible-card behavior is unchanged in source and automated checks; the live state matrix confirms action visibility and non-destructive interactions.

### Results narrative and source fidelity (Must)

- [x] The dashboard states the concrete decision it supports without claiming automatic optimization, best-config selection, or other planned capabilities as implemented.
- [x] The list-to-detail sequence progresses from experiment overview to existing configuration/run results without adding, transforming, or reinterpreting metrics.
- [x] Experiment IDs, provider/model names, retrieval methods, statuses, counts, scores, and durations remain sourced from their existing fields and retain their current units and semantics.
- [x] An unfamiliar reviewer can identify the product purpose, the selected experiment's state, and the next available action from the desktop first viewport in a five-second comprehension check.
- [x] Existing detailed-results navigation remains discoverable; Search Explorer receives only a shared-shell responsive width integration, with no content or behavior change.

### Regression budget (Must)

- [x] Live GET comparison and source comparison confirm the same API calls, request parameters, polling cadence, timeouts, and mutations.
- [x] List → detail → back source paths preserve the same selected experiment, cached handoff, pagination state, and collapsible-card persistence behavior.
- [x] No lifecycle status, action-visibility rule, score, count, duration, or storage statistic changes solely because presentation changed.
- [x] The production build contains no new runtime dependency; JavaScript and CSS output sizes are recorded above and remain inside the 5% budget.
- [x] The regression matrix above covers running, paused, complete, partial, failed, cancelled, empty, loading, polling, and error presentations.

### Responsive and accessible presentation (Must)

- [x] At 390 × 844 and 1440 × 900, the list-to-detail journey has no unintended horizontal page scrolling, clipped controls, or overlapping content.
- [x] Interactive elements implement visible keyboard focus, meaningful labels, and a minimum 44 × 44 px touch target where space permits; live keyboard traversal passes.
- [x] Normal text meets WCAG AA contrast (4.5:1); large text and essential UI boundaries meet at least 3:1.
- [x] Information conveyed by colour is also conveyed by text, iconography, or position.

### Optional polish (Could — only after all Must criteria pass)

- [x] Add restrained transitions using existing browser/CSS capabilities, with reduced-motion respected.
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

Scenario: results remain faithful to source data after visual restructuring
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
| `frontend/src/components/SearchExplorerScreen.tsx` | One responsive width utility required by the shared shell; no content, state, or action change |

Existing reusable primitives such as `ExperimentProgressCard`, `CollapsibleCard`, and control buttons may be edited only when the same small change is required by both target screens.

## Before-checks [GATE]

- [x] Inspect the desktop and mobile baseline from exact `main@1647164`.
- [x] Record baseline source-level list-to-detail network contract, polling cadence, valid controls, persisted UI state, and production bundle sizes.
- [x] Record that no supplied visual-direction prompt was present and constrain the documented fallback direction.
- [x] Reduce the documented fallback direction to explicit palette, typography, spacing, surface, and motion constraints.
- [x] Reduce the results-led research input to the adoption table above; do not use external implementation details or unresolved claims.
- [x] Confirm `npm run lint`, `npm run typecheck`, and `npm run build` pass before editing.
- [x] Confirm no new runtime dependency is required.

## Two-hour stop line

| Time | Outcome |
|------|---------|
| 0–10 min | Baselines inspected; prompt reduced to constraints |
| 10–25 min | Shared tokens, shell, and chrome aligned |
| 25–65 min | Experiment list Must criteria complete |
| 65–95 min | Experiment detail Must criteria complete |
| 95–115 min | Responsive, keyboard, contrast, and behavior verification |
| 115–120 min | Build and final visual verification |

If implementation reaches 95 minutes with any Must criterion incomplete, stop optional styling and finish only the smallest changes needed to pass the Must criteria. Do not borrow time by adding dependencies or changing behavior.

## After-checks

- [x] `cd frontend && npm run lint`
- [x] `cd frontend && npm run typecheck`
- [x] `cd frontend && npm run test`
- [x] `cd frontend && npm run build`
- [x] Manual list → detail → back journey passes at 390 × 844 and 1440 × 900.
- [x] Pause/resume/cancel/delete visibility rules match the pre-change source behavior across the live state matrix.
- [x] Live GET and source-level before/after comparison confirms unchanged endpoints, parameters, polling cadence, timeouts, and mutations.
- [x] Before/after bundle-size comparison meets the 5% regression budget.
- [x] Loading, empty, error, polling, pagination, and collapsed/expanded states are manually checked.
- [x] Lifecycle-state regression matrix passes for running, paused, complete, partial, failed, and cancelled experiments.
- [x] Keyboard focus and contrast checks pass for every touched interactive primitive.
- [x] Before/after live inspection demonstrates each visual acceptance criterion.
- [x] Five-second comprehension check identifies purpose, experiment state, and next action without prompting.
- [x] No backend, API, polling, or data-model file changed.

## Test strategy

This slice changes presentation without intentionally changing state or data logic. The focused Vitest + React Testing Library/jsdom tier renders the real list and detail components against controlled API responses. Its 7 scenarios cover running, paused, complete, partial, failed, and cancelled copy plus Pause, Cancel, Resume, Explore, Delete, and list-to-detail action visibility.

`npm run test` is part of frontend `verify`, the quick/full quality gates, and CI. TypeScript, ESLint, production build, responsive inspection, keyboard navigation, contrast checks, and explicit before/after behavior comparison remain complementary verification activities.

## Commit

```text
feat(slice-39): make the dashboard demo journey presentation-ready
```
