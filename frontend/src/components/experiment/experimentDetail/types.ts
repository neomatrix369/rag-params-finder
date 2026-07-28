import type { EnvParams, ExperimentStatus, RunStatus, SweepSummary } from '../../../types';
import { Phase } from '../../../types';

export interface ExperimentDetail {
  experiment_id: string;
  experiment_name: string;
  status: ExperimentStatus;
  created_at?: string;
  completed_at?: string | null;
  run_count?: number;
  grid_equivalent_count?: number;
  failed_count?: number;
  completion_reason?: string;
  bayesian_summary?: {
    best_query_avg_score?: number;
    best_chunk_size?: number;
    best_overlap?: number;
    best_embedding_model?: string;
    best_retrieval_method?: string;
    best_retriever_type?: string;
    grid_equivalent_count?: number;
    planned_trials?: number;
    attempted_trials?: number;
    discarded_trials?: number;
    not_started?: number;
    termination_reason?: string;
  };
  runs?: RunStatus[];
  started_at?: string;
  git_commit?: string;
  git_branch?: string;
  git_dirty?: boolean;
  python_version?: string;
  app_version?: string;
  env_params?: EnvParams;
  data_paths?: string[];
  queries_file?: string;
  retrieval_model?: string | null;
  top_k_initial?: number;
  top_k_final?: number;
  parallelism?: number;
  on_error?: string;
  sweep_summary?: SweepSummary;
  config?: {
    embedding?: {
      provider?: string;
    };
    retrieval?: {
      retrieval_provider?: string;
    };
    execution?: {
      search_strategy?: 'grid' | 'bayesian';
    };
  };
}

export const PHASE_ORDER: Phase[] = [
  Phase.QUEUED, Phase.PARSING, Phase.CHUNKING, Phase.EMBEDDING,
  Phase.STORING, Phase.QUERYING, Phase.RERANKING, Phase.COMPLETE,
];
