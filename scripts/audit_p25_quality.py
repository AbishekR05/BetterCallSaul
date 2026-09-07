# scripts/audit_p25_quality.py
"""
Phase 2.5 Retrieval Quality Audit Script.
Evaluates all 5 RetrieverAdapters against the pilot ground-truth candidate pool (1,000-chunk annotated space)
and reports authentic Recall@K, Precision@K, MRR, NDCG@10, False-Confidence, and Latency.
"""

import sys
sys.path.append("d:/Abishek")

import json
import time
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Set

from eval.schemas import EvalQuery, RelevanceJudgment, ScoredChunk
from eval.metrics import compute_query_metrics, compute_aggregate_metrics

from src.retrieval.adapters import (
    BaselineAdapter,
    HybridAdapter,
    RerankedAdapter,
    CalibratedAdapter,
    JurisdictionBoostedAdapter
)

QUERIES_PATH = Path("d:/Abishek/eval/queries/p24_queries_v1.jsonl")
AUDITED_GT_PATH = Path("d:/Abishek/benchmark/phase_2_4/ground_truth_v1_audited.jsonl")
OUTPUT_DIR = Path("d:/Abishek/benchmark/phase_2_5")


def audit_phase_2_5_quality():
    print("==================================================")
    print("PHASE 2.5 RETRIEVAL QUALITY AUDIT")
    print("==================================================")

    # 1. Load Queries and Ground Truth
    queries: List[EvalQuery] = []
    with open(QUERIES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(EvalQuery(**json.loads(line)))

    gt_by_query: Dict[str, List[RelevanceJudgment]] = {}
    pilot_gt_chunk_ids: Set[str] = set()

    with open(AUDITED_GT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rj = RelevanceJudgment(**json.loads(line))
                pilot_gt_chunk_ids.add(rj.chunk_id)
                if rj.query_id not in gt_by_query:
                    gt_by_query[rj.query_id] = []
                gt_by_query[rj.query_id].append(rj)

    print(f"Loaded {len(queries)} queries and {len(pilot_gt_chunk_ids):,} ground-truth chunk IDs.")

    adapters = {
        "Baseline (Dense)": BaselineAdapter(),
        "Hybrid (RRF)": HybridAdapter(fusion_method="rrf"),
        "Hybrid (Weighted)": HybridAdapter(fusion_method="weighted"),
        "Hybrid + Reranker": RerankedAdapter(),
        "Calibrated Confidence": CalibratedAdapter(),
        "Final Combined (P2.5)": JurisdictionBoostedAdapter()
    }

    audit_results: Dict[str, Dict[str, Any]] = {}

    for name, adapter_instance in adapters.items():
        print(f"\nAuditing Adapter: '{name}'...")
        query_metrics_list = []
        latencies_ms = []

        for idx, q in enumerate(queries, 1):
            start_t = time.time()
            filters = {}
            if hasattr(q, 'jurisdiction_expectation') and q.jurisdiction_expectation:
                filters['expected_jurisdiction'] = q.jurisdiction_expectation

            # Retrieve top 50 candidates
            retrieved_chunks = adapter_instance.retrieve(q.query_text, top_k=50, filters=filters)
            lat_ms = (time.time() - start_t) * 1000.0
            latencies_ms.append(lat_ms)

            # Filter candidates to pilot candidate space to evaluate relative ranking & recall capability
            pilot_filtered_chunks = [c for c in retrieved_chunks if c.chunk_id in pilot_gt_chunk_ids]
            
            # If no pilot hits were in the 2.1M DB top-50, fallback to full retrieved chunks for confidence/jurisdiction metrics
            eval_chunks = pilot_filtered_chunks if pilot_filtered_chunks else retrieved_chunks

            judgments = gt_by_query.get(q.query_id, [])
            q_metrics = compute_query_metrics(q, eval_chunks, judgments, k_values=[5, 8, 10, 20])
            query_metrics_list.append(q_metrics)

        agg = compute_aggregate_metrics(query_metrics_list)
        agg["latency_p95_ms"] = float(np.percentile(latencies_ms, 95))
        agg["adapter_name"] = name
        audit_results[name] = agg

    # Save audited JSON
    out_json = OUTPUT_DIR / "phase_2_5_quality_audit_metrics.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)

    # Display Audit Summary Table
    summary_rows = []
    for name, res in audit_results.items():
        summary_rows.append({
            "Adapter": name,
            "Recall@5": f"{res.get('Recall@5_strict', 0.0):.4f}",
            "Recall@10": f"{res.get('Recall@10_strict', 0.0):.4f}",
            "Recall@20": f"{res.get('Recall@20_strict', 0.0):.4f}",
            "Precision@5": f"{res.get('Precision@5_strict', 0.0):.4f}",
            "MRR": f"{res.get('MRR_strict', 0.0):.4f}",
            "NDCG@10": f"{res.get('NDCG@10', 0.0):.4f}",
            "False Conf Rate": f"{res.get('false_confidence_rate', 0.0)*100:.1f}%",
            "Latency P95 (ms)": f"{res.get('latency_p95_ms', 0.0):.1f}"
        })

    df_summary = pd.DataFrame(summary_rows)
    print("\n==================================================")
    print("PHASE 2.5 AUDITED RETRIEVAL QUALITY METRICS")
    print("==================================================")
    print(df_summary.to_string(index=False))
    print("==================================================")
    print(f"Saved audit metrics to {out_json}")


if __name__ == "__main__":
    audit_phase_2_5_quality()
