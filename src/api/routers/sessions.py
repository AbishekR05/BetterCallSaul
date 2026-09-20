# src/api/routers/sessions.py
"""
Session Management HTTP Router (§5, §6).
Exposes /api/v1/sessions and /api/v1/sessions/{session_id}.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, Response, status

from src.api.schemas.session import (
    CreateSessionRequest,
    SessionResponse,
    SessionListResponse,
)
from src.api.dependencies import (
    get_session_store,
    get_authenticated_user,
    get_authorized_session,
)
from src.api.services.session_service import SessionService
from src.conversation.session_store import SessionStore
from src.auth.schemas import AuthenticatedUser

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


@router.get("", response_model=SessionListResponse, status_code=status.HTTP_200_OK)
async def list_sessions(
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    session_store: SessionStore = Depends(get_session_store),
):
    """Returns all active sessions owned exclusively by the caller (§5)."""
    service = SessionService(session_store)
    return service.list_sessions(authenticated_user.user_id)


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    req: CreateSessionRequest = CreateSessionRequest(),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    session_store: SessionStore = Depends(get_session_store),
):
    """Creates a new persistent session stamped with caller's user_id (§5)."""
    service = SessionService(session_store)
    return service.create_session(authenticated_user.user_id)


@router.get("/{session_id}", response_model=SessionResponse, status_code=status.HTTP_200_OK)
async def get_session(
    session_id: UUID,
    authorized_sid: str = Depends(get_authorized_session),
    session_store: SessionStore = Depends(get_session_store),
):
    """Retrieves session details after ownership verification (§5, §6)."""
    service = SessionService(session_store)
    return service.get_session(authorized_sid)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    authorized_sid: str = Depends(get_authorized_session),
    session_store: SessionStore = Depends(get_session_store),
):
    """Purges a session after ownership verification (§5, §6)."""
    service = SessionService(session_store)
    service.delete_session(authorized_sid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
