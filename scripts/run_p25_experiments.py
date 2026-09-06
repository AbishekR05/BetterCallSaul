# scripts/run_p25_experiments.py
"""
Phase 2.5 Retrieval Optimization Experiment Suite Executor.
Runs Experiments 1 through 5 against Phase 2.4 evaluation harness and audited ground truth.
Outputs comparative metrics tables and saves full telemetry reports to benchmark/phase_2_5/.
"""

import sys
import functools
print = functools.partial(print, flush=True)

sys.path.append("d:/Abishek")


import json
import time
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List

from eval.harness import get_corpus_snapshot
from eval.schemas import EvalQuery, RelevanceJudgment
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
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_queries_and_ground_truth():
    queries = []
    with open(QUERIES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(EvalQuery(**json.loads(line)))

    gt_by_query = {}
    with open(AUDITED_GT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rj = RelevanceJudgment(**json.loads(line))
                if rj.query_id not in gt_by_query:
                    gt_by_query[rj.query_id] = []
                gt_by_query[rj.query_id].append(rj)

    return queries, gt_by_query


def evaluate_adapter(adapter_name: str, adapter_instance: Any, queries: List[EvalQuery], gt_by_query: Dict[str, List[RelevanceJudgment]]) -> Dict[str, Any]:
    print(f"\nEvaluating Adapter: '{adapter_name}' across {len(queries)} queries...")
    query_metrics_list = []
    latencies_ms = []

    for idx, q in enumerate(queries, 1):
        if idx % 40 == 0 or idx == len(queries):
            print(f"  [{idx}/{len(queries)}] Processing query evaluations...")
            
        start_t = time.time()
        filters = {}
        if hasattr(q, 'jurisdiction_expectation') and q.jurisdiction_expectation:
            filters['expected_jurisdiction'] = q.jurisdiction_expectation

        retrieved_chunks = adapter_instance.retrieve(q.query_text, top_k=20, filters=filters)
        lat_ms = (time.time() - start_t) * 1000.0
        latencies_ms.append(lat_ms)

        judgments = gt_by_query.get(q.query_id, [])
        q_metrics = compute_query_metrics(q, retrieved_chunks, judgments, k_values=[5, 8, 10, 20])
        query_metrics_list.append(q_metrics)

    agg = compute_aggregate_metrics(query_metrics_list)
    agg["latency_mean_ms"] = float(np.mean(latencies_ms))
    agg["latency_p50_ms"] = float(np.percentile(latencies_ms, 50))
    agg["latency_p95_ms"] = float(np.percentile(latencies_ms, 95))
    agg["adapter_name"] = adapter_name
    return agg


def run_phase_2_5_suite():
    print("==================================================")
    print("STARTING PHASE 2.5 RETRIEVAL OPTIMIZATION EXPERIMENTS")
    print("==================================================")

    queries, gt_by_query = load_queries_and_ground_truth()
    snapshot = get_corpus_snapshot()
    print(f"Corpus Snapshot: {snapshot.chunks_row_count:,} chunks | {snapshot.embeddings_row_count:,} embeddings")

    experiment_results: Dict[str, Dict[str, Any]] = {}

    # Experiment 1: Hybrid vs Dense-Only
    print("\n--- Experiment 1: Hybrid (RRF & Weighted) vs. Baseline Dense-Only ---")
    experiment_results["Baseline (Dense)"] = evaluate_adapter("Baseline (Dense)", BaselineAdapter(), queries, gt_by_query)
    experiment_results["Hybrid (RRF)"] = evaluate_adapter("Hybrid (RRF)", HybridAdapter(fusion_method="rrf"), queries, gt_by_query)
    experiment_results["Hybrid (Weighted)"] = evaluate_adapter("Hybrid (Weighted)", HybridAdapter(fusion_method="weighted"), queries, gt_by_query)

    # Experiment 2: Reranking with BGE Cross-Encoder
    print("\n--- Experiment 2: BAAI/bge-reranker-base Cross-Encoder Reranking ---")
    experiment_results["Hybrid + Reranker"] = evaluate_adapter("Hybrid + Reranker", RerankedAdapter(), queries, gt_by_query)

    # Experiment 3: Confidence Calibration
    print("\n--- Experiment 3: Empirical Confidence Threshold Calibration ---")
    experiment_results["Calibrated Confidence"] = evaluate_adapter("Calibrated Confidence", CalibratedAdapter(), queries, gt_by_query)

    # Experiment 4 & 5: Jurisdiction Boosting & Final Combined
    print("\n--- Experiment 4 & 5: Jurisdiction Soft Boosting & Final Combined System ---")
    experiment_results["Final Combined (P2.5)"] = evaluate_adapter("Final Combined (P2.5)", JurisdictionBoostedAdapter(), queries, gt_by_query)

    # Save summary report
    out_json = OUTPUT_DIR / "phase_2_5_experiment_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(experiment_results, f, indent=2)

    # Compile Comparison Table
    summary_rows = []
    for name, res in experiment_results.items():
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
    print("PHASE 2.5 EXPERIMENT RESULTS COMPARISON SUMMARY")
    print("==================================================")
    print(df_summary.to_string(index=False))
    print("==================================================")
    print(f"Saved full experiment results to {out_json}")


if __name__ == "__main__":
    run_phase_2_5_suite()
