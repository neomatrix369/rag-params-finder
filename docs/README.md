# Documentation index

All guides for **rag-params-finder**, organized by **who you are** and **what you want to do**.

**Repo entry:** [README.md](../README.md) · **Fastest run:** [QUICKSTART.md](../QUICKSTART.md)

**Maintainers:** slice status and decision log live in [plan/slices/PROGRESS.md](./plan/slices/PROGRESS.md) (updated 2026-07-28). Specs live under numbered theme folders `01`–`07` (#162, **IMPLEMENTED**) — index: [plan/slices/README.md](./plan/slices/README.md); Slice 40: [SLICE-40](./plan/slices/07-quality-craft/SLICE-40-DOCS-PLAN-SLICES-SSOT.md).

> **Who is this for?** Same personas as [README → Who is this for?](../README.md#who-is-this-for) — this page is the **doc map**; the README is the project entry.

---

## Who is this for?

| Persona | Start here | Then |
|---------|------------|------|
| **New user — MongoDB + providers** | [user-guide/mongodb-setup.md](./user-guide/mongodb-setup.md) | [QUICKSTART.md](../QUICKSTART.md) → [user-guide/getting-started.md](./user-guide/getting-started.md) |
| **New user — Postgres (local or Supabase-hosted)** | [user-guide/postgres-setup.md](./user-guide/postgres-setup.md) | [QUICKSTART.md](../QUICKSTART.md) Path D → `configs/supabase/example-unified-retrievers.yaml` |
| **New user — first sweep** | [QUICKSTART.md](../QUICKSTART.md) | [user-guide/getting-started.md](./user-guide/getting-started.md) → dashboard at `http://localhost:5374` |
| **Operator — config & CLI** | [user-guide/configuration.md](./user-guide/configuration.md) | [user-guide/cli-reference.md](./user-guide/cli-reference.md) |
| **Operator — dashboard** | [user-guide/dashboard-guide.md](./user-guide/dashboard-guide.md) | [user-guide/configuration.md](./user-guide/configuration.md) (tiebreaker, env vars) |
| **Operator — SIE (BGE-M3 / Stella / SPLADE)** | [user-guide/sie-setup.md](./user-guide/sie-setup.md) | [user-guide/troubleshooting.md](./user-guide/troubleshooting.md#sie-superlinked-inference-engine) |
| **Operator — fixing errors** | [user-guide/troubleshooting.md](./user-guide/troubleshooting.md) | [user-guide/mongodb-setup.md](./user-guide/mongodb-setup.md) (indexes, Voyage tiers) · [postgres-setup.md](./user-guide/postgres-setup.md) |
| **Contributor — system design** | [contributor-guide/architecture.md](./contributor-guide/architecture.md) | [adr/](./adr/) |
| **Contributor — extending** | [contributor-guide/extending.md](./contributor-guide/extending.md) | [contributor-guide/development.md](./contributor-guide/development.md) |
| **Contributor — dev environment** | [contributor-guide/development.md](./contributor-guide/development.md) | [plan/slices/PROGRESS.md](./plan/slices/PROGRESS.md) · [plan/slices/](./plan/slices/) specs |
| **Agent / slice worker** | [AGENTS.md](../AGENTS.md) · [CLAUDE.md](../CLAUDE.md) |  [plan/slices/PROGRESS.md](./plan/slices/PROGRESS.md) → current `0N-<theme>/SLICE-XX-*.md` |

---

## User guide

| Doc | What it covers |
|-----|----------------|
| [user-guide/mongodb-setup.md](./user-guide/mongodb-setup.md) | MongoDB Atlas cloud or local Docker, Voyage AI, search indexes |
| [user-guide/postgres-setup.md](./user-guide/postgres-setup.md) | Postgres + pgvector — local Docker or Supabase-hosted Postgres (same backend) |
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
| [contributor-guide/module-theme-map.md](./contributor-guide/module-theme-map.md) | Behavior \| Feature \| Function theme map + Slice 45 layout status |
| [contributor-guide/development.md](./contributor-guide/development.md) | Dev loop, quality gates, Docker, slice playbook |
| [contributor-guide/extending.md](./contributor-guide/extending.md) | New models, chunkers, retrieval methods, API endpoints |
| [contributor-guide/release-process.md](./contributor-guide/release-process.md) | Versioning, `scripts/release/release.sh`, CHANGELOG |
| [contributor-guide/local-environment.md](./contributor-guide/local-environment.md) | Private/machine-specific Atlas and Voyage notes |

---

## Architecture decisions & slices

| Doc | What it covers |
|-----|----------------|
| [adr/ADR-001-two-process-architecture.md](./adr/ADR-001-two-process-architecture.md) | CLI + server separation |
| [adr/ADR-002-voyage-and-local-providers.md](./adr/ADR-002-voyage-and-local-providers.md) | Dual embedding/rerank providers |
| [adr/ADR-003-mongodb-atlas-vector-store.md](./adr/ADR-003-mongodb-atlas-vector-store.md) | MongoDB Atlas as vector store (**Superseded** by ADR-004; Mongo still supported) |
| [adr/ADR-004-postgresql-pgvector-vector-store.md](./adr/ADR-004-postgresql-pgvector-vector-store.md) | Dual-backend: Postgres/pgvector (Supabase) **and** MongoDB |
| [plan/slices/PROGRESS.md](./plan/slices/PROGRESS.md) | Slice status, decision log, forward roadmap |
| [plan/slices/README.md](./plan/slices/README.md) · `0N-<theme>/SLICE-*.md` | Per-slice specs by delivery-wave theme (#162); status SSOT remains [PROGRESS.md](./plan/slices/PROGRESS.md) |

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
| Example YAML configs | `configs/mongodb/` and `configs/supabase/` (mirrored stems; shared `configs/questions.example.json`) |
| Run on Postgres/pgvector (local or Supabase-hosted) | [user-guide/postgres-setup.md](./user-guide/postgres-setup.md) · `./start-services.sh --postgres-local` |
| Quality gates before commit | [contributor-guide/development.md](./contributor-guide/development.md) · `./scripts/ci/quality-gates.sh` |
| Docker server + dashboard | [plan/slices/03-platform/SLICE-14-DOCKER-COMPOSE.md](./plan/slices/03-platform/SLICE-14-DOCKER-COMPOSE.md) |
| SIE (BGE-M3) Docker setup | [user-guide/sie-setup.md](./user-guide/sie-setup.md) |
| Continue an in-flight slice |  [plan/slices/PROGRESS.md](./plan/slices/PROGRESS.md) + matching `plan/slices/0N-<theme>/SLICE-XX-*.md` |
