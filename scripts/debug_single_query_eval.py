import sys
sys.path.append("d:/Abishek")
import json
from pathlib import Path
from eval.schemas import EvalQuery, RelevanceJudgment
from src.retrieval.adapters import BaselineAdapter

QUERIES_PATH = Path("d:/Abishek/eval/queries/p24_queries_v1.jsonl")
AUDITED_GT_PATH = Path("d:/Abishek/benchmark/phase_2_4/ground_truth_v1_audited.jsonl")

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

adapter = BaselineAdapter()
print(f"Testing first 5 queries...")

for q in queries[:5]:
    retrieved = adapter.retrieve(q.query_text, top_k=10)
    retrieved_cids = [r.chunk_id for r in retrieved]
    gt_judgments = gt_by_query.get(q.query_id, [])
    gt_cids = [j.chunk_id for j in gt_judgments if j.relevance_grade >= 3.0]
    overlap = set(retrieved_cids).intersection(set(gt_cids))
    print(f"\nQuery ID: '{q.query_id}' | Text: '{q.query_text[:50]}...'")
    print(f"  Retrieved Chunk IDs ({len(retrieved_cids)}): {retrieved_cids[:3]}")
    print(f"  GT Chunk IDs ({len(gt_cids)}): {gt_cids[:3]}")
    print(f"  Overlap count: {len(overlap)}")
