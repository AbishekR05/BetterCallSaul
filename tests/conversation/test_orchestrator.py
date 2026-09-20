# tests/conversation/test_orchestrator.py
"""
End-to-End Orchestrator Integration Tests for Phase 2.7 (§5, §14, §15).
"""

import pytest
from src.generation.llm_client import MockLLMClient
from src.conversation.orchestrator import ConversationalOrchestrator
from src.conversation.session_store import InMemorySessionStore


class MockRetrieverAdapter:
    """Mock Phase 2.5 Retriever Adapter returning empty or dummy chunks."""
    def retrieve(self, query: str, top_k: int = 10, filters=None):
        return []


def test_orchestrator_single_turn_creation():
    mock_retriever = MockRetrieverAdapter()
    mock_llm = MockLLMClient(canned_response_mode="sufficient")
    store = InMemorySessionStore()

    orchestrator = ConversationalOrchestrator(
        session_store=store,
        retriever_adapter=mock_retriever,
        llm_client=mock_llm
    )

    res = orchestrator.handle_turn(session_id=None, user_query="What is the minimum wage in Maharashtra?")
    assert res.session_id is not None
    assert res.turn.turn_index == 1
    assert res.turn.followup_classification == "standalone"
    assert res.turn.grounded_answer is not None


def test_orchestrator_multi_turn_followup():
    mock_retriever = MockRetrieverAdapter()
    mock_llm = MockLLMClient(canned_response_mode="sufficient")
    store = InMemorySessionStore()

    orchestrator = ConversationalOrchestrator(
        session_store=store,
        retriever_adapter=mock_retriever,
        llm_client=mock_llm
    )

    t1_res = orchestrator.handle_turn(session_id=None, user_query="What is the Shops and Establishments Act in Maharashtra?")
    session_id = t1_res.session_id

    t2_res = orchestrator.handle_turn(session_id=session_id, user_query="What about Karnataka?")
    assert t2_res.session_id == session_id
    assert t2_res.turn.turn_index == 2
    assert t2_res.turn.followup_classification == "simple_followup"
    assert t2_res.turn.rewritten_query is not None
    assert "Karnataka" in t2_res.turn.rewritten_query


def test_orchestrator_ambiguous_followup_clarification():
    mock_retriever = MockRetrieverAdapter()
    mock_llm = MockLLMClient(canned_response_mode="sufficient")
    store = InMemorySessionStore()

    orchestrator = ConversationalOrchestrator(
        session_store=store,
        retriever_adapter=mock_retriever,
        llm_client=mock_llm
    )

    res1 = orchestrator.handle_turn(None, "What is Shops Act?")
    res2 = orchestrator.handle_turn(res1.session_id, "What is Minimum Wages Act?")
    res3 = orchestrator.handle_turn(res1.session_id, "Which of both carries higher penalties?")

    assert res3.turn.followup_classification == "ambiguous_followup"
    assert "ambiguous_followup_detected" in res3.turn.grounded_answer.safety_flags
    assert res3.turn.grounded_answer.clarifying_question is not None


def test_orchestrator_pii_redaction_before_persistence():
    mock_retriever = MockRetrieverAdapter()
    mock_llm = MockLLMClient(canned_response_mode="sufficient")
    store = InMemorySessionStore()

    orchestrator = ConversationalOrchestrator(
        session_store=store,
        retriever_adapter=mock_retriever,
        llm_client=mock_llm
    )

    res = orchestrator.handle_turn(None, "My PAN card is ABCDE1234F, what are my tax obligations?")
    assert "[REDACTED_PAN]" in res.turn.user_query
    assert "ABCDE1234F" not in res.turn.user_query
