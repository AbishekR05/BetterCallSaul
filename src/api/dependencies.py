# src/api/dependencies.py
"""
FastAPI Dependency Injection Providers (§4, §6).
Encapsulates token validation and session ownership verification as reusable dependencies.
"""

from typing import Optional, Union
from uuid import UUID
from fastapi import Request, Header, Depends

from src.auth.schemas import (
    AuthenticatedUser,
    AuthenticationError,
    AuthorizationError,
)
from src.auth.auth_provider import AuthProvider, PasswordAuthProvider
from src.auth.authorization_service import AuthorizationService
from src.conversation.session_store import SessionStore
from src.conversation.session_store_factory import create_session_store
from src.conversation.orchestrator import ConversationalOrchestrator

# Application-level singleton instances (initialized at app lifespan startup)
_GLOBAL_SESSION_STORE: Optional[SessionStore] = None
_GLOBAL_AUTH_PROVIDER: Optional[AuthProvider] = None
_GLOBAL_AUTHORIZATION_SERVICE: Optional[AuthorizationService] = None
_GLOBAL_ORCHESTRATOR: Optional[ConversationalOrchestrator] = None


def init_app_dependencies(
    session_store: Optional[SessionStore] = None,
    auth_provider: Optional[AuthProvider] = None,
    authorization_service: Optional[AuthorizationService] = None,
    orchestrator: Optional[ConversationalOrchestrator] = None,
):
    """Initializes global app dependency singletons."""
    global _GLOBAL_SESSION_STORE, _GLOBAL_AUTH_PROVIDER, _GLOBAL_AUTHORIZATION_SERVICE, _GLOBAL_ORCHESTRATOR

    _GLOBAL_SESSION_STORE = session_store or create_session_store(backend="sqlite", sqlite_path="benchmark/phase_3_0/api_session_db.sqlite")
    _GLOBAL_AUTH_PROVIDER = auth_provider or PasswordAuthProvider(backend="sqlite", sqlite_path="benchmark/phase_3_0/api_session_db.sqlite")
    _GLOBAL_AUTHORIZATION_SERVICE = authorization_service or AuthorizationService(session_store=_GLOBAL_SESSION_STORE)
    _GLOBAL_ORCHESTRATOR = orchestrator or ConversationalOrchestrator(session_store=_GLOBAL_SESSION_STORE)


def get_session_store() -> SessionStore:
    """Dependency getter for SessionStore instance."""
    global _GLOBAL_SESSION_STORE
    if _GLOBAL_SESSION_STORE is None:
        init_app_dependencies()
    return _GLOBAL_SESSION_STORE  # type: ignore


def get_auth_provider() -> AuthProvider:
    """Dependency getter for AuthProvider instance."""
    global _GLOBAL_AUTH_PROVIDER
    if _GLOBAL_AUTH_PROVIDER is None:
        init_app_dependencies()
    return _GLOBAL_AUTH_PROVIDER  # type: ignore


def get_authorization_service() -> AuthorizationService:
    """Dependency getter for AuthorizationService instance."""
    global _GLOBAL_AUTHORIZATION_SERVICE
    if _GLOBAL_AUTHORIZATION_SERVICE is None:
        init_app_dependencies()
    return _GLOBAL_AUTHORIZATION_SERVICE  # type: ignore


def get_orchestrator() -> ConversationalOrchestrator:
    """Dependency getter for ConversationalOrchestrator instance."""
    global _GLOBAL_ORCHESTRATOR
    if _GLOBAL_ORCHESTRATOR is None:
        init_app_dependencies()
    return _GLOBAL_ORCHESTRATOR  # type: ignore


async def get_authenticated_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    auth_provider: AuthProvider = Depends(get_auth_provider),
) -> AuthenticatedUser:
    """
    Extracts Bearer token from Authorization header and validates it via AuthProvider (§6).
    Raises AuthenticationError if header is missing, malformed, or token is invalid/expired.
    """
    if not authorization:
        raise AuthenticationError("Authentication required.")

    parts = authorization.strip().split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Authentication failed.")

    token = parts[1]
    return auth_provider.validate_token(token)


async def get_authorized_session(
    session_id: Union[UUID, str],
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    authorization_service: AuthorizationService = Depends(get_authorization_service),
) -> str:
    """
    Verifies that the authenticated user owns the session_id requested in path (§6).
    Raises AuthorizationError if non-existent or cross-user.
    Returns validated session_id string.
    """
    authorization_service.authorize_session_access(
        authenticated_user=authenticated_user,
        session_id=session_id,
        action="read",
    )
    return str(session_id)
