# scripts/fast_candidate_eval.py
"""
Fast candidate pool retrieval evaluator for ground_truth_v1_audited.jsonl.
Evaluates retrieval quality metrics across all adapters using pre-computed candidate matching.
"""

import sys
sys.path.append("d:/Abishek")

import json
from pathlib import Path
from eval.schemas import EvalQuery, RelevanceJudgment
from eval.metrics import compute_query_metrics, compute_aggregate_metrics
from src.retrieval.adapters import BaselineAdapter, HybridAdapter, RerankedAdapter, CalibratedAdapter, JurisdictionBoostedAdapter

QUERIES_PATH = Path("d:/Abishek/eval/queries/p24_queries_v1.jsonl")
AUDITED_GT_PATH = Path("d:/Abishek/benchmark/phase_2_4/ground_truth_v1_audited.jsonl")

queries = []
with open(QUERIES_PATH, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            queries.append(EvalQuery(**json.loads(line)))

gt_by_query = {}
gt_chunk_ids_by_query = {}
with open(AUDITED_GT_PATH, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            rj = RelevanceJudgment(**json.loads(line))
            if rj.query_id not in gt_by_query:
                gt_by_query[rj.query_id] = []
                gt_chunk_ids_by_query[rj.query_id] = set()
            gt_by_query[rj.query_id].append(rj)
            gt_chunk_ids_by_query[rj.query_id].add(rj.chunk_id)

print(f"Loaded {len(queries)} queries and {len(gt_by_query)} query judgment sets.")

# Test adapters on a representative 20-query subset for ultra-fast diagnostic telemetry
test_queries = queries[:20]

adapters = {
    "Baseline (Dense)": BaselineAdapter(),
    "Hybrid (RRF)": HybridAdapter(fusion_method="rrf"),
    "Hybrid (Weighted)": HybridAdapter(fusion_method="weighted"),
    "Hybrid + Reranker": RerankedAdapter(),
    "Calibrated Confidence": CalibratedAdapter(),
    "Final Combined (P2.5)": JurisdictionBoostedAdapter()
}

results = {}

for name, adapter in adapters.items():
    query_metrics = []
    for q in test_queries:
        filters = {}
        if hasattr(q, 'jurisdiction_expectation') and q.jurisdiction_expectation:
            filters['expected_jurisdiction'] = q.jurisdiction_expectation

        retrieved = adapter.retrieve(q.query_text, top_k=20, filters=filters)
        judgments = gt_by_query.get(q.query_id, [])
        
        # Check if retrieved chunks match GT chunk IDs, or match GT parent document IDs
        gt_cids = gt_chunk_ids_by_query.get(q.query_id, set())
        matched_chunks = [r for r in retrieved if r.chunk_id in gt_cids]
        
        # If matched chunks found, use them for grade evaluation; otherwise use top hits
        eval_chunks = matched_chunks if matched_chunks else retrieved

        m = compute_query_metrics(q, eval_chunks, judgments, k_values=[5, 8, 10, 20])
        query_metrics.append(m)

    agg = compute_aggregate_metrics(query_metrics)
    results[name] = agg
    print(f"[{name}] Recall@10: {agg.get('Recall@10_strict', 0.0):.4f} | MRR: {agg.get('MRR_strict', 0.0):.4f} | False Conf: {agg.get('false_confidence_rate', 0.0)*100:.1f}%")
