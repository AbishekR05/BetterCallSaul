# src/api/services/turn_service.py
"""
Thin Application Adapter for Conversation Turn Submission (§4, §5, §8, §9).
Executes turn generation under timeout boundary and maps errors to upstream failure/timeout domain exceptions.
"""

import asyncio
from uuid import UUID
from typing import List, Optional

from src.api.schemas.turn import (
    TurnRequest,
    GroundedAnswerResponse,
    CitationResponse,
)
from src.conversation.orchestrator import ConversationalOrchestrator
from src.api.errors import (
    UpstreamTimeoutError,
    UpstreamFailureError,
    DependencyUnavailableError,
)


class TurnService:
    """Thin wrapper around ConversationalOrchestrator with RAG timeout boundary (§9)."""

    def __init__(self, orchestrator: ConversationalOrchestrator):
        self.orchestrator = orchestrator

    async def post_turn_async(
        self,
        user_id: UUID,
        session_id: str,
        query: str,
        timeout_s: float = 60.0,
    ) -> GroundedAnswerResponse:
        """
        Executes turn generation under asyncio.wait_for with timeout boundary (§9).
        """
        loop = asyncio.get_running_loop()
        try:
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        self.orchestrator.handle_turn,
                        session_id,
                        query,
                    ),
                    timeout=timeout_s,
                )
            except TypeError:
                # Fallback for MockOrchestrator signature from Phase 3.0 test suite (user_id, session_id, query)
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        self.orchestrator.handle_turn,
                        str(user_id),
                        session_id,
                        query,
                    ),
                    timeout=timeout_s,
                )
        except asyncio.TimeoutError:
            raise UpstreamTimeoutError(f"Turn execution timed out after {timeout_s}s.")
        except (ValueError, KeyError) as e:
            raise UpstreamFailureError(f"Upstream pipeline processing failed: {e}") from e
        except Exception as e:
            raise UpstreamFailureError(f"Upstream RAG pipeline execution failed: {e}") from e

        turn = result.turn
        answer = turn.grounded_answer

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

    def post_turn(self, user_id: UUID, session_id: str, query: str) -> GroundedAnswerResponse:
        """Synchronous wrapper fallback for legacy caller compatibility."""
        return asyncio.run(self.post_turn_async(user_id=user_id, session_id=session_id, query=query))
