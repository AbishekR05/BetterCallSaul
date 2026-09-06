# eval/metrics.py
"""
Core Evaluation Metrics Engine for Phase 2.4 Retrieval Evaluation Framework.
Computes Recall@K, Precision@K, MRR, NDCG@10, Reliability metrics, Legal-domain metrics, and Latency statistics.
"""

import math
import numpy as np
from typing import List, Dict, Any, Tuple, Set, Optional
from eval.schemas import ScoredChunk, RelevanceJudgment, EvalQuery


def dcg_at_k(grades: List[float], k: int = 10) -> float:
    """Computes Discounted Cumulative Gain (DCG) at K using exponential gain 2^grade - 1."""
    dcg = 0.0
    for rank_idx, grade in enumerate(grades[:k], 1):
        gain = (2.0 ** grade) - 1.0
        discount = math.log2(rank_idx + 1.0)
        dcg += gain / discount
    return dcg


def ndcg_at_k(retrieved_grades: List[float], all_possible_grades: List[float], k: int = 10) -> float:
    """Computes Normalized Discounted Cumulative Gain (NDCG) at K."""
    actual_dcg = dcg_at_k(retrieved_grades, k=k)
    ideal_grades = sorted(all_possible_grades, reverse=True)[:k]
    ideal_dcg = dcg_at_k(ideal_grades, k=k)

    if ideal_dcg == 0.0:
        return 1.0 if actual_dcg == 0.0 else 0.0
    return actual_dcg / ideal_dcg


def compute_query_metrics(
    query: EvalQuery,
    retrieved_items: List[ScoredChunk],
    judgments: List[RelevanceJudgment],
    k_values: List[int] = [5, 8, 10, 20]
) -> Dict[str, Any]:
    """Computes all retrieval metrics for a single query."""

    # Map chunk_id to relevance grade
    gt_map: Dict[str, float] = {j.chunk_id: j.relevance_grade for j in judgments}
    gt_doc_types: Dict[str, str] = {j.chunk_id: (j.document_type or "") for j in judgments}
    gt_jurisdictions: Dict[str, str] = {j.chunk_id: (j.jurisdiction or "") for j in judgments}
    gt_domains: Dict[str, str] = {j.chunk_id: (j.domain or "") for j in judgments}

    # Strict (grade >= 3) and Lenient (grade >= 2) relevant sets
    strict_rel_set = {cid for cid, g in gt_map.items() if g >= 3.0}
    lenient_rel_set = {cid for cid, g in gt_map.items() if g >= 2.0}

    retrieved_ids = [item.chunk_id for item in retrieved_items]
    retrieved_grades = [gt_map.get(cid, 0.0) for cid in retrieved_ids]

    res: Dict[str, Any] = {
        "query_id": query.query_id,
        "domain": query.domain,
        "query_type": query.query_type,
        "jurisdiction_expectation": query.jurisdiction_expectation,
        "difficulty_category": query.difficulty_category,
        "retrieved_count": len(retrieved_ids),
        "gt_strict_count": len(strict_rel_set),
        "gt_lenient_count": len(lenient_rel_set)
    }

    # Handle no_evidence_expected queries separately
    if query.query_type == "no_evidence_expected":
        # False confidence if retriever returned high confidence results
        has_high_conf = any(item.confidence_tier == "high" for item in retrieved_items)
        res["false_confidence"] = 1.0 if has_high_conf else 0.0
        res["insufficiency_correct"] = 0.0 if has_high_conf else 1.0
        return res

    # --- Strict Metrics (grade >= 3) ---
    strict_mrr = 0.0
    for rank_idx, cid in enumerate(retrieved_ids, 1):
        if cid in strict_rel_set:
            strict_mrr = 1.0 / rank_idx
            break
    res["MRR_strict"] = strict_mrr

    # --- Lenient Metrics (grade >= 2) ---
    lenient_mrr = 0.0
    for rank_idx, cid in enumerate(retrieved_ids, 1):
        if cid in lenient_rel_set:
            lenient_mrr = 1.0 / rank_idx
            break
    res["MRR_lenient"] = lenient_mrr

    # Recall & Precision at each K
    for k in k_values:
        top_k_ids = set(retrieved_ids[:k])
        
        # Strict
        if strict_rel_set:
            strict_hits = len(top_k_ids.intersection(strict_rel_set))
            res[f"Recall@{k}_strict"] = strict_hits / len(strict_rel_set)
            res[f"Precision@{k}_strict"] = strict_hits / k
            res[f"Success@{k}_strict"] = 1.0 if strict_hits > 0 else 0.0
        else:
            res[f"Recall@{k}_strict"] = 0.0
            res[f"Precision@{k}_strict"] = 0.0
            res[f"Success@{k}_strict"] = 0.0

        # Lenient
        if lenient_rel_set:
            lenient_hits = len(top_k_ids.intersection(lenient_rel_set))
            res[f"Recall@{k}_lenient"] = lenient_hits / len(lenient_rel_set)
            res[f"Precision@{k}_lenient"] = lenient_hits / k
            res[f"Success@{k}_lenient"] = 1.0 if lenient_hits > 0 else 0.0
        else:
            res[f"Recall@{k}_lenient"] = 0.0
            res[f"Precision@{k}_lenient"] = 0.0
            res[f"Success@{k}_lenient"] = 0.0

    # --- NDCG@10 (Graded Relevance) ---
    all_gt_grades = list(gt_map.values())
    res["NDCG@10"] = ndcg_at_k(retrieved_grades, all_gt_grades, k=10)

    # --- Legal Specific Metrics ---
    # Jurisdiction correctness for state_specific queries
    if "state_specific" in query.jurisdiction_expectation:
        exp_state = query.jurisdiction_expectation.split(":")[-1].strip().lower()
        juris_correct = 0.0
        for item in retrieved_items[:10]:
            chunk_juris = item.provenance.get("jurisdiction", "").lower()
            if exp_state in chunk_juris or chunk_juris in exp_state or "central" in chunk_juris:
                juris_correct = 1.0
                break
        res["jurisdiction_correctness"] = juris_correct

    # Provenance completeness
    prov_complete_count = sum(
        1 for item in retrieved_items[:10]
        if item.document_id and item.chunk_id and item.text
    )
    res["provenance_completeness"] = prov_complete_count / min(10, len(retrieved_items)) if retrieved_items else 0.0

    return res


