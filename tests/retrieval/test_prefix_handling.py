# tests/retrieval/test_prefix_handling.py
"""
Section 3 Dedicated Unit Test:
Fails loudly if BGE query instruction prefix is ever changed or omitted.
"""

from src.retrieval.embedding import BGE_QUERY_PREFIX, format_bge_query

EXPECTED_PREFIX = "Represent this sentence for searching relevant passages: "

def test_bge_prefix_constant_exact_match():
    """Verify BGE_QUERY_PREFIX matches the exact required BGE-base v1.5 query instruction."""
    assert BGE_QUERY_PREFIX == EXPECTED_PREFIX, (
        f"BGE instruction prefix mismatch! Expected '{EXPECTED_PREFIX}', got '{BGE_QUERY_PREFIX}'"
    )

def test_format_bge_query_applies_prefix():
    """Verify format_bge_query prepends prefix to query string."""
    query = "What is the penalty for drunk driving under Motor Vehicles Act?"
    prefixed = format_bge_query(query)
    assert prefixed.startswith(EXPECTED_PREFIX)
    assert prefixed == f"{EXPECTED_PREFIX}{query}"
    assert len(prefixed) == len(EXPECTED_PREFIX) + len(query)
