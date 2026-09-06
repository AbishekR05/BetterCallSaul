# tests/eval/test_metrics.py
"""
Unit Tests for Phase 2.4 Metrics Calculation Module.
"""

from eval.metrics import dcg_at_k, ndcg_at_k, compute_query_metrics, compute_aggregate_metrics
from eval.annotation_tool import cohen_weighted_kappa
from eval.schemas import EvalQuery, ScoredChunk, RelevanceJudgment


def test_dcg_and_ndcg_hand_computed():
    # Toy example: retrieved grades = [4, 0, 3]
    # DCG@3 = (2^4 - 1)/log2(2) + (2^0 - 1)/log2(3) + (2^3 - 1)/log2(4)
    # DCG@3 = 15/1.0 + 0 + 7/2.0 = 15.0 + 3.5 = 18.5
    grades = [4.0, 0.0, 3.0]
    dcg = dcg_at_k(grades, k=3)
    assert abs(dcg - 18.5) < 1e-4

    # Ideal grades = [4, 3, 0] -> Ideal DCG = (15/1.0) + (7/1.58496) = 15 + 4.416 = 19.416
    ndcg = ndcg_at_k(grades, all_possible_grades=[4.0, 3.0, 0.0], k=3)
    assert 0.0 <= ndcg <= 1.0
    assert abs(ndcg - (18.5 / (15.0 + (7.0 / 1.5849625007211563)))) < 1e-4


def test_cohen_weighted_kappa():
    # Perfect agreement
    y1 = [4.0, 3.0, 0.0, 2.0]
    y2 = [4.0, 3.0, 0.0, 2.0]
    assert abs(cohen_weighted_kappa(y1, y2) - 1.0) < 1e-4

    # Imperfect agreement
    y1 = [4.0, 3.0, 0.0, 2.0]
    y2 = [3.0, 3.0, 0.5, 2.0]
    k = cohen_weighted_kappa(y1, y2)
    assert 0.5 < k < 1.0


def test_query_metrics_strict_vs_lenient():
    q = EvalQuery(query_id="q1", query_text="test query", domain="Consumer Protection")
    
    retrieved = [
        ScoredChunk(chunk_id="c1", document_id="d1", text="text1", similarity_score=0.9),  # grade 2 (lenient match)
        ScoredChunk(chunk_id="c2", document_id="d1", text="text2", similarity_score=0.8),  # grade 4 (strict match)
        ScoredChunk(chunk_id="c3", document_id="d1", text="text3", similarity_score=0.5),  # grade 0 (irrelevant)
    ]
    
    judgments = [
        RelevanceJudgment(query_id="q1", chunk_id="c1", relevance_grade=2.0, grade_label="parent_relevant"),
        RelevanceJudgment(query_id="q1", chunk_id="c2", relevance_grade=4.0, grade_label="exact_relevant"),
    ]
    
    metrics = compute_query_metrics(q, retrieved, judgments, k_values=[3])
    
    # Strict (grade >= 3): first hit at rank 2 (c2) -> MRR = 0.5, Recall@3 = 1.0
    assert metrics["MRR_strict"] == 0.5
    assert metrics["Recall@3_strict"] == 1.0
    
    # Lenient (grade >= 2): first hit at rank 1 (c1) -> MRR = 1.0, Recall@3 = 1.0
    assert metrics["MRR_lenient"] == 1.0
    assert metrics["Recall@3_lenient"] == 1.0
