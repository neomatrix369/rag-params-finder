# Dashboard Guide

![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3-06B6D4?logo=tailwindcss&logoColor=white)

The React dashboard at `http://localhost:5173` provides a read-only view of experiments and results. It polls the server every 2 seconds while any experiment is running.

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

Click any row to open the Experiment Detail screen.

**Status badges**:

| Badge | Color | Meaning |
|---|---|---|
| `complete` | Green | All runs finished successfully |
| `running` | Blue | One or more runs still active |
| `partial` | Yellow | Some runs completed, some failed |
| `failed` | Red | All runs failed |
| `cancelled` | Gray | Experiment was cancelled |

---

### 🔬 Experiment Detail

Opened by clicking a row in the Experiments List. Polls every 2 seconds while status is non-terminal.

**Metric cards** (top row):
- Total Runs — number of config combinations in the sweep
- Successful — runs that reached COMPLETE
- Failed — runs that hit an error
- Avg Duration — mean elapsed time across completed runs

**Phase indicator dots**: one row of colored dots per run, representing each pipeline phase in order:

```
QUEUED → PARSING → CHUNKING → EMBEDDING → STORING → QUERYING → RERANKING → COMPLETE
```

| Dot color | Meaning |
|---|---|
| Green | Phase completed |
| Blue pulsing | Phase currently active |
| Gray | Phase not yet started |
| Red | Phase failed |

**Runs table**: each row is one config combination (model + chunking method + chunk size + overlap + retrieval method). Expand a row to see per-query results with dense scores and rerank scores.

**Pagination**: Shows 10 runs per page. Navigate using Previous/Next buttons below the table.

---

### 🔍 Search Explorer

Opened from the Experiment Detail screen once at least one run is complete. Loads once from `GET /experiments/{id}/explore` (no polling).

**Best parameters card**: the top-scoring config combination with its overall relevance score, highlighted at the top of the screen.

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
| Experiments List | Yes | Every 2 s | Never (always refreshes) |
| Experiment Detail | Yes | Every 2 s | Status reaches terminal state |
| Search Explorer | No | — | Loads once |

Terminal statuses: `complete`, `failed`, `partial`, `cancelled`

---

## 🔄 Loading States & Progress Feedback

### Initial Load

When opening any screen, a **Loading Feedback Panel** appears showing:
- Operation title (e.g., "Loading experiments")
- Progress bar with byte-level download progress
- Activity feed with fetch milestones (start → headers → chunks → complete)

The panel automatically hides when loading completes.

### Background Polling

After the initial load completes, a subtle **"Syncing..."** indicator appears briefly at the bottom (Experiments List) or top-right (Experiment Detail, Search Explorer) during background refreshes every 2 seconds. This indicator:
- Shows a blue pulsing dot + "Syncing..." text
- Appears only during the poll (100–500ms)
- Does not block interaction with the page

### Re-query Progress (Search Explorer)

When changing the query filter dropdown in Search Explorer, the Loading Feedback Panel re-appears with:
- Title: "Refreshing results…"
- Subtitle: "Re-fetching explorer data (query filter changed or refresh triggered)."
- Progress tracking same as initial load

---

## 👉 See Also

- [Getting Started](getting-started.md) — start the server and dashboard
- [CLI Reference](cli-reference.md) — submit experiments and check status from the terminal
- [Configuration Reference](configuration.md) — understand what each config combination means
- [Troubleshooting](troubleshooting.md) — fix "Loading…" errors or missing results
