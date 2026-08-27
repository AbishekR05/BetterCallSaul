# src/retrieval.py
import json
from src.db import get_db_connection
from src.ingestion import embedding_model

def vector_search(query_text, limit=5):
    """Perform vector similarity search using pgvector cosine distance."""
    # Generate query embedding
    query_embedding = embedding_model.encode(query_text).tolist()
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Cosine distance in pgvector is <=>
    # Cosine similarity is 1 - distance
    cur.execute("""
        SELECT c.id, c.content, c.page_number, c.metadata, 
               (1 - (c.embedding <=> %s::vector)) AS similarity,
               d.filename
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s;
    """, (query_embedding, query_embedding, limit))
    
    results = []
    for row in cur.fetchall():
        results.append({
            "id": row[0],
            "content": row[1],
            "page_number": row[2],
            "metadata": row[3] if isinstance(row[3], dict) else json.loads(row[3]),
            "score": float(row[4]),
            "source": row[5]
        })
        
    conn.close()
    return results

def keyword_search(query_text, limit=5):
    """Perform full-text keyword search using PostgreSQL tsvector."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # We clean/format query for plainto_tsquery
    cur.execute("""
        SELECT c.id, c.content, c.page_number, c.metadata, 
               ts_rank_cd(to_tsvector('english', c.content), query) AS rank_score,
               d.filename
        FROM chunks c
        JOIN documents d ON c.document_id = d.id,
        plainto_tsquery('english', %s) query
        WHERE to_tsvector('english', c.content) @@ query
        ORDER BY rank_score DESC
        LIMIT %s;
    """, (query_text, limit))
    
    results = []
    for row in cur.fetchall():
        results.append({
            "id": row[0],
            "content": row[1],
            "page_number": row[2],
            "metadata": row[3] if isinstance(row[3], dict) else json.loads(row[3]),
            "score": float(row[4]),
            "source": row[5]
        })
        
    conn.close()
    return results

def hybrid_retrieval(query_text, limit=5, rrf_k=60):
    """
    Perform hybrid search combining vector search and keyword search.
    Uses Reciprocal Rank Fusion (RRF) to merge and rank results.
    """
    # Get more candidates than limit to allow ranking fusion
    candidate_limit = limit * 3
    
    vector_results = vector_search(query_text, limit=candidate_limit)
    keyword_results = keyword_search(query_text, limit=candidate_limit)
    
    # Reciprocal Rank Fusion
    # RRF Score = Sum_over_runs (1 / (k + rank))
    rrf_scores = {}
    doc_map = {}
    
    # Rank 1-indexed
    for rank, doc in enumerate(vector_results, start=1):
        doc_id = doc["id"]
        doc_map[doc_id] = doc
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (rrf_k + rank))
        
    for rank, doc in enumerate(keyword_results, start=1):
        doc_id = doc["id"]
        doc_map[doc_id] = doc
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (rrf_k + rank))
        
    # Sort documents by RRF score descending
    sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
    
    fused_results = []
    for doc_id in sorted_doc_ids[:limit]:
        doc = doc_map[doc_id]
        # Include the RRF fusion score for transparency
        doc["rrf_score"] = rrf_scores[doc_id]
        fused_results.append(doc)
        
    # Fallback to pure vector search if keyword search returned absolutely nothing and RRF is empty
    if not fused_results and vector_results:
        return vector_results[:limit]
        
    return fused_results
