# tests/auth/test_cross_user_isolation.py
"""
Zero-Tolerance Security Evaluation Suite for Cross-User Isolation (§17, §20).
Enforces zero cross-user access, UUID manipulation resilience, and session isolation.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from src.auth.authorization_service import AuthorizationService
from src.auth.auth_provider import PasswordAuthProvider
from src.auth.schemas import AuthenticatedUser, AuthorizationError
from src.conversation.persistent_session_store import PersistentSessionStore


@pytest.fixture
def sqlite_store(tmp_path):
    db_path = str(tmp_path / "test_cross_user.sqlite")
    return PersistentSessionStore(backend="sqlite", sqlite_path=db_path)


def test_zero_tolerance_cross_user_isolation(sqlite_store):
    auth_service = AuthorizationService(session_store=sqlite_store)
    auth_provider = PasswordAuthProvider(backend="sqlite", sqlite_path=sqlite_store.sqlite_path)

    user_a_obj = auth_provider.create_account("usera@example.com", "PasswordA123!")
    user_b_obj = auth_provider.create_account("userb@example.com", "PasswordB123!")

    user_a = AuthenticatedUser(
        user_id=user_a_obj.user_id,
        auth_identifier="usera@example.com",
        issued_at_utc=datetime.now(timezone.utc),
        expires_at_utc=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    user_b = AuthenticatedUser(
        user_id=user_b_obj.user_id,
        auth_identifier="userb@example.com",
        issued_at_utc=datetime.now(timezone.utc),
        expires_at_utc=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    # User A creates a persistent session
    session_a = sqlite_store.create_session(user_id=str(user_a_obj.user_id))
    # User B creates a persistent session
    session_b = sqlite_store.create_session(user_id=str(user_b_obj.user_id))

    # User A accesses session_a -> Pass
    assert auth_service.authorize_session_access(user_a, session_a.session_id) is True

    # User B accesses session_b -> Pass
    assert auth_service.authorize_session_access(user_b, session_b.session_id) is True

    # User B attempts to access User A's session -> Fail (Zero-tolerance)
    with pytest.raises(AuthorizationError):
        auth_service.authorize_session_access(user_b, session_a.session_id)

    # User A attempts to access User B's session -> Fail (Zero-tolerance)
    with pytest.raises(AuthorizationError):
        auth_service.authorize_session_access(user_a, session_b.session_id)


def test_uuid_manipulation_attack_fails(sqlite_store):
    auth_service = AuthorizationService(session_store=sqlite_store)
    auth_provider = PasswordAuthProvider(backend="sqlite", sqlite_path=sqlite_store.sqlite_path)

    user_obj = auth_provider.create_account("target@example.com", "Password123!")
    user = AuthenticatedUser(
        user_id=user_obj.user_id,
        auth_identifier="target@example.com",
        issued_at_utc=datetime.now(timezone.utc),
        expires_at_utc=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    valid_session = sqlite_store.create_session(user_id=str(user_obj.user_id))

    # Fuzzing or manipulating UUID digits
    manipulated_id = valid_session.session_id[:-4] + "0000"

    with pytest.raises(AuthorizationError):
        auth_service.authorize_session_access(user, manipulated_id)
