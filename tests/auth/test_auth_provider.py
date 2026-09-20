# tests/auth/test_auth_provider.py
"""
Unit tests for AuthProvider and PasswordAuthProvider (§8, §13, §20).
"""

import pytest
import time
from uuid import uuid4
from src.auth.auth_provider import PasswordAuthProvider
from src.auth.schemas import (
    User,
    AuthenticatedUser,
    AuthenticationError,
    AccountCreationError,
)
from src.conversation.persistent_session_store import PersistentSessionStore


def test_create_account_and_login_success():
    provider = PasswordAuthProvider()
    email = "lawyer@example.com"
    raw_pass = "ComplexPassphrase123"

    user = provider.create_account(email, raw_pass)
    assert user.auth_identifier == email.lower()
    assert user.status == "active"
    assert user.password_hash is not None
    assert "ComplexPassphrase123" not in user.password_hash

    # Login
    auth_user, token = provider.authenticate({"auth_identifier": email, "password": raw_pass})
    assert auth_user.user_id == user.user_id
    assert auth_user.auth_identifier == email.lower()
    assert token is not None

    # Validate token
    validated = provider.validate_token(token)
    assert validated.user_id == user.user_id


def test_duplicate_account_creation_fails():
    provider = PasswordAuthProvider()
    email = "DUPLICATE@example.com"
    provider.create_account(email, "Password123")

    with pytest.raises(AccountCreationError):
        provider.create_account("duplicate@example.com", "DifferentPass123")


def test_invalid_login_credentials():
    provider = PasswordAuthProvider()
    email = "user@example.com"
    provider.create_account(email, "ValidPassword123")

    # Nonexistent user
    with pytest.raises(AuthenticationError):
        provider.authenticate({"auth_identifier": "nonexistent@example.com", "password": "ValidPassword123"})

    # Wrong password
    with pytest.raises(AuthenticationError):
        provider.authenticate({"auth_identifier": email, "password": "WrongPassword"})


def test_logout_and_revocation():
    provider = PasswordAuthProvider()
    email = "logout_test@example.com"
    provider.create_account(email, "Password123!")

    auth_user, token = provider.authenticate({"auth_identifier": email, "password": "Password123!"})
    assert provider.validate_token(token) is not None

    # Perform logout
    provider.logout(token)

    # Validating revoked token must fail with AuthenticationError
    with pytest.raises(AuthenticationError):
        provider.validate_token(token)


def test_expired_token_validation_fails():
    # TTL set to 0 minutes for immediate expiration test
    provider = PasswordAuthProvider(token_ttl_minutes=0)
    email = "expire@example.com"
    provider.create_account(email, "Password123!")

    auth_user, token = provider.authenticate({"auth_identifier": email, "password": "Password123!"})

    with pytest.raises(AuthenticationError):
        provider.validate_token(token)


def test_rate_limiting_trigger():
    provider = PasswordAuthProvider(min_password_length=8)
    email = "bruteforce@example.com"
    provider.create_account(email, "CorrectPassword123")

    # Perform failed attempts
    for _ in range(5):
        try:
            provider.authenticate({"auth_identifier": email, "password": "BadPassword"})
        except AuthenticationError:
            pass

    # Next attempt should hit rate limit
    with pytest.raises(AuthenticationError) as exc_info:
        provider.authenticate({"auth_identifier": email, "password": "CorrectPassword123"})

    assert "too many failed login attempts" in str(exc_info.value).lower()
