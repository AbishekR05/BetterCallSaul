# tests/planning/test_retrieval_planner.py
"""
Unit tests for RetrievalPlanner deterministic mapping.
"""

import pytest
from src.planning.schemas import (
    LegalQuestionIntent, IntentClassificationResult
)
from src.planning.retrieval_planner import RetrievalPlanner


def test_planner_statutory_mapping():
    planner = RetrievalPlanner()
    classification = IntentClassificationResult(
        intent=LegalQuestionIntent.STATUTORY_INFORMATION,
        domain_hint="Criminal Law",
        confidence=0.9
    )
    plan = planner.plan(classification, "What is the penalty for murder?")
    assert plan.intent == LegalQuestionIntent.STATUTORY_INFORMATION
    assert plan.source_mix["legislation"] == 0.80
    assert plan.source_mix["judgment"] == 0.20
    assert not plan.requires_clarification
    assert plan.domain_filter == "Criminal Law"


def test_planner_case_law_mapping():
    planner = RetrievalPlanner()
    classification = IntentClassificationResult(
        intent=LegalQuestionIntent.CASE_LAW,
        confidence=0.85
    )
    plan = planner.plan(classification, "Why did Supreme Court reject this?")
    assert plan.intent == LegalQuestionIntent.CASE_LAW
    assert plan.source_mix["judgment"] == 0.80
    assert plan.source_mix["legislation"] == 0.20
    assert not plan.requires_clarification


def test_planner_clarification_required_mapping():
    planner = RetrievalPlanner()
    classification = IntentClassificationResult(
        intent=LegalQuestionIntent.CLARIFICATION_REQUIRED,
        confidence=0.95
    )
    plan = planner.plan(classification, "Which law applies?")
    assert plan.intent == LegalQuestionIntent.CLARIFICATION_REQUIRED
    assert plan.requires_clarification
    assert plan.clarification_prompt is not None
