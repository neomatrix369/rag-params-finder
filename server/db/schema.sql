-- rag-params-finder — Postgres/pgvector schema (Supabase hosted + local Docker).
--
-- Applied idempotently on every server boot by server.db.postgres.bootstrap_schema().
--
-- Layout note: experiments, run_status, and results keep their promoted, queryable
-- fields as columns and carry the remaining document in a JSONB `doc` column. The
-- StorageBackend port is dict-in/dict-out over documents whose shape is owned by
-- Pydantic models and sweep metadata, so JSONB preserves them without a migration
-- every time a field is added. Chunks are fully columnar because retrieval indexes
-- them directly.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS experiments (
    experiment_id   TEXT PRIMARY KEY,
    experiment_name TEXT        NOT NULL DEFAULT '',
    status          TEXT        NOT NULL DEFAULT 'running',
    created_at      TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    doc             JSONB       NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS experiments_created_at_idx ON experiments (created_at DESC);
CREATE INDEX IF NOT EXISTS experiments_status_idx ON experiments (status);

CREATE TABLE IF NOT EXISTS run_status (
    run_id        TEXT PRIMARY KEY,
    experiment_id TEXT        NOT NULL REFERENCES experiments (experiment_id) ON DELETE CASCADE,
    phase         TEXT        NOT NULL DEFAULT 'queued',
    created_at    TIMESTAMPTZ,
    updated_at    TIMESTAMPTZ,
    doc           JSONB       NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS run_status_experiment_idx ON run_status (experiment_id);
CREATE INDEX IF NOT EXISTS run_status_phase_idx ON run_status (experiment_id, phase);

-- Single chunks table with one nullable vector column per supported dimension.
-- Every retrieval query MUST filter by embedding_model so vectors produced by
-- different models are never compared (PRD acceptance criterion).
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id        TEXT PRIMARY KEY,
    experiment_id   TEXT    NOT NULL REFERENCES experiments (experiment_id) ON DELETE CASCADE,
    run_id          TEXT    NOT NULL,
    text            TEXT    NOT NULL,
    chunk_index     INTEGER NOT NULL,
    embedding_model TEXT    NOT NULL,
    chunk_method    TEXT    NOT NULL,
    chunk_size      INTEGER,
    overlap         INTEGER,
    padding         INTEGER,
    embedding_384   vector(384),
    embedding_1024  vector(1024)
);

CREATE INDEX IF NOT EXISTS chunks_experiment_idx ON chunks (experiment_id);
CREATE INDEX IF NOT EXISTS chunks_run_idx ON chunks (run_id);
CREATE INDEX IF NOT EXISTS chunks_model_idx ON chunks (experiment_id, embedding_model);

CREATE TABLE IF NOT EXISTS results (
    result_id     BIGSERIAL PRIMARY KEY,
    experiment_id TEXT  NOT NULL REFERENCES experiments (experiment_id) ON DELETE CASCADE,
    run_id        TEXT  NOT NULL,
    query_id      TEXT  NOT NULL,
    query_text    TEXT  NOT NULL DEFAULT '',
    doc           JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS results_experiment_idx ON results (experiment_id);
CREATE INDEX IF NOT EXISTS results_run_idx ON results (experiment_id, run_id);
