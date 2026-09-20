# tests/conversation/test_session_store.py
"""
Unit tests for SessionStore and InMemorySessionStore (§11, §14).
Includes zero-tolerance session isolation verification.
"""

import pytest
import time
from datetime import datetime, timedelta
from src.conversation.schemas import ConversationTurn
from src.generation.schemas import GroundedAnswer, GenerationMetadata
from src.conversation.session_store import InMemorySessionStore


def create_dummy_turn(turn_index: int = 1, user_query: str = "Test query") -> ConversationTurn:
    dummy_meta = GenerationMetadata(
        llm_provider="mock",
        llm_model="mock-model",
        prompt_version="p26_v1",
        latency_ms_total=10.0
    )
    dummy_answer = GroundedAnswer(
        query=user_query,
        answer_summary="Dummy answer summary",
        answer_detail="Dummy detail",
        applicable_jurisdiction="central",
        evidence_sufficiency="sufficient",
        citations=[],
        caveats=[],
        clarifying_question=None,
        unused_evidence_count=0,
        generation_metadata=dummy_meta,
        safety_flags=[]
    )
    return ConversationTurn(
        turn_id=f"turn_{turn_index}",
        turn_index=turn_index,
        user_query=user_query,
        rewritten_query=None,
        followup_classification="standalone",
        grounded_answer=dummy_answer,
        jurisdiction_carried_forward="central",
        domain_carried_forward="labor_law",
        timestamp_utc=datetime.utcnow().isoformat()
    )


def test_session_creation_and_retrieval():
    store = InMemorySessionStore()
    session = store.create_session(ttl_minutes=30)
    assert session.session_id is not None
    assert session.status == "active"
    assert session.turn_count == 0

    retrieved = store.get_session(session.session_id)
    assert retrieved is not None
    assert retrieved.session_id == session.session_id


def test_add_turn_and_update_state():
    store = InMemorySessionStore()
    session = store.create_session(ttl_minutes=30)
    turn = create_dummy_turn(1, "What is minimum wage?")

    updated_session = store.add_turn(session.session_id, turn, ttl_minutes=30)
    assert updated_session.turn_count == 1
    assert len(updated_session.turns) == 1
    assert updated_session.turns[0].user_query == "What is minimum wage?"


def test_session_expiration():
    store = InMemorySessionStore()
    # Create session with negative TTL (already expired)
    session = store.create_session(ttl_minutes=-5)
    assert store.get_session(session.session_id) is None


def test_sweep_expired_sessions():
    store = InMemorySessionStore()
    s1 = store.create_session(ttl_minutes=60)
    s2 = store.create_session(ttl_minutes=-10)

    swept = store.sweep_expired_sessions()
    assert swept == 1
    assert store.get_session(s1.session_id) is not None
    assert store.get_session(s2.session_id) is None


def test_zero_tolerance_session_isolation():
    """
    CRITICAL §11 Requirement: Verify that session data cannot leak across session IDs.
    """
    store = InMemorySessionStore()
    s1 = store.create_session(ttl_minutes=30)
    s2 = store.create_session(ttl_minutes=30)

    turn_s1 = create_dummy_turn(1, "Confidential query for session 1")
    store.add_turn(s1.session_id, turn_s1)

    # Session 2 must be completely isolated and have 0 turns
    retrieved_s2 = store.get_session(s2.session_id)
    assert retrieved_s2 is not None
    assert retrieved_s2.turn_count == 0
    assert len(retrieved_s2.turns) == 0

    # Ensure querying with fake session id returns None
    assert store.get_session("non_existent_session_id") is None
