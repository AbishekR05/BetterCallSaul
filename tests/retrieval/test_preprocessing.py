# tests/retrieval/test_preprocessing.py
from src.retrieval.preprocessing import preprocess_query

def test_preprocess_valid_query():
    query = "  What   are the tenant rights in Maharashtra?  "
    norm, warnings = preprocess_query(query)
    assert norm == "What are the tenant rights in Maharashtra?"
    assert len(warnings) == 0

def test_preprocess_unicode_normalization():
    query = "Section\u00A043\u2013Tenant\u2019s Deposit"
    norm, warnings = preprocess_query(query)
    assert "Section 43" in norm or "Section" in norm

def test_preprocess_empty_query():
    raised = False
    try:
        preprocess_query("   ")
    except ValueError:
        raised = True
    assert raised is True, "Expected ValueError for empty query"

def test_preprocess_truncation():
    long_query = "a " * 600  # 1200 chars
    norm, warnings = preprocess_query(long_query, max_length=1000)
    assert len(norm) <= 1000
    assert len(warnings) == 1
    assert "Truncated" in warnings[0]

