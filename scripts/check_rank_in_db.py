import sys
sys.path.append("d:/Abishek")
from src.retrieval.embedding import QueryEmbedder
from src.db_phase2 import get_connection

embedder = QueryEmbedder()
q_vec = embedder.embed_query("Can I return a defective electronic product bought online?")

conn = get_connection()
cur = conn.cursor()

# Rank of cdcfb9a153096a362f65dee72bc7ea6e
cur.execute("""
    WITH ranked AS (
        SELECT chunk_id, embedding <=> %s::vector AS distance,
               ROW_NUMBER() OVER (ORDER BY embedding <=> %s::vector ASC) AS rank
        FROM embeddings
    )
    SELECT rank, distance FROM ranked WHERE chunk_id = 'cdcfb9a153096a362f65dee72bc7ea6e';
""", (str(q_vec), str(q_vec)))
row = cur.fetchone()

if row:
    print(f"Rank in 1.1M DB: {row[0]:,} | Distance: {row[1]:.4f}")

conn.close()
