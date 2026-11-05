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
| CAT-9 | Demo export (SLICE-56 part A) — **manual until the orchestrator's browser smoke records evidence** | `UV_FROZEN=1 uv run --no-sync python scripts/walkthru/export_walkthru_results.py --db <run_state.db> --questions configs/questions.example.json --out <path>` | Exit 0 and prints the story question; exit 1 = no exportable Redis run; exit 2 = over the size cap (nothing written) |
| CAT-10 | Offline demo (SLICE-56) — **manual until the orchestrator's browser smoke records evidence** | Serve the frontend production build (`cd frontend && npm run build`, then a static server), stop the server and Docker, block the network, open the app | About box opens and shows the bundled content; the browser records no network requests |

## How to use

- **Before a slice** (Before-Checks): run the categories your slice touches; record baseline in the gate-evidence `runtime_smoke` block.
- **At close** (After-Checks): re-run the same categories; the observed output is the evidence.
- Keep this table in sync with `CLAUDE.md` § CLI / Development Commands when commands change (single source: `CLAUDE.md`).
