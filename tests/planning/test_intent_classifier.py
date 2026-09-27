# tests/planning/test_intent_classifier.py
"""
Unit tests for LLMIntentClassifier including mock LLM classification and fallback handling.
"""

import pytest
from unittest.mock import MagicMock
from src.planning.schemas import LegalQuestionIntent
from src.planning.intent_classifier import LLMIntentClassifier
from src.generation.llm_client import MockLLMClient
from src.generation.schemas import LLMResponse


def test_classifier_short_query_heuristic():
    classifier = LLMIntentClassifier(llm_client=MockLLMClient())
    res = classifier.classify("Can I sue?")
    assert res.intent == LegalQuestionIntent.CLARIFICATION_REQUIRED
    assert res.confidence >= 0.9


def test_classifier_mock_llm_statutory():
    mock_llm = MagicMock()
    mock_llm.generate.return_value = LLMResponse(
        raw_text='{"intent": "statutory_information", "domain_hint": "Criminal Law", "confidence": 0.9, "reasoning": "Statutory penalty query"}',
        finish_reason="STOP"
    )
    classifier = LLMIntentClassifier(llm_client=mock_llm)
    res = classifier.classify("What is the penalty for murder?")
    assert res.intent == LegalQuestionIntent.STATUTORY_INFORMATION
    assert res.domain_hint == "Criminal Law"
    assert res.confidence == 0.9


def test_classifier_llm_exception_fallback():
    mock_llm = MagicMock()
    mock_llm.generate.side_effect = RuntimeError("API service offline")
    classifier = LLMIntentClassifier(llm_client=mock_llm)
    
    # Must fallback gracefully to MIXED (§8)
    res = classifier.classify("What is the penalty for murder under BNS?")
    assert res.intent == LegalQuestionIntent.MIXED
    assert res.confidence == 0.5
    assert "LLM classifier exception" in res.reasoning


def test_classifier_low_confidence_fallback():
    mock_llm = MagicMock()
    mock_llm.generate.return_value = LLMResponse(
        raw_text='{"intent": "case_law", "confidence": 0.2, "reasoning": "Unsure"}',
        finish_reason="STOP"
    )
    classifier = LLMIntentClassifier(llm_client=mock_llm)
    res = classifier.classify("Is this illegal behavior under municipal bylaws in Delhi?")
    assert res.intent == LegalQuestionIntent.MIXED
    assert "below threshold" in res.reasoning
