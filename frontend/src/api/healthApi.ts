// frontend/src/api/healthApi.ts
import { fetchApi } from './client';

export interface HealthResponse {
  status: string;
}

export interface ReadyResponse {
  status: 'ready' | 'not_ready';
  checks: {
    session_db: 'ok' | 'fail';
    corpus_db: 'ok' | 'fail';
    orchestrator: 'ok' | 'fail';
    secrets: 'ok' | 'fail';
  };
}

export const healthApi = {
  getHealth: (): Promise<HealthResponse> => {
    return fetchApi<HealthResponse>('/health', { method: 'GET' });
  },

  getReady: (): Promise<ReadyResponse> => {
    return fetchApi<ReadyResponse>('/ready', { method: 'GET' });
  },
};
