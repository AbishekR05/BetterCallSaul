# scripts/run_audited_open_world_eval.py
"""
Runs Open-World Evaluation using authentic, non-circular ground truth (ground_truth_v1_audited.jsonl).
Measures true Recall@K, Precision@K, MRR, NDCG@10, and Legal-specific metrics.
"""

import sys
sys.path.append("d:/Abishek")

import json
from pathlib import Path
from eval.harness import run_open_world, BaselineRetrieverAdapter, get_corpus_snapshot
from eval.schemas import EvalQuery, RelevanceJudgment
from eval.metrics import compute_query_metrics, compute_aggregate_metrics

QUERIES_PATH = Path("d:/Abishek/eval/queries/p24_queries_v1.jsonl")
AUDITED_GT_PATH = Path("d:/Abishek/benchmark/phase_2_4/ground_truth_v1_audited.jsonl")


def run_audited_eval():
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

    adapter = BaselineRetrieverAdapter()
    query_metrics_list = []

    for q in queries:
        retrieved_chunks = adapter.retrieve(q.query_text, top_k=20)
        judgments = gt_by_query.get(q.query_id, [])
        q_metrics = compute_query_metrics(q, retrieved_chunks, judgments, k_values=[5, 8, 10, 20])
        query_metrics_list.append(q_metrics)

    agg = compute_aggregate_metrics(query_metrics_list)
    corpus_snap = get_corpus_snapshot()

    print("==================================================")
    print("ACTUAL NON-CIRCULAR OPEN-WORLD RETRIEVAL METRICS")
    print("==================================================")
    print(f"Corpus Chunks Snapshot          : {corpus_snap.chunks_row_count:,}")
    print(f"Recall@5 (Strict)               : {agg.get('Recall@5_strict', 0.0):.4f}")
    print(f"Recall@8 (Strict)               : {agg.get('Recall@8_strict', 0.0):.4f}")
    print(f"Recall@10 (Strict)              : {agg.get('Recall@10_strict', 0.0):.4f}")
    print(f"Recall@20 (Strict)              : {agg.get('Recall@20_strict', 0.0):.4f}")
    print(f"Precision@5 (Strict)            : {agg.get('Precision@5_strict', 0.0):.4f}")
    print(f"Precision@10 (Strict)           : {agg.get('Precision@10_strict', 0.0):.4f}")
    print(f"MRR (Strict)                    : {agg.get('MRR_strict', 0.0):.4f}")
    print(f"NDCG@10 (Graded)                : {agg.get('NDCG@10', 0.0):.4f}")
    print(f"Success@5                       : {agg.get('Success@5_strict', 0.0):.4f}")
    print(f"Success@10                      : {agg.get('Success@10_strict', 0.0):.4f}")
    print(f"Success@20                      : {agg.get('Success@20_strict', 0.0):.4f}")
    print(f"Jurisdiction Correctness Rate   : {agg.get('jurisdiction_correctness_rate', 0.0)*100:.1f}%")
    print(f"False Confidence Rate (Out-Scope): {agg.get('false_confidence_rate', 0.0)*100:.1f}%")
    print("==================================================")

    out_file = Path("d:/Abishek/benchmark/phase_2_4/actual_open_world_metrics.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(agg, f, indent=2)

    return agg


if __name__ == "__main__":
    run_audited_eval()
