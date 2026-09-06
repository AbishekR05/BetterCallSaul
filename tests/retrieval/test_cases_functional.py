# tests/retrieval/test_cases_functional.py
"""
Section 22 Required Functional Test Cases for Phase 2.3 Legal Retriever.
Validates all 8 required retrieval behavioral cases against the database.
"""

from src.retrieval.config import RetrievalConfig, RetrievalFilters
from src.retrieval.retriever import LegalRetriever



@pytest.fixture(scope="module")
def retriever():
    cfg = RetrievalConfig(
        use_gpu=True,
        final_k=5,
        high_confidence_threshold=0.50,
        low_confidence_threshold=0.35
    )
    return LegalRetriever(config=cfg)


def test_case_1_successful_retrieval(retriever):
    """Case 1: Successful retrieval for a clear layman legal question."""
    query = "What are the rules regarding tenant security deposit refund?"
    res = retriever.retrieve(query)
    
    assert res.error is None
    assert res.returned_count > 0
    assert len(res.results) > 0
    assert res.results[0].similarity_score >= 0.35
    assert res.results[0].provenance.chunk_id != ""


def test_case_2_metadata_filtering(retriever):
    """Case 2: Filtering by jurisdiction = 'central' returns matching central documents."""
    query = "What is the procedure for filing an environmental clearance application?"
    filters = RetrievalFilters(jurisdiction="central")
    res = retriever.retrieve(query, filters=filters)
    
    assert res.error is None
    for item in res.results:
        assert item.provenance.jurisdiction.lower() == "central"


def test_case_3_cross_jurisdiction(retriever):
    """Case 3: Unfiltered query across jurisdictions vs filtered query."""
    query = "land acquisition compensation procedure"
    res_unfiltered = retriever.retrieve(query)
    assert res_unfiltered.returned_count > 0
    
    filters = RetrievalFilters(source_type="legislation")
    res_filtered = retriever.retrieve(query, filters=filters)
    assert res_filtered.error is None
    for item in res_filtered.results:
        assert item.provenance.source_type == "legislation"


def test_case_4_legislation_retrieval(retriever):
    """Case 4: Legislation specific retrieval."""
    query = "Section 43 Maharashtra Rent Control Act tenant deposit"
    filters = RetrievalFilters(source_type="legislation")
    res = retriever.retrieve(query, filters=filters)
    
    assert res.returned_count > 0
    assert res.results[0].provenance.source_type == "legislation"


def test_case_5_judgment_retrieval(retriever):
    """Case 5: Judgment specific retrieval with court/citation metadata."""
    query = "High Court judgment on bail in non-bailable offense"
    filters = RetrievalFilters(source_type="judgment")
    res = retriever.retrieve(query, filters=filters)
    
    assert res.error is None
    if res.returned_count > 0:
        assert res.results[0].provenance.source_type == "judgment"


def test_case_6_mixed_legislation_judgment_retrieval(retriever):
    """Case 6: Mixed legislation + judgment retrieval ranked by similarity."""
    query = "tenant eviction notice period and court rulings"
    res = retriever.retrieve(query)
    
    assert res.error is None
    assert res.returned_count > 0
    # Scores should be sorted descending
    scores = [item.similarity_score for item in res.results]
    assert scores == sorted(scores, reverse=True)


def test_case_7_ambiguous_questions(retriever):
    """Case 7: Ambiguous/vague layman question."""
    query = "Can I do that legal thing?"
    res = retriever.retrieve(query)
    
    assert res.error is None
    # Vague question should either return lower confidence tier or insufficient_evidence
    if res.returned_count > 0:
        assert res.results[0].similarity_score < 0.65


def test_case_8_no_evidence_questions(retriever):
    """Case 8: Out-of-domain question absent from corpus triggers insufficient_evidence."""
    query = "Quantum mechanics wave function collapse protocol in Martian colony 2099"
    # Set strict thresholds for out-of-domain test
    cfg = RetrievalConfig(low_confidence_threshold=0.55, min_acceptable_results=1)
    res = retriever.retrieve(query, config=cfg)
    
    assert res.error is None
    assert res.insufficient_evidence is True

