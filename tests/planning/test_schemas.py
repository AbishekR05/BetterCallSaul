# tests/planning/test_schemas.py
"""
Unit tests for Phase 3.3 Pydantic schemas.
"""

import pytest
from src.planning.schemas import (
    LegalQuestionIntent, IntentClassificationResult, RetrievalPlan, PlanTrace
)


def test_legal_question_intent_enum():
    assert LegalQuestionIntent.STATUTORY_INFORMATION.value == "statutory_information"
    assert LegalQuestionIntent.CASE_LAW.value == "case_law"
    assert LegalQuestionIntent.LEGAL_INTERPRETATION.value == "legal_interpretation"
    assert LegalQuestionIntent.PROCEDURE.value == "procedure"
    assert LegalQuestionIntent.MIXED.value == "mixed"
    assert LegalQuestionIntent.CLARIFICATION_REQUIRED.value == "clarification_required"


def test_intent_classification_result():
    res = IntentClassificationResult(
        intent=LegalQuestionIntent.STATUTORY_INFORMATION,
        domain_hint="Criminal Law",
        confidence=0.95,
        reasoning="Asks about statutory penalty"
    )
    assert res.intent == LegalQuestionIntent.STATUTORY_INFORMATION
    assert res.domain_hint == "Criminal Law"
    assert res.confidence == 0.95


def test_retrieval_plan():
    plan = RetrievalPlan(
        intent=LegalQuestionIntent.CASE_LAW,
        source_mix={"legislation": 0.2, "judgment": 0.8},
        requires_clarification=False
    )
    assert plan.intent == LegalQuestionIntent.CASE_LAW
    assert plan.source_mix["judgment"] == 0.8
    assert not plan.requires_clarification


def test_plan_trace():
    trace = PlanTrace(
        raw_query="What is the penalty for murder?",
        rewritten_query="What is the penalty for murder?",
        classified_intent=LegalQuestionIntent.STATUTORY_INFORMATION,
        source_mix={"legislation": 0.8, "judgment": 0.2},
        fallback_triggered=False,
        latency_ms=12.5
    )
    assert trace.classified_intent == LegalQuestionIntent.STATUTORY_INFORMATION
    assert trace.latency_ms == 12.5
    assert not trace.fallback_triggered
