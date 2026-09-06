# scripts/deep_inspect_failed_queries.py
import sys
sys.path.append("d:/Abishek")
import json
import psycopg
from pathlib import Path
from src.db_phase2 import get_connection

audit_path = Path("d:/Abishek/benchmark/phase_2_3/audit_results.json")
with open(audit_path, "r", encoding="utf-8") as f:
    data = json.load(f)

queries_path = Path("d:/Abishek/benchmark/phase_2_1/eval_queries.jsonl")
queries = {}
with open(queries_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            item = json.loads(line)
            queries[item["query_id"]] = item

per_q_live = data["per_query_live_pipeline"]
per_q_iso = data["per_query_isolated"]

conn = get_connection(autocommit=False)

sample_qids = ["Q001", "Q002", "Q003", "Q005"]

with conn.cursor() as cur:
    for qid in sample_qids:
        q_item = queries[qid]
        live_res = next(q for q in per_q_live if q["query_id"] == qid)
        gt_id = live_res["rel_chunk_ids"][0]
        
        # Get ground truth text
        cur.execute("SELECT c.chunk_id, d.title, c.text FROM chunks c JOIN source_documents d ON c.document_id = d.document_id WHERE c.chunk_id = %s;", (gt_id,))
        gt_row = cur.fetchone()
        
        # Get top-3 retrieved in Live DB
        ret_ids = live_res["retrieved_chunk_ids"][:3]
        cur.execute("""
            SELECT c.chunk_id, d.title, c.text 
            FROM chunks c 
            JOIN source_documents d ON c.document_id = d.document_id 
            WHERE c.chunk_id = ANY(%s);
        """, (ret_ids,))
        ret_rows = cur.fetchall()
        
        print("=" * 70)
        print(f"Query ID: {qid} | Domain: {q_item['domain']}")
        print(f"Query Text: {q_item['query_text']}")
        print(f"Ground Truth Chunk [{gt_id}]:")
        if gt_row:
            print(f"  Title: {gt_row[1]}")
            print(f"  Snippet: {gt_row[2][:150]}...")
        else:
            print("  Not found")
            
        print(f"Top Live DB Retrieved Chunks:")
        for r in ret_rows:
            print(f"  - [{r[0]}] Title: {r[1]}")
            print(f"    Snippet: {r[2][:150]}...")

conn.close()
