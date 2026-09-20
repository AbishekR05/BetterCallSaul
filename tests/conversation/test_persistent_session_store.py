# tests/conversation/test_persistent_session_store.py
"""
Unit tests for PersistentSessionStore (§20).
Tests restart recovery, session isolation, cascading deletion, PII redaction before write, and TTL sweeps.
"""

import pytest
import os
import uuid
import time
from datetime import datetime, timedelta
from src.conversation.persistent_session_store import PersistentSessionStore
from src.conversation.privacy_guard import SessionPrivacyGuard
from src.generation.schemas import GroundedAnswer, GenerationMetadata
from src.conversation.schemas import ConversationTurn, GroundedAnswer


def create_dummy_turn(turn_index: int = 1, user_query: str = "Test query") -> ConversationTurn:
    meta = GenerationMetadata(
        llm_provider="mock",
        llm_model="mock-model",
        prompt_version="p26_v1",
        latency_ms_total=10.0
    )
    answer = GroundedAnswer(
        query=user_query,
        answer_summary="Test summary",
        answer_detail="Test detail",
        applicable_jurisdiction="central",
        evidence_sufficiency="sufficient",
        citations=[],
        caveats=[],
        clarifying_question=None,
        unused_evidence_count=0,
        generation_metadata=meta,
        safety_flags=[]
    )
    return ConversationTurn(
        turn_id=str(uuid.uuid4()),
        turn_index=turn_index,
        user_query=user_query,
        rewritten_query=None,
        followup_classification="standalone",
        grounded_answer=answer,
        jurisdiction_carried_forward="central",
        domain_carried_forward="labor_law",
        timestamp_utc=datetime.utcnow().isoformat()
    )


@pytest.fixture
def sqlite_store(tmp_path):
    db_file = str(tmp_path / "test_session_db.sqlite")
    return PersistentSessionStore(backend="sqlite", sqlite_path=db_file)


def test_persistent_store_create_and_restart_recovery(sqlite_store, tmp_path):
    """Verify that sessions survive store teardown and reconnect (§20)."""
    session = sqlite_store.create_session(ttl_minutes=30)
    turn1 = create_dummy_turn(1, "What is minimum wage?")
    sqlite_store.add_turn(session.session_id, turn1)

    # Teardown store and reconnect
    db_file = sqlite_store.sqlite_path
    reconnected_store = PersistentSessionStore(backend="sqlite", sqlite_path=db_file)

    retrieved = reconnected_store.get_session(session.session_id)
    assert retrieved is not None
    assert retrieved.session_id == session.session_id
    assert retrieved.turn_count == 1
    assert retrieved.turns[0].user_query == "What is minimum wage?"


def test_persistent_store_session_isolation(sqlite_store):
    """Verify zero cross-session data leakage (§20)."""
    s1 = sqlite_store.create_session(ttl_minutes=30)
    s2 = sqlite_store.create_session(ttl_minutes=30)

    t1 = create_dummy_turn(1, "Confidential Session 1 query")
    sqlite_store.add_turn(s1.session_id, t1)

    s2_retrieved = sqlite_store.get_session(s2.session_id)
    assert s2_retrieved is not None
    assert s2_retrieved.turn_count == 0
    assert len(s2_retrieved.turns) == 0


def test_persistent_store_cascading_deletion(sqlite_store):
    """Verify explicit delete_session removes session and all turns (§20)."""
    s = sqlite_store.create_session(ttl_minutes=30)
    t = create_dummy_turn(1, "Query to delete")
    sqlite_store.add_turn(s.session_id, t)

    sqlite_store.delete_session(s.session_id)
    assert sqlite_store.get_session(s.session_id) is None

    # Confirm raw SQLite table is empty for that session
    conn = sqlite_store._get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM conversation_turns WHERE session_id = ?", (s.session_id,))
    count = cur.fetchone()[0]
    conn.close()
    assert count == 0


def test_persistent_store_pii_redaction_before_write(sqlite_store):
    """Verify PII pattern is redacted in raw stored table row (§13, §20)."""
    guard = SessionPrivacyGuard()
    raw_query = "My Aadhaar is 9876 5432 1098 and PAN is ABCDE1234F"
    redacted_query = guard.redact_pii(raw_query)

    s = sqlite_store.create_session(ttl_minutes=30)
    t = create_dummy_turn(1, redacted_query)
    sqlite_store.add_turn(s.session_id, t)

    # Inspect raw SQL row directly
    conn = sqlite_store._get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_query FROM conversation_turns WHERE session_id = ?", (s.session_id,))
    stored_query = cur.fetchone()[0]
    conn.close()

    assert "[REDACTED_AADHAAR]" in stored_query
    assert "[REDACTED_PAN]" in stored_query
    assert "9876 5432 1098" not in stored_query
    assert "ABCDE1234F" not in stored_query


def test_persistent_store_ttl_expiration_sweep(sqlite_store):
    """Verify expired sessions transition to expired status (§20)."""
    s1 = sqlite_store.create_session(ttl_minutes=60)
    s2 = sqlite_store.create_session(ttl_minutes=-10)  # Expired

    swept = sqlite_store.sweep_expired_sessions()
    assert swept == 1
    assert sqlite_store.get_session(s1.session_id) is not None
    assert sqlite_store.get_session(s2.session_id) is None
