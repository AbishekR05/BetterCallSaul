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
pilot_chunk_ids = set()
with open(AUDITED_GT_PATH, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            rj = RelevanceJudgment(**json.loads(line))
            pilot_chunk_ids.add(rj.chunk_id)
            if rj.query_id not in gt_by_query:
                gt_by_query[rj.query_id] = []
            gt_by_query[rj.query_id].append(rj)

print(f"Loaded {len(queries)} queries and {len(pilot_chunk_ids):,} pilot ground-truth chunk IDs.")

adapters = {
    "Baseline (Dense)": BaselineAdapter(),
    "Hybrid (RRF)": HybridAdapter(fusion_method="rrf"),
    "Hybrid + Reranker": RerankedAdapter(),
    "Final Combined": JurisdictionBoostedAdapter()
}

for name, adapter in adapters.items():
    query_metrics = []
    for q in queries:
        retrieved = adapter.retrieve(q.query_text, top_k=20)
        # Filter retrieved to pilot ground-truth candidate space to measure relative ranking/recall improvement
        pilot_retrieved = [r for r in retrieved if r.chunk_id in pilot_chunk_ids]
        judgments = gt_by_query.get(q.query_id, [])
        m = compute_query_metrics(q, pilot_retrieved, judgments)
        query_metrics.append(m)

    agg = compute_aggregate_metrics(query_metrics)
    print(f"\n--- {name} ---")
    print(f"Recall@5 (Strict)  : {agg.get('Recall@5_strict', 0.0):.4f}")
    print(f"Recall@10 (Strict) : {agg.get('Recall@10_strict', 0.0):.4f}")
    print(f"MRR (Strict)       : {agg.get('MRR_strict', 0.0):.4f}")
    print(f"NDCG@10 (Graded)   : {agg.get('NDCG@10', 0.0):.4f}")
