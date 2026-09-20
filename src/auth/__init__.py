# src/auth/__init__.py
"""
Phase 2.9 Authentication, Authorization & User Identity Boundary Package.
"""

from src.auth.schemas import (
    User,
    AuthenticatedUser,
    AuthError,
    AuthenticationError,
    AuthorizationError,
    AccountCreationError,
)
from src.auth.password_hashing import hash_password, verify_password
from src.auth.rate_limiter import LoginRateLimiter
from src.auth.auth_provider import AuthProvider, PasswordAuthProvider
from src.auth.authorization_service import AuthorizationService

__all__ = [
    "User",
    "AuthenticatedUser",
    "AuthError",
    "AuthenticationError",
    "AuthorizationError",
    "AccountCreationError",
    "hash_password",
    "verify_password",
    "LoginRateLimiter",
    "AuthProvider",
    "PasswordAuthProvider",
    "AuthorizationService",
]
