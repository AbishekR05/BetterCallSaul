# src/api/routers/sessions.py
"""
Session Management HTTP Router (§5, §6).
Exposes /api/v1/sessions and /api/v1/sessions/{session_id} with rate limiting.
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
    check_rate_limit,
)
from src.api.config import get_api_settings, APISettings
from src.api.services.session_service import SessionService
from src.conversation.session_store import SessionStore
from src.auth.schemas import AuthenticatedUser

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


@router.get("", response_model=SessionListResponse, status_code=status.HTTP_200_OK)
async def list_sessions(
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    session_store: SessionStore = Depends(get_session_store),
    settings: APISettings = Depends(get_api_settings),
):
    """Returns all active sessions owned exclusively by the caller (§5)."""
    await check_rate_limit("session_read_delete_user", str(authenticated_user.user_id), settings)
    service = SessionService(session_store)
    return service.list_sessions(authenticated_user.user_id)


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    req: CreateSessionRequest = CreateSessionRequest(),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    session_store: SessionStore = Depends(get_session_store),
    settings: APISettings = Depends(get_api_settings),
):
    """Creates a new persistent session stamped with caller's user_id (§5)."""
    await check_rate_limit("session_create_user", str(authenticated_user.user_id), settings)
    service = SessionService(session_store)
    return service.create_session(authenticated_user.user_id)


@router.get("/{session_id}", response_model=SessionResponse, status_code=status.HTTP_200_OK)
async def get_session(
    session_id: UUID,
    authorized_sid: str = Depends(get_authorized_session),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    session_store: SessionStore = Depends(get_session_store),
    settings: APISettings = Depends(get_api_settings),
):
    """Retrieves session details after ownership verification (§5, §6)."""
    await check_rate_limit("session_read_delete_user", str(authenticated_user.user_id), settings)
    service = SessionService(session_store)
    return service.get_session(authorized_sid)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    authorized_sid: str = Depends(get_authorized_session),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    session_store: SessionStore = Depends(get_session_store),
    settings: APISettings = Depends(get_api_settings),
):
    """Purges a session after ownership verification (§5, §6)."""
    await check_rate_limit("session_read_delete_user", str(authenticated_user.user_id), settings)
    service = SessionService(session_store)
    service.delete_session(authorized_sid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
