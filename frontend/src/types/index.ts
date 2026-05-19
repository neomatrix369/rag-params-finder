// Experiment-level status (mirrored from server/models/enums.py ExperimentStatus)
export type ExperimentStatus = 'running' | 'complete' | 'partial' | 'failed' | 'cancelled';

// Enums (mirrored from server/models/enums.py)

export enum ChunkingMethod {
  FIXED = "fixed",
  RECURSIVE = "recursive",
  TOKEN = "token",
  SENTENCE = "sentence",
  SEMANTIC = "semantic",
}

export enum RetrievalMethod {
  DENSE = "dense",
  SPARSE = "sparse",
  HYBRID = "hybrid",
}

export enum Phase {
  QUEUED = "queued",
  PARSING = "parsing",
  CHUNKING = "chunking",
  EMBEDDING = "embedding",
  STORING = "storing",
  QUERYING = "querying",
  RERANKING = "reranking",
  COMPLETE = "complete",
  FAILED = "failed",
  INTERRUPTED = "interrupted",
}

// Models

export interface EnvParams {
  server_url: string;
  voyage_rpm_limit: number;
  voyage_tpm_limit: number;
  recover_on_boot: boolean;
}

export interface SweepSummary {
  database_provider: string;
  embedding_provider: string;
  models: string[];
  chunking_methods: string[];
  chunk_sizes: number[];
  overlaps: number[];
  retrieval_methods: string[];
  rerank_provider: string;
}

export interface Experiment {
  experiment_id: string;
  experiment_name: string;
  config: Record<string, unknown>;
  created_at: string;
  started_at?: string;
  completed_at?: string | null;
  status: ExperimentStatus;
  run_count?: number;
  failed_count?: number;
  error?: string;
  git_commit?: string;
  git_branch?: string;
  git_dirty?: boolean;
  python_version?: string;
  app_version?: string;
  env_params?: EnvParams;
  data_paths?: string[];
  queries_file?: string;
  rerank_model?: string | null;
  top_k_initial?: number;
  top_k_final?: number;
  parallelism?: number;
  on_error?: string;
  sweep_summary?: SweepSummary;
}

export interface RunStatus {
  run_id: string;
  experiment_id: string;
  phase: Phase;
  database_provider: string;
  embedding_provider: string;
  embedding_model: string;
  chunking_method: ChunkingMethod;
  chunk_size: number;
  overlap: number;
  retrieval_method: RetrievalMethod;
  rerank_provider: string;
  rerank_model?: string | null;
  created_at: string;
  updated_at: string;
  elapsed_ms: number;
  error_message?: string;
}

export interface Chunk {
  id: string;
  text: string;
  index: number;
  embedding_model: string;
  chunk_method: string;
}

export interface SearchResult {
  chunk: Chunk;
  dense_score: number;
  rerank_score?: number;
  retrieval_method: string;
  rank: number;
}

export interface QueryResult {
  query_id: string;
  experiment_id: string;
  run_id: string;
  query_text: string;
  persona_id?: string;
  focus?: string;
  results: SearchResult[];
  top_k: number;
}

// Explorer response types (from GET /experiments/{id}/explore)

export interface RankedConfig {
  rank: number;
  database_provider: string;
  embedding_provider: string;
  embedding_model: string;
  chunking_method: string;
  chunk_size: number;
  overlap: number;
  retrieval_method: string;
  rerank_provider: string;
  max_score: number;
  avg_score: number;
  result_count: number;
}

export interface DetailedResult {
  rank: number;
  score: number;
  raw_score: number;
  database_provider: string;
  embedding_provider: string;
  embedding_model: string;
  chunking_method: string;
  chunk_size: number;
  overlap: number;
  retrieval_method: string;
  rerank_provider: string;
  chunk_text: string;
  query_text: string;
  run_id: string;
  rerank_score?: number | null;
  dense_score: number;
}

export interface ExploreResponse {
  experiment_id: string;
  experiment_name: string;
  query_count: number;
  total_matches: number;
  queries: string[];
  best_params: RankedConfig | null;
  ranked_configs: RankedConfig[];
  detailed_results: DetailedResult[];
}

// Delete response types (from DELETE /experiments/{id})

export interface DeletedCounts {
  experiments: number;
  run_status: number;
  chunks: number;
  results: number;
}

export interface DeleteExperimentResponse {
  status: string;
  experiment_id: string;
  deleted_counts: DeletedCounts;
  message: string;
}
