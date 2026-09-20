# tests/conversation/test_query_rewriter.py
"""
Unit tests for QueryRewriter (§10, §14).
"""

import pytest
from src.generation.llm_client import MockLLMClient
from src.conversation.query_rewriter import QueryRewriter
from tests.conversation.test_session_store import create_dummy_turn


def test_query_rewriter_heuristic_location_shift():
    mock_llm = MockLLMClient()
    rewriter = QueryRewriter(llm_client=mock_llm)

    prior_turn = create_dummy_turn(1, "What is the Shops and Establishments Act in Maharashtra?")
    prior_turn.domain_carried_forward = "Shops and Establishments Act"
    prior_turn.grounded_answer.applicable_jurisdiction = "maharashtra"

    res = rewriter._heuristic_rewrite("What about Karnataka?", [prior_turn])
    assert res.resolution_status == "resolved"
    assert "Karnataka" in res.rewritten_query
    assert "Shops and Establishments Act" in res.rewritten_query
    assert res.carried_jurisdiction == "karnataka"


def test_query_rewriter_heuristic_pronoun_replacement():
    mock_llm = MockLLMClient()
    rewriter = QueryRewriter(llm_client=mock_llm)

    prior_turn = create_dummy_turn(1, "What is Minimum Wages Act?")
    prior_turn.domain_carried_forward = "Minimum Wages Act"

    res = rewriter._heuristic_rewrite("What are the penalties under it?", [prior_turn])
    assert res.resolution_status == "resolved"
    assert "Minimum Wages Act" in res.rewritten_query
