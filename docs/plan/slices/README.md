# Slice specs — theme index

**Status SSOT:** [`PROGRESS.md`](PROGRESS.md) (flat — not nested under a theme).

**Gate evidence:** [`../gate-evidence/`](../gate-evidence/) (flat by slice id).

**Theme numbers** = delivery-wave chronology. **Slice numbers** in filenames = identity (unchanged). Decision: [#162](../DECISIONS.md).

| # | Folder | Wave | Specs |
|---|--------|------|-------|
| 01 | [`01-core-pipeline/`](01-core-pipeline/) | First skateboard → sweep / recovery | 01–07, 10, 16, 18, 29 |
| 02 | [`02-dashboard/`](02-dashboard/) | List / detail / explorer UX + export | 11, 28, 30–31, 39 |
| 03 | [`03-platform/`](03-platform/) | Compose, ports, Atlas local, toolchain, Docker build | 14, 20, 24–25B, 42 |
| 04 | [`04-sie/`](04-sie/) | SIE skateboard → bicycle | 21–23 |
| 05 | [`05-storage/`](05-storage/) | Ports → Postgres cutover + Mongo residuals | 19, 26–27, 32–38, 43 |
| 06 | [`06-bayesian/`](06-bayesian/) | Optuna track | 41A–C |
| 07 | [`07-quality-craft/`](07-quality-craft/) | Docs SSOT + coverage floors + module themes | 40, 44–45 |

## Boundary

| Path | Owns |
|------|------|
| `docs/plan/` | Continuity: TRAIL, DECISIONS, HANDOFF, GAP_ANALYSIS, PRD, interview summary |
| `docs/plan/slices/` | Per-slice specs + **PROGRESS.md** execution status |
| `docs/plan/gate-evidence/` | Per-slice gate JSON (flat) |

Do **not** invent a second status tracker at `docs/plan/PROGRESS.md`.

## Finding a slice

```text
docs/plan/slices/<NN>-<theme>/SLICE-<id>-<NAME>.md
```

Example: Slice 40 → [`07-quality-craft/SLICE-40-DOCS-PLAN-SLICES-SSOT.md`](07-quality-craft/SLICE-40-DOCS-PLAN-SLICES-SSOT.md).
