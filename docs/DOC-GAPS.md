# Documentation Gap Tracker

**Created**: 2026-05-05  
**Last Updated**: 2026-05-05 (README rewritten for simplicity; ARCHITECTURE.md updated for local models)  
**Reference**: Gap analysis vs [pre-rag-explorer-dashboard](https://github.com/neomatrix369/pre-rag-explorer-dashboard)

Each item below is a concrete, actionable doc gap. Check the box when done and record the date.

---

## Gap 1 — README: Screenshots / UI tour

**Priority**: High (judge and contributor first impression)

- [x] Create `docs/images/` directory
- [ ] Capture and add screenshot: Experiments list (status badges, run counts)
- [ ] Capture and add screenshot: Experiment detail (phase indicator dots, runs table)
- [ ] Capture and add screenshot: Search Explorer results view
- [x] Wire screenshot gallery into `README.md` (table format, with captions)

**Note**: `docs/images/` created and gallery wired into README. Screenshots (`01-experiments-list.png`, `02-experiment-detail.png`, `03-search-explorer.png`) still need to be placed manually.

**Reference**: pre-rag has `docs/images/01-upload.jpg … 04-collections.jpg` linked from README.

---

## Gap 2 — README: Troubleshooting section

**Priority**: High (judge self-service, reduces support burden)

- [x] Add `## Troubleshooting` section to `README.md` covering:
  - [x] Vector index not found (Atlas index not created yet)
  - [x] Dimension mismatch (384 vs 1024, mixing local + Voyage)
  - [x] Voyage rate limit hit
  - [x] Dashboard stuck on "Loading…" (server not running, CORS)
  - [x] Chunks not appearing in Atlas (write failure)

**Note**: These fixes currently live only in `CLAUDE.local.md` (private/local). They need to be in the public README.

---

## Gap 3 — README: Methods explained tables

**Priority**: Medium (quick scanning for judges evaluating the feature set)

- [x] Add `## Chunking Methods` table to `README.md` (method, description, best-for)
- [x] Add `## Retrieval Methods` table to `README.md` (method, algorithm, strengths)
- [x] Add brief `## Reranking` note (local vs Voyage, when it applies)

**Reference**: pre-rag README has concise markdown tables for both chunking and retrieval.

---

## Gap 4 — Broken ADR pointer

**Priority**: High (broken reference in a committed doc is a credibility issue)

`docs/ARCHITECTURE.md` references `docs/adr/` in the Design Decisions section — that directory does not exist.

- [x] **Option A** (preferred): Create `docs/adr/` with at minimum:
  - [x] `ADR-001-two-process-architecture.md`
  - [x] `ADR-002-voyage-and-local-providers.md` *(updated title: Voyage + local, not Voyage-only)*
  - [x] `ADR-003-mongodb-atlas-vector-store.md`
- [x] `ARCHITECTURE.md` updated with live links to each ADR

---

## Gap 5 — Slice docs: stale SLICE-01 and missing later slices

**Priority**: Medium (process clarity for future contributors / sessions)

- [x] Refresh `docs/slices/SLICE-01-SKATEBOARD.md` (status → ✅ COMPLETE, path fixed to `example-local.yaml`, acceptance criteria checked)
- [x] Add slice spec files for slices that were delivered but have no standalone doc:
  - [x] `docs/slices/SLICE-02-RERANK.md`
  - [x] `docs/slices/SLICE-03-SWEEP-EXPANSION.md`
  - [x] `docs/slices/SLICE-04-LIVE-STATUS.md`
  - [x] `docs/slices/SLICE-05-PERSONA-QUERIES.md`
  - [x] `docs/slices/SLICE-07-LOCAL-MODELS.md`

**Reference**: pre-rag has a standalone spec file per slice (`SLICE-07-SLIDING-WINDOW.md`, etc.).

---

## Gap 6 — PROGRESS.md housekeeping

**Priority**: Medium

- [x] Fix quick status table: add Slice 6 row (currently skipped; referenced in text)
- [x] Clear stale "Next Actions" tail (replaced with forward roadmap + interrupt recovery)
- [x] Add **forward roadmap** rows (Slices 6, 8–15) matching pre-rag's backlog table style
- [x] Add **interrupt recovery** checklist block (how to resume a session mid-slice)

---

## Gap 7 — Quality gates baseline record

**Priority**: Medium

- [x] Add `## Quality Gates Baseline` section to `CLAUDE.md` with real numbers:
  - [x] `ruff check .` → 0 errors (after `uv pip install -e ".[dev]"`)
  - [x] `mypy server/ cli/` → 0 errors
  - [x] `pytest` → 0 tests collected (no test suite yet)
  - [x] `npm run typecheck` → 0 errors ✓ (fixed `tsconfig.json` to include `vite/client.d.ts`)
  - [x] `npm run build` → ✓ built in ~1.8 s, 34 modules
  - [x] `npm audit --audit-level=high` → 0 vulnerabilities

**Reference**: pre-rag `CLAUDE.md` records exact numeric baselines per slice gate.

---

## Gap 8 — CI story (GitHub Actions)

**Priority**: Low–Medium

- [x] Add `.github/workflows/ci.yml` covering: `ruff`, `mypy`, `pytest` for backend; `npm run typecheck`, `npm run build`, `npm audit` for frontend
- [x] CI documented in `CLAUDE.md` Quality Gates Baseline section

**Note**: `npm run lint` excluded until ESLint config (`eslint.config.js`) is set up.

**Reference**: pre-rag's Slice 1 established CI as a first-class deliverable.

---

## Gap 9 — AGENTS.md and slice playbook in CLAUDE.md

**Priority**: Low (nice-to-have for agent session consistency)

- [x] Add `AGENTS.md` (thin file) — entry point with links to `CLAUDE.md`, `PROGRESS.md`, and quick commands
- [x] Add **slice execution playbook** block to `CLAUDE.md`:
  - [x] Pre-slice checklist (read PROGRESS, create/read spec, run quality gates)
  - [x] Verify-all commands before commit
  - [x] Decision log template
  - [x] Post-slice checklist

---

## Progress Summary

| Gap | Description | Status |
|-----|-------------|--------|
| 1 | README screenshots / UI tour | 🔨 In Progress (gallery wired; 3 PNGs need manual capture) |
| 2 | README troubleshooting section | ✅ Done |
| 3 | README methods explained tables | ✅ Done |
| 4 | Broken `docs/adr/` pointer | ✅ Done |
| 5 | Stale SLICE-01 + missing slice specs | ✅ Done |
| 6 | PROGRESS.md housekeeping | ✅ Done |
| 7 | Quality gates baseline record | ✅ Done |
| 8 | CI story (GitHub Actions) | ✅ Done |
| 9 | AGENTS.md + slice playbook | ✅ Done |
| 10 | README simplified; detail preserved in Reference Guide | ✅ Done |

**Legend**: 📋 Open | 🔨 In Progress | ✅ Done

---

## Gap 10 — Reference Guide (detail preserved from README simplification)

**Priority**: Done (created 2026-05-05)

README was simplified for quick scanning (aligned with pre-rag-explorer-dashboard style). All condensed content moved to `docs/REFERENCE.md`:

- [x] Step-by-step setup guide (all 7 original quickstart steps)
- [x] Full annotated YAML config with all fields explained
- [x] Queries file persona JSON format with examples
- [x] All-local config YAML example
- [x] Dashboard screen-by-screen reference (Experiments list, Detail, Search Explorer)
- [x] Expanded project structure (all files with descriptions)
- [x] Expanded troubleshooting (full debug steps, MongoDB cleanup queries)
- [x] Environment variables reference table
- [x] MongoDB Atlas collections table with cleanup instructions
- [x] Atlas vector index JSON for both 384-dim and 1024-dim (with all filter fields)
- [x] README → Documentation table updated to link to `docs/REFERENCE.md`
