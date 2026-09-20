# src/auth/schemas.py
"""
Data models and exception hierarchy for Phase 2.9 Authentication & Authorization.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4


class AuthError(Exception):
    """Base exception class for authentication and authorization errors."""
    pass


class AuthenticationError(AuthError):
    """Raised when authentication fails (invalid credentials, expired token, revoked token, etc.)."""
    pass


class AuthorizationError(AuthError):
    """Raised when an authenticated user attempts to access a session or resource they do not own."""
    pass


class AccountCreationError(AuthError):
    """Raised when account creation fails (e.g. duplicate identifier or invalid credentials)."""
    pass


@dataclass
class User:
    """
    Minimal User identity model (§7).
    """
    user_id: UUID
    auth_identifier: str  # e.g., email or username (case-normalized, unique)
    status: str = "active"  # "active" | "disabled" | "deleted"
    password_hash: Optional[str] = None
    created_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login_at_utc: Optional[datetime] = None


@dataclass
class AuthenticatedUser:
    """
    Minimal authenticated user session token representation (§8).
    Never carries password hash or sensitive credentials.
    """
    user_id: UUID
    auth_identifier: str
    issued_at_utc: datetime
    expires_at_utc: datetime
