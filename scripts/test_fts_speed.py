import sys
sys.path.append("d:/Abishek")
import time
from src.db_phase2 import get_connection

conn = get_connection()
cur = conn.cursor()

query_text = "Kerala Police Act Section 31"
keywords = [w for w in query_text.split() if len(w) > 2]

t0 = time.time()
like_clauses = " OR ".join(["text ILIKE %s" for _ in keywords])
params = [f"%{kw}%" for kw in keywords]
cur.execute(f"SELECT chunk_id, document_id, text FROM chunks WHERE {like_clauses} LIMIT 50;", params)
rows = cur.fetchall()
t_ilike = time.time() - t0
print(f"ILIKE found {len(rows)} rows in {t_ilike:.3f} seconds.")

conn.close()
