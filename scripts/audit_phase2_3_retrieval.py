# scripts/audit_phase2_3_retrieval.py
"""
Phase 2.3 Comprehensive Retrieval Evaluation & Metric Inconsistency Audit.
Investigates metric divergence between Phase 2.1 offline benchmark and Phase 2.3 live pipeline.
"""

import os
import sys
import json
import time
import functools
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Set
from dotenv import load_dotenv

# Force unbuffered printing
print = functools.partial(print, flush=True)

sys.path.append("d:/Abishek")

from src.db_phase2 import get_connection
from src.retrieval.config import RetrievalConfig
from src.retrieval.retriever import LegalRetriever
from src.retrieval.embedding import QueryEmbedder
from src.retrieval.search import execute_vector_search

load_dotenv()

BENCHMARK_DIR_2_1 = Path("d:/Abishek/benchmark/phase_2_1")
BENCHMARK_DIR_2_3 = Path("d:/Abishek/benchmark/phase_2_3")

EVAL_QUERIES_PATH = BENCHMARK_DIR_2_1 / "eval_queries.jsonl"
RELEVANCE_PATH = BENCHMARK_DIR_2_1 / "relevance_judgments.jsonl"
SAMPLED_CHUNKS_PATH = BENCHMARK_DIR_2_1 / "sampled_chunks.parquet"


