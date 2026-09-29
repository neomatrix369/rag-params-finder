-- rag-params-finder — SQLite run-state schema (Slice 55, ADR-008).
--
-- Applied idempotently on every server boot via _bootstrap_schema().
--
-- Run-state only: experiments, run_status, results. No chunks table —
-- SQLite is never a vector store (vector data always goes to VECTOR_STORE_BACKEND).
--
-- Promoted columns mirror the Postgres schema for query compatibility.
-- Non-promoted fields live in a TEXT column as a JSON blob (no native JSONB).
-- Every connection must set WAL mode + busy_timeout before first write:
--   PRAGMA journal_mode=WAL;
--   PRAGMA busy_timeout=5000;
-- These are applied in _connect() so callers never need to remember.

CREATE TABLE IF NOT EXISTS experiments (
    experiment_id   TEXT PRIMARY KEY,
    experiment_name TEXT        NOT NULL DEFAULT '',
    status          TEXT        NOT NULL DEFAULT 'running',
    created_at      TEXT,
    started_at      TEXT,
    completed_at    TEXT,
    vector_store_snapshot TEXT,
    doc             TEXT        NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS experiments_created_at_idx ON experiments (created_at DESC);
CREATE INDEX IF NOT EXISTS experiments_status_idx ON experiments (status);

CREATE TABLE IF NOT EXISTS run_status (
    run_id              TEXT PRIMARY KEY,
    experiment_id       TEXT NOT NULL REFERENCES experiments (experiment_id) ON DELETE CASCADE,
    phase               TEXT NOT NULL DEFAULT 'queued',
    created_at          TEXT,
    updated_at          TEXT,
    embedding_dimensions INTEGER,
    doc                 TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS run_status_experiment_idx ON run_status (experiment_id);
CREATE INDEX IF NOT EXISTS run_status_phase_idx ON run_status (experiment_id, phase);

CREATE TABLE IF NOT EXISTS results (
    result_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT  NOT NULL REFERENCES experiments (experiment_id) ON DELETE CASCADE,
    run_id        TEXT  NOT NULL,
    query_id      TEXT  NOT NULL,
    query_text    TEXT  NOT NULL DEFAULT '',
    doc           TEXT  NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS results_experiment_idx ON results (experiment_id);
CREATE INDEX IF NOT EXISTS results_run_idx ON results (experiment_id, run_id);
