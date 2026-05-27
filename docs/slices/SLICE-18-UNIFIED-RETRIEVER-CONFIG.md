# SLICE-18: Unified Retriever Configuration

**Status**: 🔨 IN PROGRESS
**Created**: 2026-05-23
**Target**: ~4–6 hours

---

## Goal

Restructure retrieval configuration to treat all retriever types (traditional search, rerankers, cross-encoders) as a unified "retrievers" group, enabling multiple retriever strategies in one sweep.

---

## Problem Statement

### Current Limitations

```yaml
retrieval:
  methods:
    - dense    # traditional search
    - sparse
    - hybrid
  top_k_initial: 20
  top_k_final: 5
  rerank_provider: local        # SEPARATE — not part of methods
  rerank_model: cross-encoder/ms-marco-MiniLM-L-6-v2
```

**Issues**:
1. Reranking is conceptually separate from retrieval methods
2. Cannot sweep over multiple reranker models
3. Cannot combine retriever types in complex ways
4. Frontend has inconsistent display (separate columns for rerankers)
5. Architecture treats rerankers as post-processing, not as retrievers

### Desired Outcome

```yaml
retrieval:
  top_k_initial: 20
  top_k_final: 5
  retrievers:
    - type: dense
    - type: reranker
      provider: local
      model: cross-encoder/ms-marco-MiniLM-L-6-v2
    - type: reranker
      provider: voyage
      model: rerank-2.5-lite
```

**Benefits**:
- Unified conceptual model (all retrieval strategies are "retrievers")
- Sweep over multiple reranker configurations
- Chain multiple rerankers (local → Voyage)
- Consistent frontend display
- Extensible for future retriever types

---

## Acceptance Criteria

### Backend
- [ ] `RetrieverType` enum added to `server/models/enums.py`
- [ ] `RetrieverConfig` Pydantic model with validation
- [ ] `RetrievalConfig` updated with `retrievers` field
- [ ] Old config format auto-migrates via Pydantic validator
- [ ] `RunParams` includes `retrievers` list
- [ ] `expand_sweep()` uses new retriever structure
- [ ] Orchestrator loops over `params.retrievers`
- [ ] Backward compat: old experiments still run
- [ ] New experiments write `retrievers` to MongoDB

### Frontend
- [ ] `RetrieverConfig` TypeScript interface added
- [ ] `RunStatus` includes `retrievers` field
- [ ] Experiments list shows unified "Retrievers" column
- [ ] Experiment detail runs table shows retrievers
- [ ] Search Explorer displays retrievers correctly
- [ ] Backward compat helper: `displayRetrievers(run)` function
- [ ] Old experiments render without errors

### Configuration
- [ ] All example YAMLs updated to new format
- [ ] Old format preserved as comments for reference
- [ ] `docs/user-guide/configuration.md` updated
- [ ] Migration guide added to docs

### Documentation
- [ ] `CLAUDE.md` updated with new config examples
- [ ] Architecture docs reflect unified retriever concept
- [ ] Troubleshooting guide mentions old vs new format

### Quality Gates
- [ ] `bash scripts/install-git-hooks.sh` run on dev machine (commit + pre-push hooks)
- [ ] `./scripts/quality-gates.sh` passes (full CI mirror before PR — see [`development.md`](../contributor-guide/development.md))
- [ ] `git push` succeeds with pre-push hook (essential checks) or run `./scripts/quality-gates.sh --quick` manually

### Manual Verification
- [ ] Old YAML config → successful sweep
- [ ] New YAML config → successful sweep
- [ ] Old experiments render correctly in dashboard
- [ ] New experiments display unified retrievers column
- [ ] Reranking still produces `rerank_score`
- [ ] Multiple rerankers chain correctly

---

## Implementation Steps

### Step 1: Backend Models (1 hour)

**File**: `server/models/enums.py`
- Add `RetrieverType` enum (dense, sparse, hybrid, reranker, cross_encoder)

**File**: `server/models/config.py`
- Add `RetrieverConfig` Pydantic model
- Update `RetrievalConfig`:
  - Add `retrievers: list[RetrieverConfig]`
  - Keep old fields as `Optional` (deprecated)
  - Add `@model_validator` for auto-migration
- Update `RunParams`:
  - Add `retrievers: list[RetrieverConfig]`
  - Keep old fields for backward compat
- Update `expand_sweep()`:
  - Use `config.retrieval.retrievers`
  - Populate both new and old fields in `RunParams`

**Verification**:
```bash
# Old config auto-migrates
python -c "from server.models.config import ExperimentConfig; import yaml; \
  cfg = yaml.safe_load(open('configs/example-mongodb-local.yaml')); \
  exp = ExperimentConfig(**cfg); \
  assert exp.retrieval.retrievers, 'Migration failed'"

# New config validates
uv run mypy server/models/
```

### Step 2: Orchestrator Pipeline (1 hour)

**File**: `server/core/orchestrator.py`

- Update `_run_single()` to loop over `params.retrievers`
- Traditional retrievers (dense/sparse/hybrid) → `retriever_search()`
- Rerankers → `rerank_results()`
- Add backward compat fallback to old fields if `retrievers` empty
- Log warning if multiple traditional retrievers configured

**Verification**:
```bash
# Test with old experiment (has retrieval_method field)
# Test with new config (has retrievers field)
```

### Step 3: API & Database (30 min)

**File**: `server/api/experiments.py`

- Update experiment doc creation
- Synthesize old fields from `retrievers` for backward compat
- Write `rerank_model`, `rerank_provider` at top level (for queries)

