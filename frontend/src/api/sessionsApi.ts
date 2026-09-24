// frontend/src/api/sessionsApi.ts
import { fetchApi } from './client';

export interface SessionItem {
  session_id: string;
  created_at_utc: string;
  last_active_utc: string;
  expires_at_utc: string;
  status: string;
  turn_count: number;
}

export interface SessionListResponse {
  sessions: SessionItem[];
}

export const sessionsApi = {
  listSessions: (): Promise<SessionListResponse> => {
    return fetchApi<SessionListResponse>('/api/v1/sessions', {
      method: 'GET',
    });
  },

  createSession: (): Promise<SessionItem> => {
    return fetchApi<SessionItem>('/api/v1/sessions', {
      method: 'POST',
      body: JSON.stringify({}),
    });
  },

  getSession: (sessionId: string): Promise<SessionItem> => {
    return fetchApi<SessionItem>(`/api/v1/sessions/${sessionId}`, {
      method: 'GET',
    });
  },

  deleteSession: (sessionId: string): Promise<void> => {
    return fetchApi<void>(`/api/v1/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  },
};
