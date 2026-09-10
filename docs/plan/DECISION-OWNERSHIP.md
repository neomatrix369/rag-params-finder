# Decision Ownership
> Portable contract: always-on `decision-ownership` rule (Cursor + Claude).
> Filled 2026-09-10 from existing DECISIONS / CLAUDE.md / AGENTS.md — do **not** raise ceilings without Human HITL.

| Who | Owns |
|-----|------|
| **Human** | MoSCoW / Won't scope; irreversible ADRs (Accept); `STORAGE_BACKEND` default (#130 Won't flip); coverage floor **raises** (#142 thresholds); xenon ceiling raises beyond locked E/C/C baseline; gate topology add/skip/reorder; merge/release; auth/trust policy; ambiguous intent |
| **Agent** | Reversible impl within slice AC; gate *wiring* inside locked topology (`quality-gates.sh`, pre-push, CI job wiring); enforce existing floors/xenon; docs/diagram sync; Red→Green; strengthen tests only (never weaken/skip assertions); stub preamble / Closing Gates / harness embed hygiene |
| **Shared** | ADR draft → Human Accept; CF deferrals with owner slice; reviewer SKIPPED only on wrong-repo evidence + Human confirm |

## Locked ceilings (do not auto-raise)

| Ceiling | Value | Source |
|---------|-------|--------|
| Backend coverage | Combined fail_under + floor checkers — **stmts/br/fn/lines floors per #142** (BE policy via `fail_under` + `check_backend_coverage_floors.py`; see CLAUDE.md § Quality Gates Baseline) | Human / #142 |
| Frontend coverage | Vitest **95/90/95/95** stmts/br/fn/lines (`all: true`) | #142 |
| Complexity (xenon) | `--max-absolute E --max-modules C --max-average C` on `server/` `cli/` | CLAUDE.md Quality Gates |
| Identity namespaces | `rag-params-finder-flow-planner`, `rag-params-finder-retro` | TRAIL / Graphiti |

## Fail-closed

- Never invent `--no-gate` / bypass for local agent runs
- Never auto-merge; draft PRs where project requires
- Raise any row in the ceilings table ⇒ **HITL**

→ Portable rule: `decision-ownership` · Project SSOT: this file
