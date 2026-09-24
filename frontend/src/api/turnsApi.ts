// frontend/src/api/turnsApi.ts
import { fetchApi } from './client';

export interface Citation {
  document_title: string;
  document_type: string;
  jurisdiction: string;
  section?: string | null;
  source_reference?: string | null;
}

export interface GroundedAnswerResponse {
  session_id: string;
  turn_index: number;
  answer_summary: string;
  answer_detail: string;
  applicable_jurisdiction: string;
  evidence_sufficiency: string;
  citations: Citation[];
  caveats: string[];
  clarifying_question?: string | null;
}

export const turnsApi = {
  postTurn: (
    sessionId: string,
    query: string,
    signal?: AbortSignal
  ): Promise<GroundedAnswerResponse> => {
    return fetchApi<GroundedAnswerResponse>(`/api/v1/sessions/${sessionId}/turns`, {
      method: 'POST',
      body: JSON.stringify({ query }),
      signal,
    });
  },
};
