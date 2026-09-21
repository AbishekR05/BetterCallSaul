# src/api/services/auth_service.py
"""
Thin Application Adapter for Authentication Services (§4, §5, §8).
Translates HTTP DTO requests to/from Phase 2.9 AuthProvider with database exception wrapping.
"""

import sqlite3
from typing import Any
from src.api.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    AuthUserResponse,
    AuthTokenResponse,
)
from src.auth.auth_provider import AuthProvider
from src.auth.schemas import AuthenticationError, AccountCreationError
from src.api.errors import DependencyUnavailableError


class AuthService:
    """Thin wrapper around AuthProvider with database fault handling (§8)."""

    def __init__(self, auth_provider: AuthProvider):
        self.auth_provider = auth_provider

    def _wrap_db_call(self, func, *args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except (AuthenticationError, AccountCreationError):
            raise
        except (sqlite3.Error, ConnectionError, OSError, ValueError) as e:
            # Fail closed on database driver errors (§8)
            raise DependencyUnavailableError(f"Authentication store failure: {e}") from e

    def register(self, req: RegisterRequest) -> AuthUserResponse:
        user = self._wrap_db_call(
            self.auth_provider.create_account,
            auth_identifier=req.auth_identifier,
            raw_password=req.password,
        )
        return AuthUserResponse(
            user_id=user.user_id,
            auth_identifier=user.auth_identifier,
            created_at_utc=user.created_at_utc,
        )

    def login(self, req: LoginRequest) -> AuthTokenResponse:
        auth_user, token_str = self._wrap_db_call(
            self.auth_provider.authenticate,
            {
                "auth_identifier": req.auth_identifier,
                "password": req.password,
            },
        )
        return AuthTokenResponse(
            access_token=token_str,
            expires_at_utc=auth_user.expires_at_utc,
            token_type="bearer",
        )

    def logout(self, token: str) -> None:
        self._wrap_db_call(self.auth_provider.logout, token)
