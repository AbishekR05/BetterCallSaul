# tests/generation/test_pipeline.py
"""
Unit and Integration Test Suite for Phase 2.6 Answer Generation (§13.1).
"""

import sys
import pytest
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from eval.schemas import ScoredChunk
from src.generation.schemas import GroundedAnswer
from src.generation.llm_client import MockLLMClient
from src.generation.pipeline import generate_answer, GroundedRAGPipeline


def create_sample_chunks(confidence_tier="high", jurisdiction="central") -> list[ScoredChunk]:
    """Helper to generate synthetic ScoredChunks for unit tests."""
    return [
        ScoredChunk(
            chunk_id="chk_001",
            document_id="doc_ipc_302",
            text="Section 302 of the Indian Penal Code provides punishment for murder. Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine.",
            similarity_score=0.88,
            confidence_tier=confidence_tier,
            provenance={
                "source_type": "legislation",
                "title": "Indian Penal Code",
                "act": "IPC",
                "section": "302",
                "jurisdiction": jurisdiction
            }
        ),
        ScoredChunk(
            chunk_id="chk_002",
            document_id="doc_crpc_154",
            text="Section 154 of the Code of Criminal Procedure mandates registration of Information in cognizable cases (First Information Report).",
            similarity_score=0.75,
            confidence_tier=confidence_tier,
            provenance={
                "source_type": "legislation",
                "title": "Code of Criminal Procedure",
                "act": "CrPC",
                "section": "154",
                "jurisdiction": jurisdiction
            }
        )
    ]


def test_well_supported_query():
    """Test 1: Well-supported query produces valid answer with citations."""
    chunks = create_sample_chunks()
    mock_client = MockLLMClient(canned_response_mode="sufficient")

    result = generate_answer(
        query="What is the punishment for murder under IPC?",
        scored_chunks=chunks,
        llm_client=mock_client
    )

    assert isinstance(result, GroundedAnswer)
    assert result.evidence_sufficiency == "sufficient"
    assert len(result.citations) > 0
    assert result.citations[0].chunk_id == "chk_001"
    assert "empty_retrieval_input" not in result.safety_flags


def test_empty_retrieval_input_short_circuit():
    """Test 2: Empty evidence list short-circuits cleanly without calling LLM."""
    mock_client = MockLLMClient(canned_response_mode="sufficient")

    result = generate_answer(
        query="Random obscure query",
        scored_chunks=[],
        llm_client=mock_client
    )

    assert result.evidence_sufficiency == "insufficient"
    assert "empty_retrieval_input" in result.safety_flags
    assert result.generation_metadata.latency_ms_generation == 0.0


def test_low_confidence_evidence_fallback():
    """Test 3: Query with only low-confidence evidence falls back to insufficient."""
    chunks = create_sample_chunks(confidence_tier="low")
    mock_client = MockLLMClient(canned_response_mode="sufficient")

    result = generate_answer(
        query="Out of scope query",
        scored_chunks=chunks,
        llm_client=mock_client
    )

    assert result.evidence_sufficiency == "insufficient"
    assert "all_evidence_low_confidence" in result.safety_flags
    assert any("legal advice" in c.lower() or "consult" in c.lower() for c in result.caveats)


def test_malformed_json_fallback():
    """Test 4: Malformed LLM output triggers repair attempt and safe fallback."""
    chunks = create_sample_chunks()
    mock_client = MockLLMClient(canned_response_mode="malformed_json")

    result = generate_answer(
        query="Sample query",
        scored_chunks=chunks,
        llm_client=mock_client
    )

    assert result.evidence_sufficiency == "insufficient"
    assert "generation_parse_failure" in result.safety_flags


def test_invalid_citation_reference_stripped():
    """Test 5: Citation to non-existent ID [E99] is stripped and flagged."""
    chunks = create_sample_chunks()
    mock_client = MockLLMClient(canned_response_mode="invalid_citation")

    result = generate_answer(
        query="Sample query",
        scored_chunks=chunks,
        llm_client=mock_client
    )

    assert "invalid_citation_reference" in result.safety_flags
    assert not any(c.local_id == "E99" for c in result.citations)


def test_jurisdiction_mismatch_flag():
    """Test 6: Claiming state jurisdiction (Karnataka) when evidence is Kerala raises flag."""
    chunks = [
        ScoredChunk(
            chunk_id="chk_kerala_01",
            document_id="doc_kerala_police",
            text="Section 31 of the Kerala Police Act governs police duties in Kerala.",
            similarity_score=0.85,
            confidence_tier="high",
            provenance={"jurisdiction": "Kerala", "source_type": "legislation", "title": "Kerala Police Act"}
        )
    ]

    # Create mock response claiming Karnataka jurisdiction
    from src.generation.response_parser import ResponseParser
    from src.generation.context_builder import ContextBuilder

    cb = ContextBuilder()
    text, id_map = cb.build_context(chunks)

    parser = ResponseParser()
    raw_text = """{
        "answer_summary": "Under Karnataka police laws...",
        "answer_detail": "Duties are governed by police regulations [E1].",
        "applicable_jurisdiction": "Karnataka",
        "evidence_sufficiency": "sufficient",
        "citations_used": ["E1"],
        "caveats": [],
        "clarifying_question": null
    }"""

    parsed, flags = parser.parse_response(raw_text, id_map)
    assert "jurisdiction_claim_mismatch" in flags


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
