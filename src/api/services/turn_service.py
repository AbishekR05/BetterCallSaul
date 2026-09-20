# src/api/services/turn_service.py
"""
Thin Application Adapter for Conversation Turn Submission (§4, §5, §8).
Translates HTTP TurnRequest to ConversationalOrchestrator.handle_turn and maps result to GroundedAnswerResponse.
"""

from uuid import UUID
from typing import List

from src.api.schemas.turn import (
    TurnRequest,
    GroundedAnswerResponse,
    CitationResponse,
)
from src.conversation.orchestrator import ConversationalOrchestrator


class TurnService:
    """Thin wrapper around ConversationalOrchestrator."""

    def __init__(self, orchestrator: ConversationalOrchestrator):
        self.orchestrator = orchestrator

    def post_turn(self, user_id: UUID, session_id: str, query: str) -> GroundedAnswerResponse:
        """
        Executes a conversation turn via Phase 2.7 Orchestrator and serializes public response (§8).
        """
        result = self.orchestrator.handle_turn(
            user_id=str(user_id),
            session_id=session_id,
            user_query=query,
        )

        turn = result.turn
        answer = turn.grounded_answer

        # Map citations to CitationResponse models
        citation_responses: List[CitationResponse] = []
        for c in getattr(answer, "citations", []):
            citation_responses.append(
                CitationResponse(
                    document_title=getattr(c, "title", "") or getattr(c, "document_id", ""),
                    document_type=getattr(c, "document_type", "legislation"),
                    jurisdiction=getattr(c, "jurisdiction", "central"),
                    section=getattr(c, "section", None),
                    source_reference=getattr(c, "source_url", None) or getattr(c, "act", None),
                )
            )

        return GroundedAnswerResponse(
            session_id=UUID(result.session_id),
            turn_index=turn.turn_index,
            answer_summary=getattr(answer, "answer_summary", ""),
            answer_detail=getattr(answer, "answer_detail", ""),
            applicable_jurisdiction=getattr(answer, "applicable_jurisdiction", "unclear"),
            evidence_sufficiency=getattr(answer, "evidence_sufficiency", "insufficient"),
            citations=citation_responses,
            caveats=getattr(answer, "caveats", []),
            clarifying_question=getattr(answer, "clarifying_question", None),
        )
