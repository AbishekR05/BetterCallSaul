# tests/retrieval/test_result_schema.py
import json
from src.retrieval.schema import RetrievalResult, RetrievalResultItem, ProvenanceFields, RetrievalTiming

def test_retrieval_result_json_serialization():
    prov = ProvenanceFields(
        document_id="doc_1",
        chunk_id="chk_1",
        source_type="legislation",
        title="Rent Control Act",
        jurisdiction="central"
    )
    item = RetrievalResultItem(
        chunk_id="chk_1",
        document_id="doc_1",
        text="Sample text for tenant deposit",
        similarity_score=0.78,
        confidence_tier="high",
        match_type="direct",
        provenance=prov
    )
    result = RetrievalResult(
        query="tenant deposit rights",
        normalized_query="tenant deposit rights",
        insufficient_evidence=False,
        candidate_count=10,
        returned_count=1,
        results=[item],
        timing=RetrievalTiming(total_latency_ms=45.2)
    )
    
    json_str = result.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["query"] == "tenant deposit rights"
    assert len(parsed["results"]) == 1
    assert parsed["results"][0]["similarity_score"] == 0.78
    assert parsed["results"][0]["provenance"]["title"] == "Rent Control Act"
