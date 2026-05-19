import type { ExperimentStatus } from '../types';

const TERMINAL_STATUSES: ExperimentStatus[] = ['complete', 'failed', 'partial', 'cancelled'];

export function isTerminalExperimentStatus(status: ExperimentStatus | undefined): boolean {
  if (!status) return false;
  return TERMINAL_STATUSES.includes(status);
}

export function isRunningExperimentStatus(status: ExperimentStatus | undefined): boolean {
  return status === 'running';
}
