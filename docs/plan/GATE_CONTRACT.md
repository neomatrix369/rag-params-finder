# Gate Contract — gate-evidence SSOT

The single source of truth for what a gate-evidence file must contain and when a slice may transition
`🔀 ON BRANCH → ✅ PASSED`. Committed evidence lives in [`gate-evidence/`](gate-evidence/) (flat, one
`slice-<id>.json` per slice). Do not invent `gate_status: PASSED` without the fields below.

## Close rule (Before / After)

1. **Before-Checks** — run all baseline gates on a clean branch *before* starting; record the baseline (`all green` or `waived: <reason>`).
2. **After-Checks** — re-run the same gates after the work; every check must be green (or explicitly waived with a reason).
3. Write `slice-<id>.json`, set `gate_status`, and only then update [`slices/PROGRESS.md`](slices/PROGRESS.md) + [`TRAIL.md`](TRAIL.md).

Baseline gate commands: see [`invariants.md`](invariants.md) § Baseline commands. Runnable smoke: [`../smoke-tests/SMOKE-REGISTRY.md`](../smoke-tests/SMOKE-REGISTRY.md).

## `gate_status` vocabulary

| Value | Meaning |
|-------|---------|
| `PASSED` | All After-Checks green on a merged/mergeable branch; requires `branch` + `pr` + `verified_at`. |
| `VERIFIED` | Legacy equivalent of PASSED (slices 1–6); kept as historical evidence. |
| `ON_BRANCH` | Code complete on a branch, gates green locally, PR not yet merged. |
| `PENDING_VERIFICATION` | Code on main but formal gate closure still owed (e.g. coverage/mutation debt). |

## Minimum schema (every file)

```json
{
  "slice": 45,
  "gate_status": "PASSED",
  "verified_at": "2026-07-28",
  "branch": "slice/45-module-theme-separation",
  "pr": "https://github.com/neomatrix369/rag-params-finder/pull/130",
  "note": "one-line summary of what closed"
}
```

- `slice`, `gate_status` are **required always**.
- `verified_at`, `branch`, `pr` are **required when `gate_status` is `PASSED` / `VERIFIED`**.
- `ON_BRANCH` / `PENDING_VERIFICATION` files add `inferred` and/or `code_on_main` / `code_commit` to explain the debt.

## Rich optional blocks (recommended for Must slices)

`slice-45.json` is the reference for the full shape. Add these as the slice warrants:

| Block | Holds |
|-------|-------|
| `quality_gates` | Command + exit code + backend/frontend test counts, coverage %, floors, decision refs |
| `runtime_smoke` | Live commands run (`version`, `/healthz`, sweep) + observed results — mirror [`../smoke-tests/SMOKE-REGISTRY.md`](../smoke-tests/SMOKE-REGISTRY.md) categories |
| `gwt_mapping` | Acceptance criteria (`AC-N.M` / `GWT-N.x`) → evidence |
| `phases` | Per-scope PASS notes (MoSCoW split) |
| `review` | Reviewer verdict (`nw-review APPROVED`, remediation DECISIONS refs) |
| `mutation_testing` / `lifecycle` / `deferred_could` | Mutation kill %, lifecycle notes, deferred Could items |

## Scope note

- `docs/plan/gate-evidence/` is the **committed SSOT**. A root-level `gate-evidence/` (if produced by
  primitive skills such as run-tests/run-lint/collect-gate-evidence) is scratch and is **not** the SSOT.
- This contract is **forward-looking**: existing legacy files (e.g. the 4-key `slice-1.json`) stay as-is;
  new/updated evidence follows the schema above.
