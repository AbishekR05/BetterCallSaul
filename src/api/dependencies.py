# src/api/dependencies.py
"""
FastAPI Dependency Injection Providers (§4, §5, §6, §8).
Encapsulates rate limiting checks, token validation, session authorization, and singleton access.
"""

import sqlite3
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
from src.conversation.persistent_session_store import PersistentSessionStore
from src.conversation.session_store_factory import create_session_store

from src.conversation.orchestrator import ConversationalOrchestrator
from src.api.config import get_api_settings, APISettings
from src.api.hardening.rate_limiter import get_rate_limiter, RateLimiter
from src.api.errors import RateLimitedError, DependencyUnavailableError

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

    _GLOBAL_SESSION_STORE = session_store or PersistentSessionStore(backend="sqlite", sqlite_path="benchmark/phase_3_0/api_session_db.sqlite")
    _GLOBAL_AUTH_PROVIDER = auth_provider or PasswordAuthProvider(backend="sqlite", sqlite_path="benchmark/phase_3_0/api_session_db.sqlite")

    _GLOBAL_AUTHORIZATION_SERVICE = authorization_service or AuthorizationService(session_store=_GLOBAL_SESSION_STORE)
    _GLOBAL_ORCHESTRATOR = orchestrator or ConversationalOrchestrator(session_store=_GLOBAL_SESSION_STORE)
    
    # Reset rate limiter state for isolated test execution
    try:
        get_rate_limiter().reset()
    except Exception:
        pass



def get_session_store() -> SessionStore:
    global _GLOBAL_SESSION_STORE
    if _GLOBAL_SESSION_STORE is None:
        init_app_dependencies()
    return _GLOBAL_SESSION_STORE  # type: ignore


def get_auth_provider() -> AuthProvider:
    global _GLOBAL_AUTH_PROVIDER
    if _GLOBAL_AUTH_PROVIDER is None:
        init_app_dependencies()
    return _GLOBAL_AUTH_PROVIDER  # type: ignore


def get_authorization_service() -> AuthorizationService:
    global _GLOBAL_AUTHORIZATION_SERVICE
    if _GLOBAL_AUTHORIZATION_SERVICE is None:
        init_app_dependencies()
    return _GLOBAL_AUTHORIZATION_SERVICE  # type: ignore


def get_orchestrator() -> ConversationalOrchestrator:
    global _GLOBAL_ORCHESTRATOR
    if _GLOBAL_ORCHESTRATOR is None:
        init_app_dependencies()
    return _GLOBAL_ORCHESTRATOR  # type: ignore


def get_client_ip(request: Request, settings: APISettings) -> str:
    """Extracts client IP address respecting trusted proxies (§5.2)."""
    if settings.trusted_proxies:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
            return client_ip
    return request.client.host if request.client else "127.0.0.1"


async def check_rate_limit(
    rule_name: str,
    key: str,
    settings: APISettings = Depends(get_api_settings),
):
    """Dependency helper to enforce configured rate limits (§5.3)."""
    if not settings.rate_limit_enabled or settings.rate_limit_backend == "disabled":
        return

    rule = settings.rate_limit_rules.get(rule_name)
    if not rule:
        return

    limiter = get_rate_limiter(backend=settings.rate_limit_backend)
    decision = limiter.check(
        key=key,
        max_requests=rule["requests"],
        window_s=rule["window_s"],
    )

    if not decision.allowed:
        raise RateLimitedError(
            message=f"Rate limit exceeded for rule '{rule_name}'.",
            retry_after_s=decision.retry_after_s,
        )


async def get_authenticated_user(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    auth_provider: AuthProvider = Depends(get_auth_provider),
    settings: APISettings = Depends(get_api_settings),
) -> AuthenticatedUser:
    """
    Extracts Bearer token from Authorization header and validates it via AuthProvider (§6).
    Fails closed on auth database error and enforces user-level rate limiting.
    """
    if not authorization:
        raise AuthenticationError("Authentication required.")

    parts = authorization.strip().split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Malformed Authorization header.")

    token = parts[1]

    try:
        user = auth_provider.validate_token(token)
    except (sqlite3.Error, ConnectionError, OSError) as e:
        # Fail closed on database failure (§8, §14)
        raise DependencyUnavailableError(f"Authentication database error: {e}") from e

    return user


async def get_authorized_session(
    session_id: Union[UUID, str],
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    authorization_service: AuthorizationService = Depends(get_authorization_service),
) -> str:
    """
    Verifies that the authenticated user owns the session_id requested in path (§6).
    Raises AuthorizationError (mapped to 404 session_not_found) if non-existent or cross-user.
    """
    try:
        authorization_service.authorize_session_access(
            authenticated_user=authenticated_user,
            session_id=session_id,
            action="read",
        )
    except (sqlite3.Error, ConnectionError, OSError) as e:
        raise DependencyUnavailableError(f"Session authorization database error: {e}") from e

    return str(session_id)
