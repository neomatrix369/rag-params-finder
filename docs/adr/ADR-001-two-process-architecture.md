# ADR-001: Two-Process Architecture (CLI + Server)

**Status**: Accepted  
**Date**: 2026-05-02  
**Slice**: 1 — Skateboard

---

## Context

The tool needs to submit experiment configs, execute long-running pipelines (PDF → chunk → embed → store → query), and display results. Several architectural options exist:

1. **Single process**: CLI runs the pipeline itself, writes results to a local file.
2. **Two-process**: CLI is a thin HTTP client; a separate FastAPI server owns execution and MongoDB.
3. **Browser-only**: All logic in the browser (like pre-rag-explorer-dashboard), using in-browser WASM models.

---

## Decision

Use a **two-process architecture**: a stateless Python CLI and a stateful FastAPI server.

```
CLI (thin) ──HTTP POST──▶ FastAPI Server ──▶ MongoDB Atlas
           ◀──polling ──  (execution engine)
```

---

## Rationale

| Concern | Two-process advantage |
|---|---|
| Secrets | API keys (`VOYAGE_API_KEY`, `MONGODB_URI`) stay on the server; the CLI never sees them |
| Long-running pipelines | CLI can exit or detach (`--detach`); server continues in the background |
| Multi-user | Multiple engineers can submit experiments to a shared server |
| Dashboard | React dashboard can poll the same server endpoints without duplicating execution logic |
| Separation of concerns | Config submission (CLI) is independent of pipeline execution (server) |

---

## Consequences

- **Server must be running** before CLI can submit. Engineers start two processes instead of one.
- **Single-user simplicity is reduced** — a local-only mode that bypasses the server would be simpler for solo use. Deferred enhancement.
- **Secrets must stay server-side** — CLI config files must never contain `VOYAGE_API_KEY` or `MONGODB_URI`. Validated by `.gitignore` + `.env.example`.

---

## Alternatives Considered

- **Single-process**: Simpler, but CLI must carry secrets and cannot exit while pipeline runs.
- **Browser-only**: No server cost, but MongoDB Atlas and Voyage AI cannot be called from a browser without leaking API keys. Also limited by browser memory for large embedding batches.
