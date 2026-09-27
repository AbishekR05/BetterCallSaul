# tests/planning/test_retrieval_plan_executor.py
"""
Unit tests for RetrievalPlanExecutor & IntentAwareRetrieverAdapter.
Verifies soft source-mix weighting, clarification short-circuit, and error fallbacks.
"""

import pytest
from unittest.mock import MagicMock
from eval.schemas import ScoredChunk
from src.planning.schemas import (
    LegalQuestionIntent, IntentClassificationResult, RetrievalPlan
)
from src.planning.retrieval_plan_executor import (
    RetrievalPlanExecutor, IntentAwareRetrieverAdapter
)


def test_executor_clarification_short_circuit():
    mock_base = MagicMock()
    executor = RetrievalPlanExecutor(retriever_adapter=mock_base)

    plan = RetrievalPlan(
        intent=LegalQuestionIntent.CLARIFICATION_REQUIRED,
        source_mix={"legislation": 0.0, "judgment": 0.0},
        requires_clarification=True,
        clarification_prompt="Please clarify your query."
    )

    chunks = executor.execute(plan, "Which law applies?", top_k=10)
    
    # Must NOT call base retriever (§7)
    assert chunks == []
    mock_base.retrieve.assert_not_called()


def test_executor_soft_weighting_no_template_truncation():
    mock_base = MagicMock()
    # Provide 3 legislation chunks and 3 judgment chunks
    mock_chunks = [
        ScoredChunk(chunk_id="c1", document_id="d1", text="Statute 1", similarity_score=0.7, provenance={"source_type": "legislation"}),
        ScoredChunk(chunk_id="c2", document_id="d2", text="Judgment 1", similarity_score=0.8, provenance={"source_type": "judgment"}),
        ScoredChunk(chunk_id="c3", document_id="d3", text="Statute 2", similarity_score=0.6, provenance={"source_type": "legislation"}),
        ScoredChunk(chunk_id="c4", document_id="d4", text="Judgment 2", similarity_score=0.75, provenance={"source_type": "judgment"}),
    ]
    mock_base.retrieve.return_value = mock_chunks

    executor = RetrievalPlanExecutor(retriever_adapter=mock_base)

    # Statutory intent (favors legislation)
    plan = RetrievalPlan(
        intent=LegalQuestionIntent.STATUTORY_INFORMATION,
        source_mix={"legislation": 0.8, "judgment": 0.2},
        requires_clarification=False
    )

    results = executor.execute(plan, "What is the penalty for murder?", top_k=4)

    # Must return candidates re-weighted by soft preference, NOT hard truncated to top 2 + top 2
    assert len(results) == 4
    # Legislation chunk c1 should move ahead of judgment c2 due to 0.8 weight multiplier
    assert results[0].chunk_id == "c1"


def test_intent_aware_adapter_trace_and_fallback():
    mock_classifier = MagicMock()
    mock_classifier.classify.side_effect = Exception("Classifier crashed")

    mock_base_adapter = MagicMock()
    mock_base_adapter.retrieve.return_value = [
        ScoredChunk(chunk_id="c1", document_id="d1", text="Fallback text", similarity_score=0.65)
    ]

    adapter = IntentAwareRetrieverAdapter(
        classifier=mock_classifier,
        base_retriever_adapter=mock_base_adapter
    )

    chunks = adapter.retrieve("What is the penalty for murder?", top_k=5)

    # Must complete turn using fallback (§8)
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "c1"
    assert adapter.last_trace is not None
    assert adapter.last_trace.fallback_triggered is True
    assert "Classifier error" in adapter.last_trace.fallback_reason
