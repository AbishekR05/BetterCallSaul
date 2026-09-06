import sys
sys.path.append("d:/Abishek")
from src.db_phase2 import get_connection
from scripts.manifest_manager import load_manifest
import shutil

conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM embeddings;")
emb_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM chunks;")
chunk_count = cur.fetchone()[0]
conn.close()

manifest = load_manifest()
batches = manifest.get("batches", {})
loaded_batches = [b for b, v in batches.items() if v.get("status") == "loaded"]
pending_batches = [b for b, v in batches.items() if v.get("status") != "loaded"]

total_chunks_manifest = sum(v.get("num_chunks", 0) for b, v in batches.items() if v.get("status") == "loaded")

_, _, free_disk_bytes = shutil.disk_usage("d:/")
free_disk_gb = free_disk_bytes / (1024 ** 3)

print("==================================================")
print("LIVE PRODUCTION INDEXING PROGRESS STATUS")
print("==================================================")
print(f"  PostgreSQL Embeddings Count : {emb_count:,}")
print(f"  PostgreSQL Chunks Count     : {chunk_count:,}")
print(f"  Completed Batches           : {len(loaded_batches)} / {len(batches)}")
print(f"  Remaining Batches           : {len(pending_batches)}")
print(f"  Total Chunks in Manifest    : {total_chunks_manifest:,}")
print(f"  D: Drive Free Space         : {free_disk_gb:.2f} GB")
print("==================================================")