**Verification**:
- Check MongoDB doc structure after experiment submission
- Verify old fields populated correctly

### Step 4: Frontend Types (1 hour)

**File**: `frontend/src/types/index.ts`

- Add `RetrieverConfig` interface
- Update `RunStatus`, `RankedConfig`, `DetailedResult`, `SweepSummary`
- Add `retrievers` field (keep old fields for backward compat)

**File**: `frontend/src/utils/experimentStatus.ts`

- Add `displayRetrievers(run: RunStatus): string[]` helper
- Handle both new and old formats

**Verification**:
```bash
npm run typecheck
```

### Step 5: Frontend Display (1 hour)

**File**: `frontend/src/components/ExperimentsScreen.tsx`

- Replace "Retrieval Methods" + "Rerank Provider" with unified "Retrievers" column
- Use `displayRetrievers()` helper

**File**: `frontend/src/components/ExperimentDetailScreen.tsx`

- Update runs table to show retrievers
- Remove separate reranker column

**File**: `frontend/src/components/SearchExplorerScreen.tsx`

- Update ranked configs display

**Verification**:
```bash
npm run build
# Manual: load dashboard, check experiments list and detail
```

### Step 6: Config Examples (30 min)

Update all YAML files:
- `configs/example-mongodb-local.yaml`
- `configs/example-mongodb-voyage.yaml`
- `configs/example-kimchi.yaml`

Keep old format as comments for reference.

### Step 7: Documentation (1 hour)

- `docs/user-guide/configuration.md` — new `retrievers` schema
- `docs/user-guide/getting-started.md` — update config examples
- `docs/contributor-guide/architecture.md` — unified retriever concept
- `CLAUDE.md` — update config examples, key files list
- `README.md` — quick start config snippet

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Auto-migrate old configs via Pydantic | No manual migration script; self-healing |
| Keep old DB fields indefinitely | Backward compat for existing experiments |
| Retrievers as list, not sweep dimension | Common case: combine dense + reranker in one run |
| `RERANKER` vs `CROSS_ENCODER` types | Future-proof for different reranker architectures |
| Traditional retrievers overwrite candidates | Hybrid already handles dense+sparse fusion |
| Rerankers chain in sequence | Multi-stage reranking (local → Voyage) |

---

## Backward Compatibility Strategy

### Config Files
- Old format auto-migrates via `@model_validator`
- No breaking changes for existing YAML configs

### MongoDB Documents
- New experiments write `retrievers` in `config` field
- Old fields (`rerank_model`, `rerank_provider`) still written at top level
- Old experiments read correctly (Pydantic auto-migrates on parse)

### Frontend
- `displayRetrievers()` helper checks `run.retrievers` first
- Falls back to `run.retrieval_method` + `run.rerank_model` if `retrievers` missing
- Both old and new experiments render without errors

---

## Testing Plan

### Unit Tests
- Test `RetrieverConfig` validation (provider/model required for rerankers)
- Test `RetrievalConfig` auto-migration (old → new)
- Test `expand_sweep()` with new retrievers structure

### Integration Tests
- Old YAML config → parse → sweep → MongoDB write
- New YAML config → parse → sweep → MongoDB write
- Old experiment document → load → re-run

### Manual Tests
1. Submit old config → verify sweep runs
2. Submit new config → verify sweep runs
3. Load dashboard → check old experiments render
4. Load dashboard → check new experiments display retrievers
5. Detail screen → verify runs table shows retrievers
6. Search Explorer → verify ranked configs show retrievers

---

## Migration Guide (for users)

### Old Format

```yaml
retrieval:
  methods:
    - dense
    - sparse
  top_k_initial: 20
  top_k_final: 5
  rerank_provider: local
  rerank_model: cross-encoder/ms-marco-MiniLM-L-6-v2
```

### New Format

```yaml
retrieval:
  top_k_initial: 20
  top_k_final: 5
  retrievers:
    - type: dense
    - type: sparse
    - type: reranker
      provider: local
      model: cross-encoder/ms-marco-MiniLM-L-6-v2
```

**Note**: Old format still works (auto-migrated on parse). Update configs to new format for clarity and to enable multiple rerankers.

---

## Future Enhancements (out of scope)

1. **Sweepable retrievers** — treat `retrievers` as another Cartesian dimension
2. **Ensemble retrieval** — combine multiple traditional retrievers (weighted fusion)
3. **Learned sparse retrievers** — SPLADE, DeepImpact, etc.
4. **Late interaction models** — ColBERT, Poly-Encoder
5. **Retriever-specific config** — per-retriever `top_k`, filters, etc.

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Breaking existing experiments | Low | High | Keep old fields in DB; fallback logic in frontend |
| User confusion (new format) | Medium | Low | Clear migration guide; old format still works |
| Sweep logic bugs | Low | Medium | Comprehensive testing; backward compat mode |
| Performance regression | Very Low | Medium | Reuse existing code; no new API calls |

---

## Success Metrics

- Zero regressions in existing experiments (old configs still run)
- New config format validates without errors
- Dashboard displays both old and new experiments correctly
- All quality gates pass (`./scripts/quality-gates.sh`)
- Documentation updated and clear

---

## Completion Checklist

- [ ] All acceptance criteria met
- [ ] `./scripts/quality-gates.sh` passes
- [ ] Manual verification complete
- [ ] Documentation updated
- [ ] Example configs updated
- [ ] PROGRESS.md decision log updated
- [ ] Git commit with descriptive message
