# src/api/services/auth_service.py
"""
Thin Application Adapter for Authentication Services (§4, §5).
Translates HTTP DTO requests to/from Phase 2.9 AuthProvider.
"""

from src.api.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    AuthUserResponse,
    AuthTokenResponse,
)
from src.auth.auth_provider import AuthProvider


class AuthService:
    """Thin wrapper around AuthProvider."""

    def __init__(self, auth_provider: AuthProvider):
        self.auth_provider = auth_provider

    def register(self, req: RegisterRequest) -> AuthUserResponse:
        user = self.auth_provider.create_account(
            auth_identifier=req.auth_identifier,
            raw_password=req.password,
        )
        return AuthUserResponse(
            user_id=user.user_id,
            auth_identifier=user.auth_identifier,
            created_at_utc=user.created_at_utc,
        )

    def login(self, req: LoginRequest) -> AuthTokenResponse:
        auth_user, token_str = self.auth_provider.authenticate({
            "auth_identifier": req.auth_identifier,
            "password": req.password,
        })
        return AuthTokenResponse(
            access_token=token_str,
            expires_at_utc=auth_user.expires_at_utc,
            token_type="bearer",
        )

    def logout(self, token: str) -> None:
        self.auth_provider.logout(token)
