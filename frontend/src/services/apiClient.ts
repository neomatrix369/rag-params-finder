import { Experiment } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export async function getExperiments(): Promise<Experiment[]> {
  const response = await fetch(`${API_BASE_URL}/experiments`);
  if (!response.ok) {
    throw new Error('Failed to fetch experiments');
  }
  const data = await response.json();
  return data.experiments || [];
}

export async function getExperiment(experimentId: string): Promise<Experiment> {
  const response = await fetch(`${API_BASE_URL}/experiments/${experimentId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch experiment');
  }
  return response.json();
}

export async function cancelExperiment(experimentId: string): Promise<{ status: string; message: string }> {
  const response = await fetch(`${API_BASE_URL}/experiments/${experimentId}/cancel`, {
    method: 'POST',
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to cancel experiment');
  }
  return response.json();
}
