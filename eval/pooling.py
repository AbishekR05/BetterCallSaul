# eval/pooling.py
"""
TREC-Style Candidate Pooling Module for Phase 2.4 Evaluation Framework.
Constructs unbiased, multi-source candidate pools for evaluation queries using:
1. Frozen LegalRetriever top-K vector candidates.
2. Read-only keyword/entity search over chunks.text (ILIKE / tsvector).
"""

import re
import time
import psycopg
from typing import List, Dict, Any, Tuple, Set, Optional
from src.db_phase2 import get_connection
from src.retrieval.retriever import LegalRetriever
from eval.schemas import EvalQuery, ScoredChunk


def extract_keywords_and_entities(query_text: str) -> List[str]:
    """Extract key terms, act names, section numbers, and case numbers for keyword matching."""
    # Find numbers / sections
    sections = re.findall(r'\b(?:section|sec|article|art|act|rule|order)\s*\d+[a-z]*\b', query_text, re.IGNORECASE)
    # Find quotes or capitalized terms
    quoted = re.findall(r'"([^"]+)"', query_text)
    # Tokenize words longer than 4 chars
    words = [w for w in re.findall(r'\b[a-zA-Z]{4,}\b', query_text) if w.lower() not in {"what", "where", "which", "under", "court", "legal", "rules", "state"}]
    
    terms = list(set(sections + quoted + words[:4]))
    return [t.strip() for t in terms if t.strip()]


def execute_keyword_search(
    conn: psycopg.Connection,
    query_text: str,
    limit: int = 15,
    timeout_seconds: float = 5.0
) -> List[Dict[str, Any]]:
    """Executes read-only keyword search on chunks.text using ILIKE for named entities."""
    terms = extract_keywords_and_entities(query_text)
    if not terms:
        return []

    # Build ILIKE conditions for top terms
    where_clauses = []
    params = []
    for t in terms[:3]:
        where_clauses.append("c.text ILIKE %s")
        params.append(f"%{t}%")

    where_sql = " OR ".join(where_clauses)
    timeout_ms = int(timeout_seconds * 1000)

    query_sql = f"""
        SELECT c.chunk_id, c.document_id, c.text, d.title, d.jurisdiction, d.court
        FROM chunks c
        JOIN source_documents d ON c.document_id = d.document_id
        WHERE {where_sql}
        LIMIT %s;
    """
    params.append(limit)

    results = []
    with conn.cursor() as cur:
        cur.execute(f"SET LOCAL statement_timeout = {timeout_ms};")
        cur.execute(query_sql, params)
        rows = cur.fetchall()
        for r in rows:
            results.append({
                "chunk_id": str(r[0]),
                "document_id": str(r[1]),
                "text": str(r[2]),
                "title": str(r[3]),
                "jurisdiction": str(r[4]),
                "court": str(r[5]),
                "source": "keyword_search"
            })
    return results


def build_candidate_pool(
    retriever: LegalRetriever,
    query: EvalQuery,
    vector_top_k: int = 30,
    keyword_top_k: int = 15
) -> List[ScoredChunk]:
    """
    Builds a merged, deduplicated candidate pool for a single query using:
    - Vector search (LegalRetriever)
    - Keyword search (PostgreSQL ILIKE)
    """
    # 1. Vector Search
    vec_res = retriever.retrieve(query.query_text)
    vec_chunks = vec_res.results[:vector_top_k]

    pool: List[ScoredChunk] = []
    seen_ids: Set[str] = set()

    for item in vec_chunks:
        if item.chunk_id not in seen_ids:
            seen_ids.add(item.chunk_id)
            pool.append(ScoredChunk(
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                text=item.text,
                similarity_score=item.similarity_score,
                confidence_tier=item.confidence_tier,
                match_type="vector_retrieval",
                provenance=item.provenance.dict() if hasattr(item.provenance, 'dict') else {}
            ))

    # 2. Auxiliary Keyword Search
    conn = get_connection(autocommit=False)
    try:
        kw_rows = execute_keyword_search(conn, query.query_text, limit=keyword_top_k)
        for r in kw_rows:
            cid = r["chunk_id"]
            if cid not in seen_ids:
                seen_ids.add(cid)
                pool.append(ScoredChunk(
                    chunk_id=cid,
                    document_id=r["document_id"],
                    text=r["text"],
                    similarity_score=0.0,
                    confidence_tier="low",
                    match_type="keyword_auxiliary",
                    provenance={"title": r["title"], "jurisdiction": r["jurisdiction"], "court": r["court"]}
                ))
    except Exception as e:
        # Graceful fallback if keyword search fails
        pass
    finally:
        conn.close()

    return pool
