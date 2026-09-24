# Slice 48D — DoubleWord Realtime Mode (optional)

**Status**: 📋 PLANNED
**MoSCoW**: Could (owner decision 2026-09-24, DECISIONS #202). Preamble sections are shortened: this is a Could stub; expand to full EFP form before execution.
**Depends on**: 48A ✅

## Why Could

DoubleWord is batch-first. Realtime ("dev mode") is the most expensive tier, its availability is limited, and docextract never used it. Pull this slice in only if the 48A T0 spike shows batch unusable for embeddings (V3 = NO, which promotes this slice to Must and runs it first), or if interactive small sweeps need minutes-not-hours turnaround.

## Scope sketch

- `DOUBLEWORD_MODE=realtime|batch` (server setting; default `batch`). In realtime mode, the 48A plan's cache misses are filled via `embeddings.create` in bounded list batches (same `openai` client), with no watcher wait. The cache stays the hand-off channel.
- Retries on 429/5xx with backoff. Fail fast on 401/403/404 (mark unavailable via the 48A registry).
- V8 spike (10 sequential realtime calls: error rate, p50/p95) before building. Realtime price row added to `price_per_mtok` (48B).

## Non-goals

- A separate code path for storage/retrieval. Realtime changes only how cache misses are filled.

## Output contract (sketch)

- With `DOUBLEWORD_MODE=realtime`, a DoubleWord experiment completes without entering `pre_embed.state=waiting`, and results show `embed_mode="realtime"`.

## Scenarios (to expand at promotion)

```gherkin
Scenario: Realtime mode fills cache misses without waiting
  Given DOUBLEWORD_MODE realtime and a stubbed DoubleWord embeddings endpoint
  When a DoubleWord experiment is submitted
  Then its runs execute without a waiting pre-embed state and results show embed_mode realtime

Scenario Outline: Permission errors fail fast and mark the model unavailable
  Given the stubbed endpoint answers <status>
  Then the experiment fails without retry delay and the model is recorded as unavailable
  Examples: | 401 | 403 | 404 |
```

### Closing Gates
- [ ] Standard EFP closing gates (see 48A) once promoted to Should/Must
