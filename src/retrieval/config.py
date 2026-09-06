# src/retrieval/config.py
"""
Configuration and Filter models for Phase 2.3 Legal Retrieval Pipeline.
Centralizes all default parameters, score thresholds, HNSW search settings,
and composable metadata filtering rules.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class RetrievalFilters(BaseModel):
    """
    Optional composable metadata filters applied as SQL WHERE clauses.
    All fields are optional and parameterized to prevent SQL injection.
    """
    jurisdiction: Optional[str] = Field(default=None, description="e.g. 'central' or state name 'maharashtra'")
    level: Optional[str] = Field(default=None, description="e.g. 'central' or 'state'")
    domains: Optional[List[str]] = Field(default=None, description="List of domains; OR semantics across selected list")
    source_type: Optional[str] = Field(default=None, description="'legislation' or 'judgment'")
    court: Optional[str] = Field(default=None, description="Court name (judgments only), e.g. 'Supreme Court of India'")
    date_after: Optional[str] = Field(default=None, description="Filter for date >= date_after (YYYY-MM-DD or YYYY)")
    date_before: Optional[str] = Field(default=None, description="Filter for date <= date_before (YYYY-MM-DD or YYYY)")
    effective_date_after: Optional[str] = Field(default=None, description="Filter for effective_date >= effective_date_after")
    effective_date_before: Optional[str] = Field(default=None, description="Filter for effective_date <= effective_date_before")


class RetrievalConfig(BaseModel):
    """
    Central configuration object for LegalRetriever.
    Prevents magic numbers across codebase.
    """
    # Candidate & Return K settings
    candidate_k: int = Field(default=30, description="Raw nearest neighbors pulled from pgvector before post-processing")
    final_k: int = Field(default=8, description="Final number of top direct matched chunks returned to caller")
    
    # HNSW Search Quality Parameter
    ef_search: int = Field(default=64, description="Query-time HNSW ef_search depth (higher = better recall, higher latency)")
    
    # Score Thresholds (Empirically derived from Phase 2.1 eval set)
    high_confidence_threshold: float = Field(default=0.55, description="Cosine similarity score for high confidence")
    low_confidence_threshold: float = Field(default=0.40, description="Cosine similarity score for low/weak confidence threshold")
    
    # Insufficient Evidence & Filter Relaxation
    min_acceptable_results: int = Field(default=1, description="Trigger insufficient_evidence flag if returned < min_acceptable_results")
    auto_relax_filters: bool = Field(default=True, description="Retry without metadata filters if filtered query returns < min_acceptable_results")
    
    # Context Expansion Settings
    include_parent_context: bool = Field(default=True, description="Fetch parent section chunk if available")
    include_sibling_context: bool = Field(default=False, description="Fetch adjacent sibling chunks (chunk_index +- 1)")
    sibling_window_size: int = Field(default=1, description="Number of adjacent sibling chunks to fetch on each side")
    
    # Preprocessing & Hardware Settings
    max_query_length: int = Field(default=1000, description="Max allowed character length for incoming query")
    use_gpu: bool = Field(default=True, description="Run BGE query embedding on CUDA GPU if available (fallback to CPU)")
    db_timeout_seconds: float = Field(default=10.0, description="Max wall-clock timeout for database query execution")
    
    # Deduplication policy
    dedup_policy: str = Field(default="exact_and_near", description="'exact_only' or 'exact_and_near'")
