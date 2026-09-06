# scripts/check_indexes.py
import sys
sys.path.append("d:/Abishek")
from src.db_phase2 import get_connection

conn = get_connection(autocommit=True)
cur = conn.cursor()
cur.execute("SELECT tablename, indexname, indexdef FROM pg_indexes WHERE tablename IN ('embeddings', 'chunks', 'source_documents');")
rows = cur.fetchall()
print("Indexes on PostgreSQL tables:")
for r in rows:
    print(f"  - Table: {r[0]} | Index: {r[1]}")
    print(f"    Def: {r[2]}")

cur.execute("SELECT pg_size_pretty(pg_total_relation_size('embeddings')), pg_size_pretty(pg_relation_size('embeddings')), pg_size_pretty(pg_indexes_size('embeddings'));")
size_row = cur.fetchone()
print(f"\nEmbeddings Table Total Size: {size_row[0]} | Heap Size: {size_row[1]} | Index Size: {size_row[2]}")
conn.close()
