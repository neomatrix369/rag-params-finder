# Slice 49A — Store-String Comparison Inventory (Stream 1 baseline evidence)

**Date:** 2026-09-27
**Purpose:** Before-check evidence for [SLICE-49-VECTOR-STORE-PORT-SPLIT-REGISTRY.md](../slices/05-storage/SLICE-49-VECTOR-STORE-PORT-SPLIT-REGISTRY.md) —
the exact set of call sites the later "hardened store-string guard (AST, not grep)" test must prove
have been relocated behind the `VectorStore` port / registry, or are inside an allowed module
(adapters, `registry.py`, `settings.py`, `config.py` normalisers).

## Method

An ad hoc AST walk (not committed to the repo — a throwaway `/tmp` script) over every `.py` file
under `server/` and `cli/`, flagging:

- `==` / `!=` comparisons where either operand is a string literal in
  `{"mongodb", "mongo", "postgres", "supabase", "elasticsearch"}`
- `in {...}` / `in (...)` / `in [...]` membership tests against a literal set/tuple/list containing
  one of those literals
- `match`/`case` value patterns matching one of those literals

This supersedes a plain `grep '== *"…"'` sweep (the spec's stated gap: it would miss `!=`, set
membership, and match/case forms). CLI (`cli/`) is included per the spec — the original slice 32
sweep only covered `server/`.

## Result — 23 call sites

```
server/core/guards/config_backend_guard.py:24: if engine == "postgres":
server/core/guards/health_check.py:42: if backend == "postgres":
server/core/guards/health_check.py:95: if backend == "postgres":
server/core/guards/health_check.py:107: if backend == "mongodb":
server/core/guards/search_index_guard.py:143: if backend == "postgres":
server/core/guards/search_index_guard.py:147: if backend != "mongodb":
server/db/ports/stats_common.py:108: if raw in {"supabase", "postgres"}:
server/db/ports/stats_common.py:110: if raw in {"mongo", "mongodb"}:
server/db/ports/store_factory.py:28: if backend == "mongodb":
server/db/ports/store_factory.py:32: if backend == "postgres":
server/db/ports/store_factory.py:49: if backend == "mongodb":
server/db/ports/store_factory.py:53: if backend == "postgres":
server/main.py:32: if normalize_storage_backend(settings.storage_backend) == "mongodb":
server/models/config.py:19: if provider == "supabase":
server/models/config.py:21: if provider == "mongo":
server/models/config.py:207: if value.strip().lower() == "supabase":
server/settings.py:157: if backend == "mongodb" and not self.mongodb_uri.strip():
server/settings.py:162: if backend == "postgres":
server/settings.py:183: if normalize_storage_backend(self.storage_backend) != "postgres":
cli/indexes_cmd.py:95: if backend == "postgres":
cli/indexes_cmd.py:98: if backend != "mongodb":
cli/indexes_cmd.py:128: if backend == "postgres":
cli/indexes_cmd.py:135: if backend != "mongodb":
```

## Disposition against the spec's allow-list

The spec allows branching to remain in: adapters, `registry.py` (new), `settings.py`, and
`config.py` normalisers.

| File | Allowed today? | Why / what 49A+ must do |
|---|---|---|
| `server/settings.py:157,162,183` | **Yes** (normaliser/settings module) | Stays — settings owns backend validation |
| `server/models/config.py:19,21,207` | **Yes** (config normaliser module) | Stays — `normalize_database_provider` alias logic |
| `server/db/ports/store_factory.py:28,32,49,53` | No — becomes registry-driven | Replaced by `get_vector_store()` + `registry.resolve_adapter()` (this stream does not touch it) |
| `server/core/guards/health_check.py:42,95,107` | No | Must read `VectorStore.storage_mode()` / capabilities instead of comparing strings (49A output contract) |
| `server/core/guards/search_index_guard.py:143,147` | No | Must read the active `VectorStore`'s plan/capabilities |
| `server/core/guards/config_backend_guard.py:24` | No | Must compare against the active vector store's engine label, not a literal |
| `server/db/ports/stats_common.py:108,110` | No | Provider-specific half moves behind `VectorStore.stats()` |
| `server/main.py:32` | No | Startup wiring must resolve via the registry |
| `cli/indexes_cmd.py:95,98,128,135` | No | Spec explicitly calls out this file's "thin-client leak" (deferred fix to Slice 51's `GET /api/stores`, but the branching itself should still route through the registry/port where 49A touches it) |

**Baseline count to close: 23 sites, 15 of which are outside the allow-list** (8 are already in an
allowed module: 3 in `settings.py`, 3 in `config.py`, plus the 4 in `store_factory.py` which the
output contract explicitly keeps as the factory's own internal routing — spec says
`get_storage_backend()` keeps reading `STORAGE_BACKEND` directly, so those 4 are expected to
remain as-is even after 49A; net "must relocate" count is **11** call sites across
`health_check.py`, `search_index_guard.py`, `config_backend_guard.py`, `stats_common.py`, and
`main.py`).

This inventory is the fixed point the AST guard test (`tests/server/test_no_store_string_branching.py`,
a later stream) must reconcile against — it should assert zero *unlisted* hits outside the allow-list
table above.
