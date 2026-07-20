# SLICE 05 — Multiple Queries from Persona JSON

**MoSCoW:** MUST
**Target time:** ~20 min
**Actual time:** ~10 min
**Status:** ✅ COMPLETE (2026-05-02)

---

## Goal

Load test queries from a persona-based JSON file and execute all queries within each run. Enables evaluation across multiple question types and user roles (student, advisor, etc.).

---

## Acceptance Criteria

- [x] `load_queries()` reads a persona JSON file (local path or URL)
- [x] URL queries are downloaded to `configs/` and cached (re-download on delete)
- [x] All queries in the file execute within each run
- [x] `persona_id` and `focus` stored on each `QueryResult`
- [x] Multiple queries reflected in results collection

---

## Persona JSON Format

```json
[
  {
    "persona_id": "student",
    "queries": [
      { "text": "What are Pell Grant eligibility requirements?", "focus": "financial_aid" }
    ]
  }
]
```

---

## Files Changed

| File | Change |
|---|---|
| `server/core/query_loader.py` | **NEW** `Query` frozen dataclass + `load_queries()` function |
| `server/core/orchestrator.py` | **EDIT** Replaced hardcoded query with `load_queries()` loop; stores `persona_id` and `focus` |

---

## Key Decisions

| Decision | Why |
|---|---|
| `Query` as frozen dataclass (not Pydantic) | Lightweight read-only data; no serialisation needed |
| Loop inside `run_single()` | Each query embeds + searches + reranks independently; results are per-query |
| URL caching to `configs/` | Avoid repeated downloads across runs in the same session |

---

## Exit Criteria

- Config with 3 personas × 2 queries each → 6 `QueryResult` docs per run in results collection
- `persona_id` and `focus` fields present on each result
- URL queries file downloads on first use and uses cache on subsequent runs

## Quality gates (current project standard)

```bash
bash scripts/install-git-hooks.sh
./scripts/quality-gates.sh
```

See [`development.md`](../contributor-guide/development.md) § Git hooks.
