# tests/conversation/test_context_selector.py
"""
Unit tests for ContextSelector (§9, §14).
"""

import pytest
from src.conversation.context_selector import ContextSelector
from tests.conversation.test_session_store import create_dummy_turn


def test_context_cleared_on_topic_change():
    selector = ContextSelector(max_context_turns=4)
    turns = [create_dummy_turn(1, "Turn 1"), create_dummy_turn(2, "Turn 2")]
    selected, trace = selector.select_context(turns, "What is motor vehicle fine?", "topic_change")

    assert len(selected) == 0
    assert trace.cleared_on_topic_change is True
    assert trace.window_size == 0


def test_context_window_capping():
    selector = ContextSelector(max_context_turns=2)
    turns = [create_dummy_turn(i, f"Turn {i}") for i in range(1, 6)]
    selected, trace = selector.select_context(turns, "What are the penalties under it?", "simple_followup")

    assert len(selected) <= 2
    assert trace.selected_turn_indices == [4, 5] or trace.selected_turn_indices == [5]


def test_context_selection_pronoun_relevance():
    selector = ContextSelector(max_context_turns=4)
    turns = [create_dummy_turn(1, "What is Shops Act?"), create_dummy_turn(2, "What are working hours?")]
    selected, trace = selector.select_context(turns, "Does this apply to overtime?", "simple_followup")

    assert len(selected) > 0
    assert trace.estimated_token_cost > 0
