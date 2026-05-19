import type { ExperimentDbStats, ExperimentDbStatsSummary, Experiment } from '../types';

type ExperimentLike = Pick<Experiment, 'experiment_id' | 'experiment_name' | 'status' | 'created_at'>;

export function toExperimentDbStatsSummary(
  experiment: ExperimentLike,
  dbStats: ExperimentDbStats,
): ExperimentDbStatsSummary {
  return { ...experiment, ...dbStats };
}

export function findDbStatsInGroups(
  groups: { experiments: ExperimentDbStatsSummary[] }[],
  experimentId: string,
): ExperimentDbStatsSummary | undefined {
  for (const group of groups) {
    const hit = group.experiments.find((row) => row.experiment_id === experimentId);
    if (hit) return hit;
  }
  return undefined;
}
