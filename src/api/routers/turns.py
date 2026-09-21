# src/api/routers/turns.py
"""
Conversational Turn Submission HTTP Router (§5, §7, §8, §9).
Exposes /api/v1/sessions/{session_id}/turns with session serialization, global concurrency capacity, and timeout protection.
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
    check_rate_limit,
)
from src.api.config import get_api_settings, APISettings
from src.api.hardening.locks import (
    get_session_turn_lock,
    get_turn_concurrency_semaphore,
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
    settings: APISettings = Depends(get_api_settings),
):
    """
    Submits a conversational turn (§5, §7, §8, §9).
    Protected by per-user rate limit, per-session turn serialization lock (409 session_busy),
    global turn concurrency capacity (503 server_busy), and upstream timeout (504 upstream_timeout).
    """
    # 1. Rate Limit Check
    await check_rate_limit("turn_create_user", str(authenticated_user.user_id), settings)

    session_lock = get_session_turn_lock()
    turn_semaphore = get_turn_concurrency_semaphore(
        max_concurrent=settings.max_concurrent_turns,
        queue_wait_timeout_s=settings.queue_wait_timeout_s,
    )

    # 2. Per-Session Turn Serialization Lock (409 session_busy if active turn in progress)
    async with session_lock.lock_session(authorized_sid):
        # 3. Global Turn Concurrency Semaphore (503 server_busy if capacity exceeded)
        async with turn_semaphore.acquire():
            # 4. Turn Execution with timeout boundary (504 upstream_timeout)
            service = TurnService(orchestrator)
            return await service.post_turn_async(
                user_id=authenticated_user.user_id,
                session_id=authorized_sid,
                query=req.query,
                timeout_s=settings.turn_timeout_s,
            )
