import sys
sys.path.append("d:/Abishek")
import pandas as pd
from src.db_phase2 import get_connection

df = pd.read_parquet("d:/Abishek/benchmark/phase_2_2/sample_50k.parquet")
chunk_ids = df['chunk_id'].tolist()
doc_ids = df['document_id'].dropna().unique().tolist()

print(f"Loaded {len(chunk_ids):,} chunk IDs from sample_50k.parquet")

conn = get_connection(autocommit=False)
cur = conn.cursor()

# Delete embeddings
cur.execute("DELETE FROM embeddings WHERE chunk_id = ANY(%s);", (chunk_ids,))
del_emb = cur.rowcount
print(f"Deleted {del_emb:,} benchmark embeddings.")

# Delete chunks
cur.execute("DELETE FROM chunks WHERE chunk_id = ANY(%s);", (chunk_ids,))
del_chunks = cur.rowcount
print(f"Deleted {del_chunks:,} benchmark chunks.")

conn.commit()

cur.execute("SELECT COUNT(*) FROM embeddings;")
cnt = cur.fetchone()[0]
print(f"Database clean. Current total embeddings count: {cnt:,}")
conn.close()