def load_dataset():
    queries = []
    with open(EVAL_QUERIES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(json.loads(line))

    judgments = {}
    with open(RELEVANCE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                judgments[item["query_id"]] = item.get("relevant_chunk_ids", [])

    sampled_df = pd.read_parquet(SAMPLED_CHUNKS_PATH)
    sampled_chunk_ids = set(sampled_df["chunk_id"].tolist())

    return queries, judgments, sampled_chunk_ids


def compute_metrics(retrieved_ids_list: List[List[str]], judgments: Dict[str, List[str]], query_ids: List[str], k_values=[5, 8, 10]):
    metrics = {f"Recall@{k}": [] for k in k_values}
    metrics.update({f"Precision@{k}": [] for k in k_values})
    metrics["MRR"] = []
    
    per_query_results = []

    for qid, ret_ids in zip(query_ids, retrieved_ids_list):
        rel_set = set(judgments.get(qid, []))
        if not rel_set:
            continue

        q_recall = {}
        q_precision = {}
        q_mrr = 0.0

        for rank_idx, cid in enumerate(ret_ids, 1):
            if cid in rel_set:
                q_mrr = 1.0 / rank_idx
                break

        for k in k_values:
            top_k_ids = set(ret_ids[:k])
            hits = len(top_k_ids.intersection(rel_set))
            rec = hits / len(rel_set)
            prec = hits / k
            q_recall[k] = rec
            q_precision[k] = prec
            metrics[f"Recall@{k}"].append(rec)
            metrics[f"Precision@{k}"].append(prec)

        metrics["MRR"].append(q_mrr)

        per_query_results.append({
            "query_id": qid,
            "rel_chunk_ids": list(rel_set),
            "retrieved_chunk_ids": ret_ids,
            "mrr": q_mrr,
            "recall_5": q_recall[5],
            "recall_8": q_recall[8],
            "recall_10": q_recall[10],
            "precision_5": q_precision[5],
            "precision_8": q_precision[8],
            "precision_10": q_precision[10]
        })

    summary = {m: float(np.mean(vals)) if vals else 0.0 for m, vals in metrics.items()}
    return summary, per_query_results


def run_audit():
    print("=" * 60)
    print("PHASE 2.3 RETRIEVAL EVALUATION & QUALITY METRICS AUDIT")
    print("=" * 60)

    queries, judgments, sampled_chunk_ids = load_dataset()
    print(f"[1] Loaded {len(queries)} eval queries, {len(judgments)} relevance sets.")
    print(f"    Sampled chunks baseline size: {len(sampled_chunk_ids)}")

    # Check Database Status
    conn = get_connection(autocommit=False)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM chunks;")
        db_chunk_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM source_documents;")
        db_doc_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM embeddings;")
        db_emb_count = cur.fetchone()[0]

        # Check how many of the 1000 sampled chunk IDs exist in DB
        sampled_list = list(sampled_chunk_ids)
        cur.execute("SELECT COUNT(*) FROM chunks WHERE chunk_id = ANY(%s);", (sampled_list,))
        sampled_in_db_count = cur.fetchone()[0]

    conn.close()

    print(f"[2] Database Status:")
    print(f"    - Total Chunks in DB       : {db_chunk_count:,}")
    print(f"    - Total Documents in DB    : {db_doc_count:,}")
    print(f"    - Total Embeddings in DB   : {db_emb_count:,}")
    print(f"    - Sampled Chunks Present   : {sampled_in_db_count} / {len(sampled_chunk_ids)}")

    # Check ground-truth chunk presence in DB
    all_gt_ids = set()
    for qid, cids in judgments.items():
        all_gt_ids.update(cids)
    print(f"    - Total Ground Truth Chunks : {len(all_gt_ids)}")

    conn = get_connection(autocommit=False)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM chunks WHERE chunk_id = ANY(%s);", (list(all_gt_ids),))
        gt_in_db_count = cur.fetchone()[0]
    conn.close()
    print(f"    - Ground Truth Chunks in DB : {gt_in_db_count} / {len(all_gt_ids)}")

    # Initialize Retriever
    print("\n[3] Initializing LegalRetriever (BGE-base FP16 on GPU)...")
    cfg = RetrievalConfig(use_gpu=True, final_k=10, candidate_k=50, high_confidence_threshold=0.55, low_confidence_threshold=0.40, ef_search=64)
    retriever = LegalRetriever(config=cfg)

    # Warmup query
    retriever.retrieve("What are the grounds for divorce under Hindu Marriage Act?")

    query_ids = [q["query_id"] for q in queries]

    # --- EXPERIMENT A: Live Retriever Full DB (Default Pipeline, K=10) ---
    print("\n--- Running Experiment A: Live Retriever against Full DB (Default Postprocessing) ---")
    ret_ids_exp_a = []
    latencies_a = []
    db_latencies_a = []
    embed_latencies_a = []

    for q in queries:
        res = retriever.retrieve(q["query_text"])
        latencies_a.append(res.timing.total_latency_ms)
        db_latencies_a.append(res.timing.db_search_latency_ms)
        embed_latencies_a.append(res.timing.embedding_latency_ms)
        ret_ids_exp_a.append([item.chunk_id for item in res.results])

    metrics_a, per_q_a = compute_metrics(ret_ids_exp_a, judgments, query_ids)

    print("Experiment A Metrics (Live Full DB, Default Pipeline):")
    for k, v in metrics_a.items():
        print(f"  {k:15s}: {v:.4f}")
    print(f"  Avg Total Latency: {np.mean(latencies_a):.2f} ms (Embed: {np.mean(embed_latencies_a):.2f} ms | DB: {np.mean(db_latencies_a):.2f} ms)")

    # --- EXPERIMENT B: Raw HNSW Vector Search against Full DB (No low_confidence filter, Top 10) ---
    print("\n--- Running Experiment B: Raw Vector Search against Full DB (No thresholding/dedup cutoff) ---")
    ret_ids_exp_b = []
    conn = get_connection(autocommit=False)
    embedder = retriever.embedder
    try:
        for q in queries:
            vec = embedder.embed_query(q["query_text"])
            raw_rows, _ = execute_vector_search(conn=conn, query_vector=vec, candidate_k=10, ef_search=64, filters=None)
            ret_ids_exp_b.append([r["chunk_id"] for r in raw_rows])
    finally:
        conn.close()

    metrics_b, per_q_b = compute_metrics(ret_ids_exp_b, judgments, query_ids)
    print("Experiment B Metrics (Live Full DB, Raw Top-10 Vector Search):")
    for k, v in metrics_b.items():
        print(f"  {k:15s}: {v:.4f}")

    # --- EXPERIMENT C: Isolated 1,000 Sampled Pilot Chunks Retrieval (Same condition as Phase 2.1) ---
    print("\n--- Running Experiment C: Isolated Search restricted to 1,000 Sampled Pilot Chunks ---")
    ret_ids_exp_c = []
    conn = get_connection(autocommit=False)
    sampled_id_list = list(sampled_chunk_ids)
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL hnsw.ef_search = 64;")
            for q in queries:
                vec = embedder.embed_query(q["query_text"])
                vec_str = "[" + ",".join(map(str, vec.tolist())) + "]"
                cur.execute("""
                    SELECT c.chunk_id, (1.0 - (e.embedding <=> %s::vector)) AS sim
                    FROM embeddings e
                    JOIN chunks c ON e.chunk_id = c.chunk_id
                    WHERE c.chunk_id = ANY(%s)
                    ORDER BY e.embedding <=> %s::vector ASC
                    LIMIT 10;
                """, (vec_str, sampled_id_list, vec_str))
                rows = cur.fetchall()
                ret_ids_exp_c.append([r[0] for r in rows])
    finally:
        conn.close()

    metrics_c, per_q_c = compute_metrics(ret_ids_exp_c, judgments, query_ids)
    print("Experiment C Metrics (Isolated 1,000 Sample Chunks):")
    for k, v in metrics_c.items():
        print(f"  {k:15s}: {v:.4f}")

    # Output detailed comparative breakdown and save JSON
    audit_data = {
        "db_chunk_count": db_chunk_count,
        "sampled_chunk_count": len(sampled_chunk_ids),
        "sampled_in_db": sampled_in_db_count,
        "metrics_exp_a_live_pipeline": metrics_a,
        "metrics_exp_b_raw_vec_search": metrics_b,
        "metrics_exp_c_isolated_pilot": metrics_c,
        "latency_stats": {
            "mean_total_ms": float(np.mean(latencies_a)),
            "mean_embed_ms": float(np.mean(embed_latencies_a)),
            "mean_db_ms": float(np.mean(db_latencies_a)),
            "p95_total_ms": float(np.percentile(latencies_a, 95)),
            "min_total_ms": float(np.min(latencies_a)),
            "max_total_ms": float(np.max(latencies_a))
        },
        "per_query_live_pipeline": per_q_a,
        "per_query_isolated": per_q_c
    }

    out_file = BENCHMARK_DIR_2_3 / "audit_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    print(f"\nAudit completed. Full JSON results saved to {out_file}")


if __name__ == "__main__":
    run_audit()
