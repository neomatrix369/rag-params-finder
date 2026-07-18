# Slice 39 — Demo-Ready Dashboard Polish

**Status**: 📋 PLANNED

**Branch**: `slice/39-demo-ready-dashboard-polish`

**Estimated time**: ≤2 h

**MoSCoW**: Should — a time-boxed demo interrupt; resume Slice 32 afterward

**Depends on**: none

## Problem

The dashboard is functionally mature, but its first-impression journey does not yet present that maturity as clearly as the underlying product deserves. The experiment list and experiment detail screens contain the right data and controls, yet their visual hierarchy, spacing, status emphasis, and responsive presentation can make the interface feel denser and less cohesive than the workflow it represents.

The two screens are also high-degree, currently untested frontend hotspots. A broad redesign or dependency migration would therefore create more risk than this demo time-box permits.

## Goal

Make the existing list-to-detail demo journey feel coherent, intentional, and presentation-ready while preserving every current behavior, API contract, polling interval, and experiment control.

The visual-direction prompt supplied before implementation is an input to the look and feel. It may refine colour, typography, surface, and composition choices, but it must not expand the scope or weaken the acceptance criteria below.

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
- [ ] Record the supplied visual-direction prompt in this spec or link to its stable project artifact.
- [ ] Reduce that prompt to explicit palette, typography, spacing, surface, and motion constraints.
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
- [ ] Loading, empty, error, polling, pagination, and collapsed/expanded states are manually checked.
- [ ] Keyboard focus and contrast checks pass for every touched interactive primitive.
- [ ] Before/after screenshots demonstrate each visual acceptance criterion.
- [ ] No backend, API, polling, or data-model file changed.

## Test strategy

This slice changes presentation without intentionally changing state or data logic. The current frontend has no component-test tier, so this time-box does not introduce one. TypeScript, ESLint, production build, responsive inspection, keyboard navigation, contrast checks, and explicit before/after behavior comparison are the required evidence.

If implementation changes conditional rendering or extracts new behavioral utilities, stop and add focused component/unit coverage before calling the slice complete; that work replaces optional polish rather than expanding the time-box.

## Commit

```text
feat(slice-39): make the dashboard demo journey presentation-ready
```
