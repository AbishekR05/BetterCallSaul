# tests/planning/test_p34_metadata_constraints.py
"""
Unit and Integration Tests for Phase 3.4 Hard Metadata-Aware Retrieval Constraints (§9, §10).
Verifies ConstraintExtractor, RetrievalPlan schema extensions, RetrievalPlanner,
RetrievalPlanExecutor, and IntentAwareRetrieverAdapter constraint enforcement.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath('.'))

from src.planning.schemas import (
    LegalQuestionIntent, IntentClassificationResult, RetrievalPlan, HardConstraints, ConstraintInsufficiency
)
from src.planning.constraint_extractor import ConstraintExtractor
from src.planning.retrieval_planner import RetrievalPlanner
from src.planning.retrieval_plan_executor import RetrievalPlanExecutor, IntentAwareRetrieverAdapter


def test_constraint_extractor_supreme_court():
    extractor = ConstraintExtractor()
    query = "Supreme Court precedent on compensation for delayed possession of flat by real estate developer."
    hc = extractor.extract(query)
    
    assert hc is not None
    assert hc.court == ["Supreme Court of India"]
    assert "court" in hc.evidence_spans
    assert "supreme court" in hc.evidence_spans["court"].lower()


def test_constraint_extractor_kerala_high_court():
    extractor = ConstraintExtractor()
    query = "What is the ruling of Kerala High Court regarding land acquisition?"
    hc = extractor.extract(query)
    
    assert hc is not None
    assert hc.court == ["High Court of Kerala"]
    assert "court" in hc.evidence_spans


def test_constraint_extractor_source_type_legislation():
    extractor = ConstraintExtractor()
    query = "What statutory provisions and sections of the bare act govern maternity benefit?"
    hc = extractor.extract(query)
    
    assert hc is not None
    assert hc.source_type == "legislation"
    assert "source_type" in hc.evidence_spans


def test_constraint_extractor_no_constraints():
    extractor = ConstraintExtractor()
    query = "What is the procedure for filing a consumer complaint?"
    hc = extractor.extract(query)
    
    assert hc is None


def test_constraint_extractor_weak_semantic_no_hard_filter():
    extractor = ConstraintExtractor()
    query = "Can my landlord evict me without notice?"
    hc = extractor.extract(query)
    
    assert hc is None


def test_retrieval_planner_attaches_hard_constraints():
    planner = RetrievalPlanner()
    classification = IntentClassificationResult(
        intent=LegalQuestionIntent.CASE_LAW,
        confidence=1.0
    )
    query = "Supreme Court precedent on compensation for delayed possession of flat by real estate developer."
    plan = planner.plan(classification, query)
    
    assert plan.hard_constraints is not None
    assert plan.hard_constraints.court == ["Supreme Court of India"]


def test_failing_query_enforces_supreme_court_without_high_court_substitutes():
    adapter = IntentAwareRetrieverAdapter()
    query = "Supreme Court precedent on compensation for delayed possession of flat by real estate developer."
    
    chunks = adapter.retrieve(query, top_k=10)
    
    # Must NOT substitute High Court chunks!
    for chunk in chunks:
        prov = getattr(chunk, "provenance", {}) or {}
        court = prov.get("court")
        assert court == "Supreme Court of India", f"Disallowed non-Supreme Court chunk returned: {court}"
    
    # Check trace and insufficiency outcome
    assert adapter.last_trace is not None
    assert adapter.last_trace.hard_constraints_applied is not None
    assert adapter.last_trace.hard_constraints_applied["court"] == ["Supreme Court of India"]
    assert adapter.last_trace.constraint_outcome in ["success", "insufficiency"]


def test_explicit_legislation_constraint_no_judgments():
    adapter = IntentAwareRetrieverAdapter()
    query = "What statutory provisions of the bare act govern environmental protection?"
    
    chunks = adapter.retrieve(query, top_k=10)
    
    for chunk in chunks:
        prov = getattr(chunk, "provenance", {}) or {}
        stype = prov.get("source_type") or getattr(chunk, "source_type", None)
        if stype:
            assert stype.lower() == "legislation", f"Disallowed judgment chunk returned: {stype}"


def test_unconstrained_query_preserves_phase33_behavior():
    adapter = IntentAwareRetrieverAdapter()
    query = "How do I file a consumer complaint against a builder?"
    
    chunks = adapter.retrieve(query, top_k=10)
    assert len(chunks) > 0
    assert adapter.last_trace is not None
    assert adapter.last_trace.hard_constraints_applied is None
