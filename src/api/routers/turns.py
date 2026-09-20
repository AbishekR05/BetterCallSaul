# src/api/routers/turns.py
"""
Conversational Turn Submission HTTP Router (§5, §8).
Exposes /api/v1/sessions/{session_id}/turns.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, status

from src.api.schemas.turn import (
    TurnRequest,
    GroundedAnswerResponse,
)
from src.api.dependencies import (
    get_orchestrator,
    get_authenticated_user,
    get_authorized_session,
)
from src.api.services.turn_service import TurnService
from src.conversation.orchestrator import ConversationalOrchestrator
from src.auth.schemas import AuthenticatedUser

router = APIRouter(prefix="/api/v1/sessions", tags=["Turns"])


@router.post("/{session_id}/turns", response_model=GroundedAnswerResponse, status_code=status.HTTP_200_OK)
async def post_turn(
    session_id: UUID,
    req: TurnRequest,
    authorized_sid: str = Depends(get_authorized_session),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    orchestrator: ConversationalOrchestrator = Depends(get_orchestrator),
):
    """
    Submits a conversational query turn for a specific session (§5, §8).
    Verified for bearer authentication and session ownership prior to execution.
    """
    service = TurnService(orchestrator)
    return service.post_turn(
        user_id=authenticated_user.user_id,
        session_id=authorized_sid,
        query=req.query,
    )
