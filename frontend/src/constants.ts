/** Product copy for dashboard chrome (shared header). */
export const APP_NAME = 'RAG Params Finder';
export const APP_TAGLINE =
  'Sweep chunking, embeddings, retrieval, and reranking—then inspect what worked on your evaluation queries.';
export const APP_READ_ONLY_NOTE =
  'Experiments start from the CLI; this UI reads your FastAPI backend (cancel is the only write when a run is active).';
export const APP_FOOTNOTE_SUMMARY = 'How this dashboard relates to CLI runs';

/** Polling intervals (ms). */
export const EXPERIMENTS_POLL_MS = 2000;

/** Vector DB stats are expensive on the server — refresh less often than the list. */
export const VECTOR_DB_STATS_POLL_MS = 60_000;

export const DETAIL_POLL_MS = 2000;

/** First “still waiting” warning after slow HTTP (agent-style feedback). */
export const LOADING_STALL_AFTER_MS = 1800;

/** Repeat stalled warnings while awaiting response (ms). */
export const LOADING_STALL_REPEAT_MS = 2400;

/** Dev-console poll breadcrumbs — match backend info_throttled interval. */
export const DEV_POLL_LOG_INTERVAL_MS = 60_000;
