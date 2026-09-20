# src/api/routers/auth.py
"""
Authentication HTTP Router (§5).
Exposes /api/v1/auth/register, /api/v1/auth/login, and /api/v1/auth/logout.
"""

from fastapi import APIRouter, Depends, Header, Response, status
from typing import Optional

from src.api.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    AuthUserResponse,
    AuthTokenResponse,
)
from src.api.dependencies import get_auth_provider, get_authenticated_user
from src.api.services.auth_service import AuthService
from src.auth.auth_provider import AuthProvider
from src.auth.schemas import AuthenticatedUser, AuthenticationError

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthUserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    auth_provider: AuthProvider = Depends(get_auth_provider),
):
    """Creates a new user account (§5)."""
    service = AuthService(auth_provider)
    return service.register(req)


@router.post("/login", response_model=AuthTokenResponse, status_code=status.HTTP_200_OK)
async def login(
    req: LoginRequest,
    auth_provider: AuthProvider = Depends(get_auth_provider),
):
    """Authenticates credentials and issues a bearer token (§5)."""
    service = AuthService(auth_provider)
    return service.login(req)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
    auth_provider: AuthProvider = Depends(get_auth_provider),
):
    """Revokes an active bearer token (§5)."""
    if not authorization:
        raise AuthenticationError("Authentication required.")
    parts = authorization.strip().split(" ")
    if len(parts) != 2:
        raise AuthenticationError("Authentication failed.")

    service = AuthService(auth_provider)
    service.logout(parts[1])
    return Response(status_code=status.HTTP_204_NO_CONTENT)
