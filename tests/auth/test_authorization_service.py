# tests/auth/test_authorization_service.py
"""
Unit tests for AuthorizationService session ownership verification (§9, §14, §20).
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from src.auth.authorization_service import AuthorizationService
from src.auth.schemas import AuthenticatedUser, AuthenticationError, AuthorizationError
from src.conversation.session_store import InMemorySessionStore


def test_authorized_owner_access():
    store = InMemorySessionStore()
    auth_service = AuthorizationService(session_store=store)

    user_id = uuid4()
    auth_user = AuthenticatedUser(
        user_id=user_id,
        auth_identifier="user1@example.com",
        issued_at_utc=datetime.now(timezone.utc),
        expires_at_utc=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    # Create session owned by user_id
    session = store.create_session(user_id=str(user_id))

    # Owner reading/writing their session must succeed
    assert auth_service.authorize_session_access(auth_user, session.session_id, action="read") is True
    assert auth_service.authorize_session_access(auth_user, session.session_id, action="write") is True
    assert auth_service.authorize_session_access(auth_user, session.session_id, action="delete") is True


def test_unauthorized_non_owner_access():
    store = InMemorySessionStore()
    auth_service = AuthorizationService(session_store=store)

    owner_id = uuid4()
    attacker_id = uuid4()

    owner_session = store.create_session(user_id=str(owner_id))

    attacker_user = AuthenticatedUser(
        user_id=attacker_id,
        auth_identifier="attacker@example.com",
        issued_at_utc=datetime.now(timezone.utc),
        expires_at_utc=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    # Attacker attempting to access owner's session must fail with AuthorizationError
    with pytest.raises(AuthorizationError) as exc_info:
        auth_service.authorize_session_access(attacker_user, owner_session.session_id, action="read")

    # Generic error message preventing confirmation of session existence (§9, §14)
    assert "not found or not accessible" in str(exc_info.value).lower()


def test_nonexistent_session_access():
    store = InMemorySessionStore()
    auth_service = AuthorizationService(session_store=store)

    user_id = uuid4()
    auth_user = AuthenticatedUser(
        user_id=user_id,
        auth_identifier="user1@example.com",
        issued_at_utc=datetime.now(timezone.utc),
        expires_at_utc=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    fake_session_id = str(uuid4())

    with pytest.raises(AuthorizationError) as exc_info:
        auth_service.authorize_session_access(auth_user, fake_session_id, action="read")

    # Identical error message as cross-user unauthorized access (§14)
    assert "not found or not accessible" in str(exc_info.value).lower()
