import sys
sys.path.append("d:/Abishek")
from src.db_phase2 import get_connection

conn = get_connection()
cur = conn.cursor()

chunk_id = "cdcfb9a153096a362f65dee72bc7ea6e"
cur.execute("SELECT c.chunk_id, c.document_id, c.text, e.chunk_id FROM chunks c LEFT JOIN embeddings e ON c.chunk_id = e.chunk_id WHERE c.chunk_id = %s;", (chunk_id,))
row = cur.fetchone()

if row:
    print(f"Chunk ID: {row[0]}")
    print(f"Document ID: {row[1]}")
    print(f"Text Snippet: {row[2][:100]}...")
    print(f"Has Embedding in DB: {row[3] is not None}")
else:
    print(f"Chunk ID '{chunk_id}' NOT FOUND in chunks table!")

conn.close()
