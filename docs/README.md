# Documentation index

All guides for **rag-params-finder**, organized by **who you are** and **what you want to do**.

**Repo entry:** [README.md](../README.md) · **Fastest run:** [QUICKSTART.md](../QUICKSTART.md)

**Maintainers:** slice status and decision log live in [plan/slices/PROGRESS.md](./plan/slices/PROGRESS.md) (updated 2026-07-01 for slices 21/24/25/25B; 97 tests).

> **Who is this for?** Same personas as [README → Who is this for?](../README.md#who-is-this-for) — this page is the **doc map**; the README is the project entry.

---

## Who is this for?

| Persona | Start here | Then |
|---------|------------|------|
| **New user — MongoDB + providers** | [user-guide/mongodb-setup.md](./user-guide/mongodb-setup.md) | [QUICKSTART.md](../QUICKSTART.md) → [user-guide/getting-started.md](./user-guide/getting-started.md) |
| **New user — first sweep** | [QUICKSTART.md](../QUICKSTART.md) | [user-guide/getting-started.md](./user-guide/getting-started.md) → dashboard at `http://localhost:5374` |
| **Operator — config & CLI** | [user-guide/configuration.md](./user-guide/configuration.md) | [user-guide/cli-reference.md](./user-guide/cli-reference.md) |
| **Operator — dashboard** | [user-guide/dashboard-guide.md](./user-guide/dashboard-guide.md) | [user-guide/configuration.md](./user-guide/configuration.md) (tiebreaker, env vars) |
| **Operator — SIE (BGE-M3 / Stella / SPLADE)** | [user-guide/sie-setup.md](./user-guide/sie-setup.md) | [user-guide/troubleshooting.md](./user-guide/troubleshooting.md#sie-superlinked-inference-engine) |
| **Operator — fixing errors** | [user-guide/troubleshooting.md](./user-guide/troubleshooting.md) | [user-guide/mongodb-setup.md](./user-guide/mongodb-setup.md) (indexes, Voyage tiers) |
| **Contributor — system design** | [contributor-guide/architecture.md](./contributor-guide/architecture.md) | [adr/](./adr/) |
| **Contributor — extending** | [contributor-guide/extending.md](./contributor-guide/extending.md) | [contributor-guide/development.md](./contributor-guide/development.md) |
| **Contributor — dev environment** | [contributor-guide/development.md](./contributor-guide/development.md) | [plan/slices/PROGRESS.md](./plan/slices/PROGRESS.md) · [plan/slices/](./plan/slices/) specs |
| **Agent / slice worker** | [AGENTS.md](../AGENTS.md) · [CLAUDE.md](../CLAUDE.md) |  [plan/slices/PROGRESS.md](./plan/slices/PROGRESS.md) → current `SLICE-XX-*.md` |

---

## User guide

| Doc | What it covers |
|-----|----------------|
| [user-guide/mongodb-setup.md](./user-guide/mongodb-setup.md) | MongoDB Atlas cloud or local Docker, Voyage AI, search indexes |
| [user-guide/getting-started.md](./user-guide/getting-started.md) | Install, configure, first experiment (step-by-step) |
| [user-guide/sie-setup.md](./user-guide/sie-setup.md) | SIE setup — remote gateway (preferred) or optional self-hosted Docker; warm-up, Aim UI, known issues |
| [user-guide/configuration.md](./user-guide/configuration.md) | Full YAML config reference, env vars, sweep dimensions |
| [user-guide/cli-reference.md](./user-guide/cli-reference.md) | All CLI commands (`run`, `pause`, `resume`, `delete`, `indexes`, …) |
| [user-guide/dashboard-guide.md](./user-guide/dashboard-guide.md) | Experiments list, detail, Search Explorer |
| [user-guide/troubleshooting.md](./user-guide/troubleshooting.md) | Common errors, Docker, index preflight, storage quota, SIE |

---

## Contributor guide

| Doc | What it covers |
|-----|----------------|
| [contributor-guide/architecture.md](./contributor-guide/architecture.md) | Two-process design, modules, data flow, collections |
| [contributor-guide/development.md](./contributor-guide/development.md) | Dev loop, quality gates, Docker, slice playbook |
| [contributor-guide/extending.md](./contributor-guide/extending.md) | New models, chunkers, retrieval methods, API endpoints |
| [contributor-guide/release-process.md](./contributor-guide/release-process.md) | Versioning, `scripts/release.sh`, CHANGELOG |
| [contributor-guide/local-environment.md](./contributor-guide/local-environment.md) | Private/machine-specific Atlas and Voyage notes |

---

## Architecture decisions & slices

| Doc | What it covers |
|-----|----------------|
| [adr/ADR-001-two-process-architecture.md](./adr/ADR-001-two-process-architecture.md) | CLI + server separation |
| [adr/ADR-002-voyage-and-local-providers.md](./adr/ADR-002-voyage-and-local-providers.md) | Dual embedding/rerank providers |
| [adr/ADR-003-mongodb-atlas-vector-store.md](./adr/ADR-003-mongodb-atlas-vector-store.md) | MongoDB Atlas as vector store |
| [plan/slices/PROGRESS.md](./plan/slices/PROGRESS.md) | Slice status, decision log, forward roadmap |
| [plan/slices/SLICE-*.md](./plan/slices/) | Per-slice specs (acceptance criteria, verification) |

---

## Maintainer / internal

| Doc | What it covers |
|-----|----------------|
| [_internal/DOC-GAPS.md](./_internal/DOC-GAPS.md) | Documentation gap tracker |
| [_internal/DOCS-CODE-AUDIT.md](./_internal/DOCS-CODE-AUDIT.md) | Docs vs code audit |
| [_internal/DOCS-CODE-AUDIT-FIXES.md](./_internal/DOCS-CODE-AUDIT-FIXES.md) | Audit remediation log |
| [_internal/TIEBREAKER-EXPLANATION-FEATURE.md](./_internal/TIEBREAKER-EXPLANATION-FEATURE.md) | Tiebreaker UI feature notes |
| [_internal/GRAPHITI-EXPORT-SLICE-1.md](./_internal/GRAPHITI-EXPORT-SLICE-1.md) | Graphiti export notes |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Redirect stub → contributor-guide/architecture.md |

---

## Common tasks → doc

| Task | Doc / command |
|------|----------------|
| Install and run first sweep | [QUICKSTART.md](../QUICKSTART.md) |
| Atlas vector + text search indexes | [user-guide/mongodb-setup.md](./user-guide/mongodb-setup.md) |
| Example YAML configs | `configs/example-mongodb-local.yaml`, `configs/example-mongodb-voyage.yaml`, `configs/example-mongodb-sie.yaml` |
| Quality gates before commit | [contributor-guide/development.md](./contributor-guide/development.md) · `./scripts/quality-gates.sh` |
| Docker server + dashboard | [plan/slices/SLICE-14-DOCKER-COMPOSE.md](./plan/slices/SLICE-14-DOCKER-COMPOSE.md) |
| SIE (BGE-M3) Docker setup | [user-guide/sie-setup.md](./user-guide/sie-setup.md) |
| Continue an in-flight slice |  [plan/slices/PROGRESS.md](./plan/slices/PROGRESS.md) + matching `plan/slices/SLICE-XX-*.md` |
