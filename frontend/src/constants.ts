/** Product copy for dashboard chrome (shared header). */
export const APP_NAME = 'RAG Params Finder';
export const APP_TAGLINE =
  'Sweep chunking, embeddings, retrieval, and reranking—then inspect what worked on your evaluation queries.';
export const APP_READ_ONLY_NOTE =
  'Experiments start from the CLI; this UI reads your FastAPI backend (cancel is the only write when a run is active).';

/** Polling intervals (ms). */
export const EXPERIMENTS_POLL_MS = 500;

export const DETAIL_POLL_MS = 2000;

/** First “still waiting” warning after slow HTTP (agent-style feedback). */
export const LOADING_STALL_AFTER_MS = 1800;

/** Repeat stalled warnings while awaiting response (ms). */
export const LOADING_STALL_REPEAT_MS = 2400;
