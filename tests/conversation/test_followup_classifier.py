# tests/conversation/test_followup_classifier.py
"""
Unit tests for FollowUpClassifier (§9, §14).
"""

import pytest
from src.conversation.followup_classifier import FollowUpClassifier
from tests.conversation.test_session_store import create_dummy_turn


def test_classify_no_turns_is_standalone():
    classifier = FollowUpClassifier()
    res = classifier.classify("What is the minimum wage in Maharashtra?", [])
    assert res == "standalone"


def test_classify_simple_followup_pronouns():
    classifier = FollowUpClassifier()
    prior_turn = create_dummy_turn(1, "What is the Shops and Establishments Act?")
    res = classifier.classify("What are the penalties under it?", [prior_turn])
    assert res == "simple_followup"


def test_classify_simple_followup_location_shift():
    classifier = FollowUpClassifier()
    prior_turn = create_dummy_turn(1, "What is the Shops and Establishments Act in Maharashtra?")
    res = classifier.classify("What about Karnataka?", [prior_turn])
    assert res == "simple_followup"


def test_classify_topic_change():
    classifier = FollowUpClassifier()
    prior_turn = create_dummy_turn(1, "What is the procedure for maternity benefit under labor law?")
    prior_turn.domain_carried_forward = "maternity_benefit"
    res = classifier.classify("What is the penalty for driving without a licence under motor vehicle act?", [prior_turn])
    assert res == "topic_change"


def test_classify_contradictory_followup():
    classifier = FollowUpClassifier()
    prior_turn = create_dummy_turn(1, "What if an employer fails to pay minimum wages?")
    res = classifier.classify("What if I actually already paid the wages instead?", [prior_turn])
    assert res == "contradictory_followup"


def test_classify_ambiguous_followup():
    classifier = FollowUpClassifier()
    t1 = create_dummy_turn(1, "What is the Shops and Establishments Act?")
    t2 = create_dummy_turn(2, "What is the Minimum Wages Act?")
    res = classifier.classify("Which of both carries higher fines?", [t1, t2])
    assert res == "ambiguous_followup"
