# Screenshot gallery

Product UI captures for `rag-params-finder`, grouped by flow. Paths are relative to this folder.
The **showcase** (embedded, with captions) lives in the root [README → Screenshots](../../README.md#-screenshots);
this file is the **maintainer index + capture contract**.

Shots are **dashboard captures** (`http://localhost:5374`) from Atlas Local runs so they stay stable and
key-free. CLI captures, when added, are live terminal grabs.

## Contents

### Experiments list (entry surface)

| Shot | Screen |
|------|--------|
| [`01-experiments-list.png`](01-experiments-list.png) | Result-led experiment cards — lifecycle state, sweep outcome, next action |

### Atlas Local + local embeddings — `configs/mongodb/example-local.yaml`

| Shot | Screen |
|------|--------|
| [`example-mongodb-local/02-experiment-detail.png`](example-mongodb-local/02-experiment-detail.png) | Experiment detail — lifecycle, config, run results |
| [`example-mongodb-local/03-search-explorer.png`](example-mongodb-local/03-search-explorer.png) | Search Explorer — best-parameters card, ranked configs |

### Atlas Local + SIE embeddings — `configs/mongodb/example-sie.yaml`

| Shot | Screen |
|------|--------|
| [`example-mongodb-sie/02-experiment-detail.png`](example-mongodb-sie/02-experiment-detail.png) | Experiment detail — SIE (BGE-M3 / Stella-v5) run results |
| [`example-mongodb-sie/03-search-explorer.png`](example-mongodb-sie/03-search-explorer.png) | Search Explorer — SIE ranked configs |

## Naming & flow convention

- `NN-<screen>.png` — **`NN` is a two-digit flow order** (01 entry → drill-down). Keep the order a viewer would follow.
- Group per config/flow in a subfolder (`example-<backend>-<provider>/`); shared entry shots sit at the gallery root.
- One screen per file; crop to the relevant chrome; prefer dark mode for contrast.

## Regenerating shots

Captures require the app running with data (no live-key backend needed):

```bash
./start-services.sh --mongodb-local                       # server :8001 + dashboard :5374
rag-params-finder run --config configs/mongodb/example-local.yaml   # produce data to show
# then capture the dashboard at http://localhost:5374
```

Prefer the **`capture-app-gallery`** skill to (re)capture CLI + dashboard at every drill-down level,
organise into numbered flow subfolders, and refresh this index + the README thumbnail strip.

## When you add or change a shot

1. Save it here under the naming convention above.
2. Add/refresh its row in this index **and** the root [README → Screenshots](../../README.md#-screenshots).
3. Keep captions consistent between the two.
