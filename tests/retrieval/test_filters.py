# tests/retrieval/test_filters.py
from src.retrieval.config import RetrievalFilters
from src.retrieval.filters import build_sql_where_clause

def test_empty_filters():
    sql, params = build_sql_where_clause(None)
    assert sql == ""
    assert params == []

def test_jurisdiction_and_source_type_filter():
    filters = RetrievalFilters(jurisdiction="central", source_type="legislation")
    sql, params = build_sql_where_clause(filters)
    assert "WHERE" in sql
    assert "jurisdiction" in sql
    assert "source_type" in sql
    assert len(params) == 2
    assert params[0] == "central"
    assert params[1] == "legislation"

def test_domain_list_filter():
    filters = RetrievalFilters(domains=["Tenancy", "Property"])
    sql, params = build_sql_where_clause(filters)
    assert "document_domains" in sql
    assert len(params) == 2
    assert "tenancy" in params
    assert "property" in params
