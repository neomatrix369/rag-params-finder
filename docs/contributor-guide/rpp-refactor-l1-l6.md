# RPP refactor L1-L6: before and after

Record of the `/nw-refactor` pass that applied the Refactoring Priority Premise levels L1 to L6 across the backend. Design context lives in [`architecture.md`](architecture.md) and [`module-theme-map.md`](module-theme-map.md).

## Before / After

```text
OUTCOME DERIVATION  (before: 4 owners, drifting vocabularies)
  orchestrator sweep ──┐
  orchestrator bayes ──┼──► each re-counts phases, each invents its own labels
  startup reconcile  ──┤
  GET /experiments   ──┘        (last writer wins on every poll)

OUTCOME DERIVATION  (after: 1 shared tally, 3 named rule sets)
  tally_runs(runs) ──► RunTally          [outcome.py]
        │                 CompletionReason (13 persisted strings)
        ├─► orchestrator: _sweep_* / _bayesian_* rules
        ├─► startup_reconciliation: _classify_waiting, _completion_reason
        └─► experiments_lifecycle: _stale_outcome (pure) + _persist (command)

STORAGE PORT  (before: one 28-method interface)
  StorageBackend ─ experiments + runs + results + cascade + stats + explore

STORAGE PORT  (after: composed narrow protocols, same 28 methods)
  ExperimentStore ─┐
  RunStore        ─┼─► StorageBackend (composition, adapters unchanged)
  ResultStore     ─┤
  StatsReporter   ─┘

APP STARTUP  (before)                    APP STARTUP  (after)
  lifespan()  CC 19                        BOOT_STEPS = [BootStep(name, fn, policy), ...]
   try/except x6 (4 policies)              _run_boot_steps(): one loop, policy per step
   resolve_adapter(x) is ...               is_same_adapter(...)            lifespan CC 1

DOUBLEWORD  (before)                     DOUBLEWORD  (after)
  experiments.py: policy + URL + imports   experiments.py: 3-line handler
  Qwen3 prompt duplicated x2               prepare_embeddings() in pre_embed.py
                                           QWEN3_QUERY_INSTRUCTION (one owner)

RESULTS  (before)                        RESULTS  (after)
  10-tuple, positional destructure         RunConfigKey(NamedTuple), named fields
  analyze_results CC 28                    analyze_results CC 6
```

## Measured result

| Unit | Before | After |
|---|---|---|
| `orchestrator._run_sweep_inner` | E (40) | A (5) |
| `experiments_lifecycle._normalize_stale_running_status` | E (32) | CC 9 |
| `results_analyzer.analyze_results` | D (28) | B (6) |
| `cli/display._print_summary` | D (27) | A (1) |
| `startup_reconciliation._reconcile_one` | D (23) | B (2) |
| `main.lifespan` | C (19) | A (1) |

No E or D units remain in `server/` or `cli/`. Tests: 1338 passed, 0 failed.

Nothing is committed. All changes sit uncommitted on `main`, which your rules prohibit, so I'd move them to a branch like `refactor/rpp-l1-l6` before committing.

## Related

- [`architecture.md`](architecture.md) — Storage Ports section and pipeline overview
- [`module-theme-map.md`](module-theme-map.md) — folder and theme taxonomy for the touched modules
- Code: [`server/core/pipeline/outcome.py`](../../server/core/pipeline/outcome.py), [`server/core/pipeline/orchestrator.py`](../../server/core/pipeline/orchestrator.py), [`server/db/ports/storage.py`](../../server/db/ports/storage.py), [`server/main.py`](../../server/main.py), [`server/core/results_analyzer.py`](../../server/core/results_analyzer.py), [`server/core/pipeline/pre_embed.py`](../../server/core/pipeline/pre_embed.py)
