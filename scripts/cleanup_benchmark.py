import sys
sys.path.append("d:/Abishek")
from src.db_phase2 import get_connection

conn = get_connection(autocommit=False)
cur = conn.cursor()

print("Cleaning up benchmark test rows...")
cur.execute("DELETE FROM embeddings WHERE chunk_id LIKE 'bench_chunk_%';")
cur.execute("DELETE FROM chunks WHERE chunk_id LIKE 'bench_chunk_%';")
cur.execute("DELETE FROM source_documents WHERE document_id LIKE 'bench_doc_%';")
conn.commit()

cur.execute("SELECT COUNT(*) FROM embeddings;")
cnt = cur.fetchone()[0]
print(f"Cleanup complete. Total embeddings in PostgreSQL: {cnt:,}")
conn.close()
