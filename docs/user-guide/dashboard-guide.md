# Dashboard Guide

![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3-06B6D4?logo=tailwindcss&logoColor=white)

The React dashboard at `http://localhost:5374` visualizes experiments and results. Experiments are **submitted from the CLI**; the dashboard can **pause, resume, cancel, and delete** active sweeps. It polls the server every 2 seconds while any experiment is `running` or `paused`.

**Prerequisites:** MongoDB backend ready ([MongoDB Setup](mongodb-setup.md)) and server running. Optional SIE sweeps require [SIE Setup](sie-setup.md) before submitting `example-mongodb-sie.yaml`.

All screens feature:
- **Loading feedback panels** with progress bars during initial data loads
- **Polling indicators** (subtle "Syncing..." badge) during background refreshes
- **Pagination** for long lists (10 items per page by default)

---

## 🖥️ Screens

### 📋 Experiments List

The landing screen shows all submitted experiments, newest first.

| Column | Description |
|---|---|
| Name | Experiment name with timestamp suffix |
| Status | Color-coded badge (see below) |
| Runs | Total runs / successful runs / failed runs |
| Created | Submission timestamp |

**Pagination**: Shows 10 experiments per page. Navigate using Previous/Next buttons at the bottom.

**Collapsible rows**: Click the chevron on a row to expand inline details without leaving the list. Expansion state is remembered per experiment (`localStorage`).

**Vector DB stats panel** (top of list): Aggregated storage footprint for your Atlas cluster — total chunks, estimated embedding storage, active index names, and per-experiment breakdown. Loads from `GET /experiments/vector-db-stats` on its own schedule (**every 60 s**, 90 s fetch timeout) so a slow stats aggregation does not block the experiment list (2 s poll, 30 s timeout). When Atlas Admin API credentials or `MONGODB_STORAGE_LIMIT_MB` is configured, the panel also shows cluster quota (used/free MB), instance tier (e.g. `M0 (shared)`), cloud provider, and region. The Atlas API does not expose RAM, vCPU, or pricing — only tier and storage limits.

**Actions**:
- **View details**: Click any row to open the Experiment Detail screen
- **Delete**: Click the trash icon button in the Actions column to delete an experiment (confirmation required)
  - Cannot delete **running** experiments — pause or cancel first (**paused** experiments can be deleted)
  - Deletion is permanent and removes all associated data (chunks, results, run statuses)

**Status badges**:

| Badge | Color | Meaning |
|---|---|---|
| `complete` | Green | All planned runs finished successfully |
| `running` | Blue | One or more runs still active |
| `paused` | Violet | Sweep paused — completed runs kept; resume to continue remaining combos |
| `partial` | Yellow | Sweep stopped early — some runs complete, some failed/interrupted, and/or some parameter combos never started |
| `failed` | Red | All runs failed, **or** experiment rejected at search-index preflight (no runs started) |
| `cancelled` | Gray | Experiment was cancelled |

---

### 🔬 Experiment Detail

Opened by clicking a row in the Experiments List. Polls every 2 seconds while status is non-terminal. List→detail navigation reuses cached experiment payloads when available to reduce duplicate fetches.

**Overview panel** (top): Status badge, control buttons, and compact run-outcome metrics in one card:

**Control buttons** (header, via `ExperimentControlButtons`):

| Button | When shown | Effect |
|---|---|---|
| **Pause** | Status is `running` | Stops after current phase; status → `paused` |
| **Resume** | Status is `paused` | Continues from next incomplete parameter combo |
| **Cancel** | Status is `running` | Stops sweep; status → `cancelled` or `partial` |

Pause and cancel are cooperative — the current pipeline phase finishes before the sweep halts. Delete is blocked only for `running` experiments (paused experiments can be deleted).

| Metric | Meaning |
|---|---|
| Total | Planned sweep size (`run_count` from config) |
| Successful | Runs that reached `COMPLETE` |
| Failed | Runs that ended in `FAILED` |
| Interrupted | Runs stopped mid-pipeline (cancel or server restart) |
| Not Started | Parameter combos never queued — sweep stopped before reaching them |
| In Progress | Runs currently executing *(running experiments only)* |
| Duration | Wall time from `started_at` to `completed_at` — shows **—** while `running` or `paused` (clock starts when the first run begins, not at submission) |

These buckets always sum to **Total** on terminal experiments.

Pause, resume, and cancel controls appear **only in the overview header** — not duplicated in the progress card or paused banner.

**Outcome banners** (below runs table):

