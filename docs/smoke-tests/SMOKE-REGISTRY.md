# Smoke Test Registry

A category-indexed map from a capability to a **runnable** verification command. Every command reuses
existing tooling — no new scripts. Cross-referenced from [`../plan/invariants.md`](../plan/invariants.md)
§ Baseline commands and [`../plan/GATE_CONTRACT.md`](../plan/GATE_CONTRACT.md) `runtime_smoke` block.

Prerequisite for CLI/server categories: server running (`uvicorn server.main:app --reload --port 8001`)
or the Docker stack (`./start-services.sh`).

| Cat | What it proves | Command | Expected |
|-----|----------------|---------|----------|
| CAT-1 | Server health + storage ping | `curl -s localhost:8001/healthz` · `bash scripts/docker/health-check.sh` | `200` with `storage_mode`; `503` if a store is down |
| CAT-2 | End-to-end sweep submits & runs | `rag-params-finder run --config configs/mongodb/example-local.yaml` · pgvector: `configs/supabase/example-local.yaml` | Experiment id printed; runs progress through phases |
| CAT-3 | Search indexes present | `rag-params-finder indexes list` | Atlas known/unknown OR Postgres PRESENT/MISSING |
| CAT-4 | Backend switching (four modes) | `./start-services.sh` · `--mongodb-local` · `--postgres-local` · `--postgres-cloud` | Stack boots; config `database_provider` mismatch → 422 |
| CAT-5 | All quality gates | `./scripts/ci/quality-gates.sh` | Exit 0 (repo lint + backend + frontend + audits) |
| CAT-6 | CLI installed | `rag-params-finder version` | Prints current version (e.g. `0.12.0`) |
| CAT-7 | Lifecycle controls | `rag-params-finder pause <id>` · `resume <id>` · `cancel <id>` · `delete <id>` | State transitions reflected in dashboard / `GET /experiments/{id}` |
| CAT-8 | Dashboard progress feedback (feature-level) | see [`../../VERIFICATION_CHECKLIST.md`](../../VERIFICATION_CHECKLIST.md) | 7 manual UI cases + regression suite pass |
| CAT-9 | Walkthru data export (SLICE-56 part A) | `UV_FROZEN=1 uv run --no-sync python scripts/walkthru/export_walkthru_results.py --db <run_state.db> --questions configs/questions.example.json --out <path>` | Exit 0 and prints the story question; exit 1 = no exportable Redis run, or a clean one-line error for a missing/unreadable database or questions file, malformed questions JSON, or a WAL-mode database inside a read-only folder (copy the .db with its -wal/-shm first); exit 2 = over the size cap. Nothing is written on any failure. Pass `--data-path-contains <pdf name>` to keep one dataset. Two runs on the same inputs are byte-identical (unit-tested) |
| CAT-10 | Offline walkthru (SLICE-56) — **VERIFIED 2026-11-05 by a real-browser run (headless Chromium, real mouse clicks) at 1280x800 and 390x844 against the production build; the script is not committed (no browser-test dependency in the repo)** | `cd frontend && npm run build && npx vite preview`, open the app, block requests to the backend port in the browser, then: About, Start Walkthru, Next through all 5 steps, Back, the Autoplay toggle, Open the demo | About shows 9 sections, no image, Esc returns focus. All 5 steps advance by real mouse; Autoplay is off by default, advances after the step's duration when on and stops when off. Leaderboard filter narrows rows (42 to 10), selecting a run drives the replay (7 stages, "only total time was recorded"), the improvement panel shows the query average and the caveat. **0 backend requests while the walkthru or demo screen is open** (the Experiments page fetches again when the tour ends). No sideways scroll at either size; no console errors. One external request remains: the Google Fonts stylesheet from `index.html` (predates this slice; fails silently offline, system font is used). The first run found two defects unit tests cannot see (Next button off-screen at 1280px; page 809px wide at 390px), fixed in `8ba44d0` and `1c69964` |

## How to use

- **Before a slice** (Before-Checks): run the categories your slice touches; record baseline in the gate-evidence `runtime_smoke` block.
- **At close** (After-Checks): re-run the same categories; the observed output is the evidence.
- Keep this table in sync with `CLAUDE.md` § CLI / Development Commands when commands change (single source: `CLAUDE.md`).
