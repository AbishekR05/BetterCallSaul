# src/retrieval/retriever.py
"""
Main LegalRetriever orchestrator for Phase 2.3.
Provides a clean, read-only entrypoint for RAG search.
"""

import time
from typing import Optional
from src.db_phase2 import get_connection
from src.retrieval.config import RetrievalConfig, RetrievalFilters
from src.retrieval.schema import RetrievalResult, RetrievalTiming
from src.retrieval.preprocessing import preprocess_query
from src.retrieval.embedding import QueryEmbedder
from src.retrieval.search import execute_vector_search
from src.retrieval.postprocessing import process_candidate_results
from src.retrieval.logging_utils import log_retrieval_event


class LegalRetriever:
    """
    Production-ready, read-only legal document retriever.
    Integrates query normalization, prefixed BGE embedding, pgvector HNSW search,
    metadata filtering, score thresholding, context expansion, and telemetry logging.
    """
    def __init__(self, config: Optional[RetrievalConfig] = None):
        self.config = config or RetrievalConfig()
        self.embedder = QueryEmbedder(use_gpu=self.config.use_gpu)

    def retrieve(
        self,
        query: str,
        filters: Optional[RetrievalFilters] = None,
        config: Optional[RetrievalConfig] = None
    ) -> RetrievalResult:
        """
        Executes legal retrieval for incoming layman question string.
        Returns structured RetrievalResult. Strictly READ-ONLY against database.
        """
        start_total = time.time()
        cfg = config or self.config
        timing = RetrievalTiming()
        warnings = []
        
        # 1. Preprocessing & Normalization
        start_prep = time.time()
        try:
            norm_query, prep_warnings = preprocess_query(query, max_length=cfg.max_query_length)
            warnings.extend(prep_warnings)
        except Exception as e:
            # Safe fail-closed handling for invalid query
            total_ms = (time.time() - start_total) * 1000.0
            timing.total_latency_ms = total_ms
            res = RetrievalResult(
                query=query,
                normalized_query="",
                filters_requested=filters,
                filters_applied=filters,
                insufficient_evidence=True,
                candidate_count=0,
                returned_count=0,
                results=[],
                timing=timing,
                warnings=warnings,
                error=str(e)
            )
            log_retrieval_event(res)
            return res
            
        timing.preprocessing_latency_ms = (time.time() - start_prep) * 1000.0

        # 2. BGE Query Embedding Generation
        start_embed = time.time()
        try:
            query_vector = self.embedder.embed_query(norm_query)
        except Exception as e:
            total_ms = (time.time() - start_total) * 1000.0
            timing.total_latency_ms = total_ms
            res = RetrievalResult(
                query=query,
                normalized_query=norm_query,
                filters_requested=filters,
                filters_applied=filters,
                insufficient_evidence=True,
                candidate_count=0,
                returned_count=0,
                results=[],
                timing=timing,
                warnings=warnings,
                error=f"Embedding error: {e}"
            )
            log_retrieval_event(res)
            return res
            
        timing.embedding_latency_ms = (time.time() - start_embed) * 1000.0

        # 3. Database Vector Search & Post-Processing
        filters_applied = filters
        raw_candidates = []
        final_items = []
        insufficient_ev = False
        raw_cand_count = 0
        
        try:
            conn = get_connection(autocommit=False)
            try:
                # Primary Vector Search
                raw_candidates, db_latency_ms = execute_vector_search(
                    conn=conn,
                    query_vector=query_vector,
                    candidate_k=cfg.candidate_k,
                    ef_search=cfg.ef_search,
                    filters=filters_applied,
                    db_timeout_seconds=cfg.db_timeout_seconds
                )
                timing.db_search_latency_ms = db_latency_ms
                
                # Post-Processing
                start_post = time.time()
                final_items, insufficient_ev, raw_cand_count = process_candidate_results(
                    conn=conn,
                    raw_candidates=raw_candidates,
                    config=cfg
                )
                timing.postprocessing_latency_ms = (time.time() - start_post) * 1000.0
                
                # Filter Relaxation Retry
                if insufficient_ev and filters_applied is not None and cfg.auto_relax_filters:
                    warnings.append("Requested metadata filters returned insufficient evidence; auto-relaxing filters.")
                    relaxed_raw, relaxed_db_ms = execute_vector_search(
                        conn=conn,
                        query_vector=query_vector,
                        candidate_k=cfg.candidate_k,
                        ef_search=cfg.ef_search,
                        filters=None,
                        db_timeout_seconds=cfg.db_timeout_seconds
                    )
                    relaxed_items, relaxed_insuff, _ = process_candidate_results(
                        conn=conn,
                        raw_candidates=relaxed_raw,
                        config=cfg
                    )
                    if len(relaxed_items) > 0 and not relaxed_insuff:
                        final_items = relaxed_items
                        insufficient_ev = False
                        filters_applied = None
                        raw_candidates = relaxed_raw
                        raw_cand_count = len(relaxed_raw)
                        
            finally:
                conn.close()
                
        except Exception as e:
            total_ms = (time.time() - start_total) * 1000.0
            timing.total_latency_ms = total_ms
            res = RetrievalResult(
                query=query,
                normalized_query=norm_query,
                filters_requested=filters,
                filters_applied=filters_applied,
                insufficient_evidence=True,
                candidate_count=0,
                returned_count=0,
                results=[],
                timing=timing,
                warnings=warnings,
                error=f"Database search error: {e}"
            )
            log_retrieval_event(res)
            return res

        timing.total_latency_ms = (time.time() - start_total) * 1000.0
        
        # 4. Construct Final Result Object
        result = RetrievalResult(
            query=query,
            normalized_query=norm_query,
            filters_requested=filters,
            filters_applied=filters_applied,
            insufficient_evidence=insufficient_ev,
            candidate_count=raw_cand_count,
            returned_count=len(final_items),
            results=final_items,
            timing=timing,
            warnings=warnings,
            error=None
        )
        
        # 5. Log Telemetry Event
        log_retrieval_event(result)
        return result
