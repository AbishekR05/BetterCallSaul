# tests/auth/test_migration_compat.py
"""
Migration & Phase 2.8 Backward Compatibility Test (§18, §20).
Confirms that pre-existing persistence suite tests pass seamlessly against the modified schema.
"""

import pytest
from uuid import uuid4
from src.auth.auth_provider import PasswordAuthProvider
from src.conversation.persistent_session_store import PersistentSessionStore
from tests.conversation.test_persistent_session_store import create_dummy_turn


def test_phase28_persistence_compatibility_with_user_id(tmp_path):
    db_path = str(tmp_path / "compat_test.sqlite")
    store = PersistentSessionStore(backend="sqlite", sqlite_path=db_path)
    auth_provider = PasswordAuthProvider(backend="sqlite", sqlite_path=db_path)

    # 1. Anonymous session creation (user_id=None) for backward compatibility
    session1 = store.create_session()
    assert session1.session_id is not None
    assert session1.user_id is None

    # 2. Owned session creation (user_id provided)
    user_account = auth_provider.create_account("compat_user@example.com", "Password123!")
    user_id = str(user_account.user_id)
    session2 = store.create_session(user_id=user_id)
    assert session2.session_id is not None
    assert session2.user_id == user_id

    # 3. Add turn to owned session using standard dummy turn builder
    turn = create_dummy_turn(1, "What is Article 21?")
    updated_session = store.add_turn(session2.session_id, turn)
    assert updated_session.turn_count == 1

    # 4. Fetch session and verify user_id persistence
    fetched = store.get_session(session2.session_id)
    assert fetched is not None
    assert fetched.user_id == user_id
    assert len(fetched.turns) == 1
    assert fetched.turns[0].user_query == "What is Article 21?"
