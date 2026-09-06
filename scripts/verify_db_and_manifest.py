# scripts/verify_db_and_manifest.py
import sys
sys.path.append("d:/Abishek")
import json
import shutil
import psycopg
from pathlib import Path
from src.db_phase2 import get_connection

print("==================================================")
print("PHASE 2.2 PRODUCTION INDEXING AUDIT & PRE-OPTIMIZATION CHECK")
print("==================================================")

# 1. Inspect PostgreSQL Schema & Indexes
conn = get_connection(autocommit=True)
cur = conn.cursor()

cur.execute("""
    SELECT tablename, indexname, indexdef 
    FROM pg_indexes 
    WHERE tablename IN ('embeddings', 'chunks', 'source_documents');
""")
indexes = cur.fetchall()
print("\n[1] Active PostgreSQL Indexes:")
for r in indexes:
    print(f"  - Table: {r[0]:18s} | Index: {r[1]:22s}")
    print(f"    Definition: {r[2]}")

# 2. Inspect Row Counts & Table Sizes
cur.execute("SELECT COUNT(*) FROM source_documents;")
doc_count = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM chunks;")
chunk_count = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM embeddings;")
emb_count = cur.fetchone()[0]

cur.execute("""
    SELECT 
        pg_size_pretty(pg_total_relation_size('embeddings')) AS emb_total,
        pg_size_pretty(pg_relation_size('embeddings')) AS emb_heap,
        pg_size_pretty(pg_indexes_size('embeddings')) AS emb_idx,
        pg_size_pretty(pg_total_relation_size('chunks')) AS chunks_total,
        pg_size_pretty(pg_tablespace_size('bcs_tablespace')) AS bcs_ts_size;
""")
sizes = cur.fetchone()

print(f"\n[2] Current Database Scale & Storage Usage:")
print(f"  - Loaded Source Documents : {doc_count:,}")
print(f"  - Loaded Chunks           : {chunk_count:,}")
print(f"  - Loaded Embeddings       : {emb_count:,}")
print(f"  - Embeddings Heap Size    : {sizes[1]}")
print(f"  - Embeddings Index Size   : {sizes[2]} (HNSW index footprint)")
print(f"  - Embeddings Total Size   : {sizes[0]}")
print(f"  - Chunks Table Total Size : {sizes[3]}")
print(f"  - bcs_tablespace (D:) Size: {sizes[4]}")

# 3. Inspect D: Drive Available Storage Space
total, used, free = shutil.disk_usage("d:/")
print(f"\n[3] D: Drive Disk Space:")
print(f"  - Total Size : {total / (1024**3):.2f} GB")
print(f"  - Used Space : {used / (1024**3):.2f} GB")
print(f"  - Free Space : {free / (1024**3):.2f} GB")

# Projected storage for 15.7M chunks
# 15.7M chunks * 768 float32 dims * 4 bytes = ~48.2 GB raw heap vectors
# HNSW index footprint for 15.7M vectors (m=16) = ~35 - 45 GB
# Total projected pgvector storage = ~85 - 100 GB
print(f"\n[4] Projected Full Corpus (15.7M Chunks) Storage Requirements:")
print(f"  - Projected Raw Embeddings Heap : ~48 GB")
print(f"  - Projected Chunks & Docs Tables: ~15 GB")
print(f"  - Projected Final HNSW Index    : ~40 GB")
print(f"  - Total Projected bcs_tablespace: ~103 GB")
print(f"  - Storage Safety Margin         : {free / (1024**3) - 103:.2f} GB available headroom on D: drive (SAFE)")

# 5. Inspect Manifest Checkpoint State
manifest_path = Path("d:/Abishek/benchmark/phase_2_2/manifest_phase2_2.json")
if manifest_path.exists():
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    loaded_batches = [b for b, data in manifest.get("batches", {}).items() if data.get("status") == "loaded"]
    in_progress = [b for b, data in manifest.get("batches", {}).items() if data.get("status") in ("embedding", "failed")]
    print(f"\n[5] Manifest Checkpoint Status:")
    print(f"  - Total Batches Tracked : {len(manifest.get('batches', {}))}")
    print(f"  - Successfully Loaded   : {len(loaded_batches)} batches")
    print(f"  - Transient/In-Progress : {len(in_progress)} batches")

conn.close()
