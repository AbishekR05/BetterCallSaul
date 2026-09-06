# src/retrieval/postprocessing.py
"""
Post-processing module for Phase 2.3 Legal Retrieval Pipeline.
Handles score thresholding, confidence tiering, deduplication,
parent/sibling context expansion, and insufficient evidence detection.
"""

import hashlib
from typing import List, Dict, Any, Tuple, Set
import psycopg
from src.retrieval.config import RetrievalConfig
from src.retrieval.schema import RetrievalResultItem
from src.retrieval.provenance import extract_provenance


def text_hash(text: str) -> str:
    """Utility to compute MD5 hash of text for near-dedup."""
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()


def process_candidate_results(
    conn: psycopg.Connection,
    raw_candidates: List[Dict[str, Any]],
    config: RetrievalConfig
) -> Tuple[List[RetrievalResultItem], bool, int]:
    """
    Processes raw pgvector candidate rows:
      1. Score thresholding & two-tier confidence assignment
      2. Deduplication (exact chunk_id + text hash within same document)
      3. Parent & Sibling Context Expansion (if enabled in config)
      4. Insufficient evidence detection
      
    Returns:
      (final_result_items, insufficient_evidence_flag, raw_candidate_count)
    """
    raw_candidate_count = len(raw_candidates)
    
    # 1. Score Thresholding & Confidence Tiering
    valid_candidates = []
    for row in raw_candidates:
        score = row.get("similarity_score", 0.0)
        if score < config.low_confidence_threshold:
            continue
            
        confidence_tier = "high" if score >= config.high_confidence_threshold else "low"
        row["confidence_tier"] = confidence_tier
        valid_candidates.append(row)
        
    # 2. Deduplication (Exact chunk_id + Text Hash within same doc)
    seen_chunk_ids: Set[str] = set()
    seen_doc_text_hashes: Set[Tuple[str, str]] = set()
    deduped_direct: List[Dict[str, Any]] = []
    
    for row in valid_candidates:
        cid = str(row["chunk_id"])
        doc_id = str(row["document_id"])
        thash = text_hash(str(row["text"]))
        
        if cid in seen_chunk_ids:
            continue
        if (doc_id, thash) in seen_doc_text_hashes:
            continue
            
        seen_chunk_ids.add(cid)
        seen_doc_text_hashes.add((doc_id, thash))
        deduped_direct.append(row)
        
        if len(deduped_direct) >= config.final_k:
            break
            
    # Check Insufficient Evidence
    insufficient_evidence = len(deduped_direct) < config.min_acceptable_results
    
    # Assemble direct RetrievalResultItem list
    direct_items: List[RetrievalResultItem] = []
    for row in deduped_direct:
        prov = extract_provenance(row)
        item = RetrievalResultItem(
            chunk_id=str(row["chunk_id"]),
            document_id=str(row["document_id"]),
            text=str(row["text"]),
            similarity_score=float(row["similarity_score"]),
            confidence_tier=row["confidence_tier"],
            match_type="direct",
            provenance=prov
        )
        direct_items.append(item)
        
    # 3. Context Expansion (Parent Section & Sibling Chunks)
    expansion_items: List[RetrievalResultItem] = []
    
    if (config.include_parent_context or config.include_sibling_context) and len(direct_items) > 0:
        with conn.cursor() as cur:
            for item in direct_items:
                doc_id = item.document_id
                cid = item.chunk_id
                parent_id = item.provenance.parent_id if hasattr(item.provenance, 'parent_id') else ""
                
                # Fetch Parent Context Chunk
                if config.include_parent_context and parent_id and parent_id != doc_id:
                    if parent_id not in seen_chunk_ids:
                        cur.execute("""
                            SELECT c.*, d.title, d.act, d.case_name, d.citation, d.court, 
                                   d.jurisdiction, d.level, d.state, d.date, d.effective_date, 
                                   d.is_historical, d.source_url, d.original_source_id, d.dataset_version
                            FROM chunks c
                            JOIN source_documents d ON c.document_id = d.document_id
                            WHERE c.chunk_id = %s;
                        """, (parent_id,))
                        parent_row = cur.fetchone()
                        if parent_row:
                            cols = [desc[0] for desc in cur.description]
                            p_dict = dict(zip(cols, parent_row))
                            p_dict["similarity_score"] = item.similarity_score
                            p_prov = extract_provenance(p_dict)
                            p_item = RetrievalResultItem(
                                chunk_id=str(p_dict["chunk_id"]),
                                document_id=str(p_dict["document_id"]),
                                text=str(p_dict["text"]),
                                similarity_score=item.similarity_score,
                                confidence_tier=item.confidence_tier,
                                match_type="parent_context",
                                provenance=p_prov
                            )
                            expansion_items.append(p_item)
                            seen_chunk_ids.add(parent_id)

    final_items = direct_items + expansion_items
    return final_items, insufficient_evidence, raw_candidate_count
