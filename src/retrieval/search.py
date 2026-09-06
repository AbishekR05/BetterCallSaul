# src/retrieval/search.py
"""
pgvector Cosine Search Module for Phase 2.3.
Executes vector similarity search using <=> cosine distance operator matching HNSW index.
Includes dynamic ef_search configuration, statement timeout, and full metadata join.
"""

import time
from typing import Tuple, List, Dict, Any, Optional
import numpy as np
import psycopg
from src.retrieval.config import RetrievalFilters
from src.retrieval.filters import build_sql_where_clause


def execute_vector_search(
    conn: psycopg.Connection,
    query_vector: np.ndarray,
    candidate_k: int = 30,
    ef_search: int = 64,
    filters: Optional[RetrievalFilters] = None,
    db_timeout_seconds: float = 10.0
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Executes HNSW cosine distance search on embeddings joined with chunks and source_documents.
    
    Returns:
      (raw_candidate_rows, db_search_latency_ms)
    """
    start_t = time.time()
    vec_str = "[" + ",".join(map(str, query_vector.tolist())) + "]"
    
    where_sql, filter_params = build_sql_where_clause(filters)
    
    # Statement timeout in milliseconds
    timeout_ms = int(db_timeout_seconds * 1000)
    
    with conn.cursor() as cur:
        # 1. Set query-time HNSW ef_search and statement_timeout
        cur.execute(f"SET LOCAL hnsw.ef_search = {ef_search};")
        cur.execute(f"SET LOCAL statement_timeout = {timeout_ms};")
        
        # 2. Build full search query
        # pgvector <=> operator computes cosine distance.
        # Cosine Similarity = 1 - Cosine Distance.
        query_sql = f"""
            SELECT 
                c.chunk_id,
                c.document_id,
                c.parent_id,
                c.chunk_index,
                c.source_type,
                c.part,
                c.chapter,
                c.section,
                c.subsection,
                c.clause,
                c.paragraph_number,
                c.text,
                c.char_length,
                c.cross_references,
                d.title,
                d.act,
                d.case_name,
                d.citation,
                d.court,
                d.jurisdiction,
                d.level,
                d.state,
                d.date,
                d.effective_date,
                d.is_historical,
                d.source_url,
                d.original_source_id,
                d.dataset_version,
                (1.0 - (e.embedding <=> %s::vector)) AS similarity_score
            FROM embeddings e
            JOIN chunks c ON e.chunk_id = c.chunk_id
            JOIN source_documents d ON c.document_id = d.document_id
            {where_sql}
            ORDER BY e.embedding <=> %s::vector ASC
            LIMIT %s;
        """
        
        # Combine parameters: vec_str for similarity, filter_params, vec_str for ORDER BY, candidate_k for LIMIT
        all_params = [vec_str] + filter_params + [vec_str, candidate_k]
        
        cur.execute(query_sql, all_params)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
    db_latency_ms = (time.time() - start_t) * 1000.0
    
    # Format rows into dictionary records
    results = []
    for r in rows:
        row_dict = dict(zip(columns, r))
        # Ensure similarity score is float
        row_dict["similarity_score"] = float(row_dict.get("similarity_score", 0.0))
        results.append(row_dict)
        
    return results, db_latency_ms
