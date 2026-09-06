import sys
sys.path.append("d:/Abishek")
import json
from pathlib import Path
from src.db_phase2 import get_connection

AUDITED_GT_PATH = Path("d:/Abishek/benchmark/phase_2_4/ground_truth_v1_audited.jsonl")

gt_chunk_ids = set()
gt_doc_ids = set()

with open(AUDITED_GT_PATH, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            item = json.loads(line)
            if "chunk_id" in item: gt_chunk_ids.add(item["chunk_id"])
            if "document_id" in item: gt_doc_ids.add(item["document_id"])

print(f"Audited Ground Truth unique chunk_ids: {len(gt_chunk_ids):,}")
print(f"Audited Ground Truth unique document_ids: {len(gt_doc_ids):,}")

conn = get_connection()
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM chunks WHERE chunk_id = ANY(%s);", (list(gt_chunk_ids),))
matching_chunks = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM source_documents WHERE document_id = ANY(%s);", (list(gt_doc_ids),))
matching_docs = cur.fetchone()[0]

conn.close()

print(f"Matching chunk_ids present in active 1.1M DB: {matching_chunks:,} / {len(gt_chunk_ids):,}")
print(f"Matching document_ids present in active 1.1M DB: {matching_docs:,} / {len(gt_doc_ids):,}")
