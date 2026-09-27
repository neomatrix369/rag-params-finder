# Traversal guide — route by goal

The [documentation index](README.md) routes by **who you are** (persona). This guide routes by **what you're
trying to do right now**. Pick the mode that matches your goal.

---

## Mode 1 — Onboarding (first run, ~30 min)

| Step | Resource | Location | Time | Intent |
|------|----------|----------|------|--------|
| 1 | Project entry | [README.md](../README.md) | 5 min | What the tool is + fastest path |
| 2 | Pick a backend | [user-guide/mongodb-setup.md](user-guide/mongodb-setup.md) · [postgres-setup.md](user-guide/postgres-setup.md) | 10 min | Stand up a store (cloud or local) |
| 3 | First sweep | [QUICKSTART.md](../QUICKSTART.md) → [user-guide/getting-started.md](user-guide/getting-started.md) | 10 min | Submit a config, watch it run |
| 4 | See results | dashboard at `http://localhost:5374` | 5 min | Confirm runs + explore output |

**Exit criteria:** a sweep you submitted from the CLI is visible and progressing on the dashboard.

## Mode 2 — Incremental build / contributor (skateboard → car)

Delivery evolves as vehicle milestones across the slice **themes** (`01`–`08`). Each row → the theme's
specs + live status.

| Milestone | Theme | Specs | Status |
|-----------|-------|-------|--------|
| Skateboard — end-to-end pipeline | `01-core-pipeline` | [slices/01-core-pipeline/](plan/slices/01-core-pipeline/) | [PROGRESS.md](plan/slices/PROGRESS.md) |
| Scooter — dashboard UX | `02-dashboard` | [slices/02-dashboard/](plan/slices/02-dashboard/) | " |
| Bicycle — platform (compose, ports, Docker) | `03-platform` | [slices/03-platform/](plan/slices/03-platform/) | " |
| — SIE / storage / Bayesian tracks | `04`–`06` | [slices/](plan/slices/) | " |
| Motorbike/Car — quality-craft + new providers | `07`–`08` | [slices/07-quality-craft/](plan/slices/07-quality-craft/) · [08-embedding-providers/](plan/slices/08-embedding-providers/) | " |

Then: architecture in [contributor-guide/architecture.md](contributor-guide/architecture.md), module layout in
[contributor-guide/module-theme-map.md](contributor-guide/module-theme-map.md), and the slice-authoring
contract in [plan/slices/README.md](plan/slices/README.md).

## Mode 3 — Ad-hoc lookup (<60s triage)

| I need… | Go straight to |
|---------|----------------|
| Fix an error / failure | [user-guide/troubleshooting.md](user-guide/troubleshooting.md) |
| A config field's meaning | [user-guide/configuration.md](user-guide/configuration.md) |
| A CLI command | [user-guide/cli-reference.md](user-guide/cli-reference.md) |
| Switch backend (Mongo/Postgres, local/cloud) | [user-guide/mongodb-setup.md](user-guide/mongodb-setup.md) · [postgres-setup.md](user-guide/postgres-setup.md) |
| SIE setup (BGE-M3 / Stella / SPLADE) | [user-guide/sie-setup.md](user-guide/sie-setup.md) |
| Current slice status | [plan/slices/PROGRESS.md](plan/slices/PROGRESS.md) |
| Verify something works (runnable) | [smoke-tests/SMOKE-REGISTRY.md](smoke-tests/SMOKE-REGISTRY.md) |
| A past architecture decision | [adr/README.md](adr/README.md) |