| Status | Banner |
|---|---|
| `complete` | Green — all planned runs succeeded |
| `partial` | Amber — “Sweep Incomplete” with breakdown (e.g. 41/90 complete, 48 never started) |
| `paused` | Violet — “Experiment Paused” banner with run count; resume via header controls |
| `cancelled` | Gray — runs completed before cancellation |
| Failed runs | Red panel listing `error_message` per run |
| Preflight failed | Experiment `error_message` explains missing indexes or quota — fix with `rag-params-finder indexes list` / `indexes reset`; see [Troubleshooting](troubleshooting.md#-search-index-preflight-failed) |
| Interrupted runs | Amber panel listing interruption reason |

**Vector DB stats card**: Collapsible panel with per-experiment chunk counts, embedding model breakdown, estimated storage, and index names. Loaded from `GET /experiments/{id}/db-stats`.

**Phase indicator dots**: one row of colored dots per run, representing each pipeline phase in order:

```
QUEUED → PARSING → CHUNKING → EMBEDDING → STORING → QUERYING → RERANKING → COMPLETE
```

| Dot color | Meaning |
|---|---|
| Green | Phase completed |
| Blue pulsing | Phase currently active |
| Gray | Phase not yet started |
| Red | Phase failed or run interrupted |

**Runs table**: each row is one config combination (model + chunking method + chunk size + overlap + retrieval method). Expand a row to see per-query results with dense scores and rerank scores.

**Pagination**: Shows 10 runs per page. Navigate using Previous/Next buttons below the table.

**Actions** (top-right header):
- **Delete experiment**: Click the trash icon button to delete the entire experiment
  - Opens a confirmation modal showing experiment details and deletion statistics
  - Cannot delete **running** experiments — pause or cancel first (**paused** experiments can be deleted)
  - Deletion is permanent and removes all associated data

---

### 🔍 Search Explorer

Opened from the Experiment Detail screen once at least one run is complete. Initial load from `GET /experiments/{id}/explore`. While the experiment is still **running**, the screen **polls every 15 s** so ranked configs appear as runs finish — a heavier Mongo aggregate than the experiment list, so the interval is longer. A **"Syncing..."** badge in the header uses delayed show/hide timing (600 ms before appear, 1 s minimum visible) to reduce flicker on fast responses.

Changing the query filter triggers an immediate re-fetch (see **Re-query Progress** below).

#### Two Views: Hyperparameters & Detailed Results

The Search Explorer has **two tabs**:

1. **Hyperparameters** (default) — Aggregated config performance
2. **Detailed Results** — Individual chunk-level results

**Hyperparameters Tab**:

- **Sweep Dimensions** (collapsible) — Shows what parameters were swept: embedding models, chunking methods, chunk sizes, overlaps, retrievers. Displays the Cartesian product calculation (e.g., "1 model × 5 methods × 3 sizes × 2 overlaps × 4 retrievers = 120 configurations"). Collapsed by default.

- **Best Parameters Card** — The **top-ranked configuration** with:
  - 🟠 **Tie alert** (when multiple configs achieve the same max score): "N configs tied at 100%"
  - ℹ️ **Tiebreaker explanation** (when ties exist): "Tiebreaker applied: ranked by query avg (weighted per-query average), then chunk size (smaller = faster), then overlap (smaller = less storage)"
  - **Dual metrics**: Query Avg ✓ (weighted, fairer) + Chunk Avg (unweighted, legacy)
  - All config parameters (database, embedding model, chunking, chunk size, overlap, retrieval)

- **Top 3 Config Cards** — Visual comparison with:
  - ⭐ **#1**: "Best by tiebreaker" badge (when tied)
  - 🔀 **#2, #3**: "Tied" badge (when tied)
  - **Contextual annotations** explaining WHY each config is ranked (e.g., "✓ Ranked #1 by: smallest chunk size (512 vs 1024)")
  - **Dual metrics** for each config

- **All Configurations Table** (if > 3 configs) — Paginated table showing all configs ranked by performance

**Detailed Results Tab**:

- Individual chunk retrieval results (each row = one chunk from one query)
- **Displays**: rank, score, embedding model, retrieval method, **chunking method**, **chunk size/overlap** (purple badge), **query text**, chunk text
- **Expandable chunks**: Click a row to expand truncated text
- Shows **how results map back to configs** via size/overlap badges

#### Weighted Averaging (Query-Level Fairness)

The dashboard shows **two average scores** for each config:

| Metric | Type | Description | When to use |
|---|---|---|---|
| **Query Avg** ✓ | Weighted | Each query contributes equally | **Default** — fairer when queries return different numbers of chunks |
| **Chunk Avg** | Unweighted | Each chunk contributes equally | Legacy — queries with more results dominate |

**Why weighted averaging is fairer**:

If Query 1 returns 5 chunks (scores: 100, 100, 95, 90, 85) and Query 2 returns 3 chunks (scores: 80, 75, 70):
- **Chunk avg**: (100+100+95+90+85+80+75+70)/8 = **87%** ← Query 1 dominates (5/8 = 62.5% weight)
- **Query avg**: (94 + 75)/2 = **84.5%** ← Each query weighted equally (50% each)

Query avg prevents high-scoring queries with many results from hiding poorly-performing queries with few results.

**Configurable**: Set `TIEBREAKER_METRIC=chunk_avg` in `.env` to use legacy unweighted averaging for ranking. Default is `query_avg` (recommended).

#### Tiebreaker Logic (When Configs Tie on Max Score)

When multiple configs achieve the same **max score** (e.g., all at 100%), they are ranked by:

1. **Query avg score** (DESC) — Consistency across queries (weighted, fairer)
2. **Chunk size** (ASC) — Smaller = faster embedding + less storage
3. **Overlap** (ASC) — Smaller = fewer duplicate chunks

The UI shows:
- 🟠 Amber alert badge: "N configs tied at 100%"
- ℹ️ Tiebreaker explanation panel
- ⭐ / 🔀 Visual badges on top 3 cards
- Contextual annotations explaining the ranking

**Ranked config cards**: all config combinations ordered by score, with score bars for visual comparison. Each card shows the embedding model, chunking method, chunk size, overlap, and retrieval method.

**Pagination**: Shows 5 configurations per page. Navigate using Previous/Next buttons below the cards.

**Per-query results**: expand any config card to see the detailed ranked chunks for each query, with individual dense and rerank scores.

---

## 📊 Score Normalization

All scores displayed in the dashboard are normalized to a 0–100 scale using min-max normalization across all results for the experiment:

- Dense scores (cosine similarity, raw range 0–1) are normalized
- Rerank scores (cross-encoder logits, can be negative) are also normalized

This allows direct comparison of configs that used different models or retrieval methods.

---

## 🔄 Polling Behavior

| Screen | Polls | Interval | Stops When |
|---|---|---|---|
| Experiments List | Yes | Every 2 s (`GET /experiments`, 30 s timeout) | Never (always refreshes) |
| Experiments List — Vector DB stats | Yes | Every 60 s (`GET /experiments/vector-db-stats`, 90 s timeout) | Never; may show "loading" while the list is already visible |
| Experiment Detail | Yes | Every 2 s | Status reaches terminal state (`paused` is non-terminal — polling continues) |
| Search Explorer | Yes | Every 15 s while experiment is running | Stops when experiment reaches a terminal status (`complete`, `failed`, `partial`, `cancelled`) |

Terminal statuses: `complete`, `failed`, `partial`, `cancelled` (non-terminal: `running`, `paused`)

---

## 🔄 Loading States & Progress Feedback

### Initial Load

When opening any screen, a **Loading Feedback Panel** appears showing:
- Operation title (e.g., "Loading experiments")
- Progress bar with byte-level download progress
- Activity feed with fetch milestones (start → headers → chunks → complete)

The panel automatically hides when loading completes.

### Background Polling

After the initial load completes, a subtle **"Syncing..."** indicator appears during background refreshes:
- **Experiments List** and **Experiment Detail**: every 2 s (footer or top-right)
- **Search Explorer**: every 15 s while the experiment is still running (top-right; anti-flicker delay)

The indicator shows a blue pulsing dot + "Syncing..." text, stays visible for at least ~1 s on Search Explorer polls, and does not block interaction with the page.

### Re-query Progress (Search Explorer)

When changing the query filter dropdown in Search Explorer, the Loading Feedback Panel re-appears with:
- Title: "Refreshing results…"
- Subtitle: "Re-fetching explorer data (query filter changed or refresh triggered)."
- Progress tracking same as initial load

### Experiment Execution Progress

For **running experiments**, the Experiment Detail screen shows an **Experiment Progress Card** with:
- Circular progress indicator (e.g., "50%")
- Completion status (e.g., "1 of 2 runs completed")
- **Elapsed** time since the first run started (UTC-aware timestamps)
- **ETA** — linear estimate from average time per completed run, with a 1% margin
- Visual feedback: blue gradient background, green progress ring

This card appears **only when status is "running"** and updates every 2 seconds via background polling. Progress is measured against **planned** run count (`run_count`), not just runs already in `run_status`. Elapsed and ETA appear once at least one run has completed. Once the experiment reaches a terminal status, the card is replaced with the outcome banner described above.

**Note**: This is distinct from network loading — the Loading Feedback Panel tracks API data transfer, while the Experiment Progress Card tracks pipeline execution (runs completing).

---

## 👉 See Also

- [Getting Started](getting-started.md) — start the server and dashboard
- [CLI Reference](cli-reference.md) — submit experiments and check status from the terminal
- [Configuration Reference](configuration.md) — understand what each config combination means
- [Troubleshooting](troubleshooting.md) — fix "Loading…" errors or missing results