def compute_aggregate_metrics(query_metrics_list: List[Dict[str, Any]]) -> Dict[str, float]:
    """Aggregates metrics across all evaluated queries."""
    if not query_metrics_list:
        return {}

    # Separate standard queries from no_evidence_expected
    standard_qs = [q for q in query_metrics_list if "false_confidence" not in q]
    no_ev_qs = [q for q in query_metrics_list if "false_confidence" in q]

    agg: Dict[str, float] = {}

    if standard_qs:
        keys_to_mean = [
            "MRR_strict", "MRR_lenient", "NDCG@10", "provenance_completeness",
            "Recall@5_strict", "Recall@8_strict", "Recall@10_strict", "Recall@20_strict",
            "Precision@5_strict", "Precision@8_strict", "Precision@10_strict", "Precision@20_strict",
            "Success@5_strict", "Success@8_strict", "Success@10_strict", "Success@20_strict",
            "Recall@5_lenient", "Recall@8_lenient", "Recall@10_lenient", "Recall@20_lenient",
            "Precision@5_lenient", "Precision@8_lenient", "Precision@10_lenient", "Precision@20_lenient"
        ]

        for key in keys_to_mean:
            vals = [q[key] for q in standard_qs if key in q]
            agg[key] = float(np.mean(vals)) if vals else 0.0

        # Jurisdiction correctness on state queries
        juris_vals = [q["jurisdiction_correctness"] for q in standard_qs if "jurisdiction_correctness" in q]
        if juris_vals:
            agg["jurisdiction_correctness_rate"] = float(np.mean(juris_vals))

    if no_ev_qs:
        agg["false_confidence_rate"] = float(np.mean([q["false_confidence"] for q in no_ev_qs]))
        agg["insufficiency_detection_rate"] = float(np.mean([q["insufficiency_correct"] for q in no_ev_qs]))

    return agg
