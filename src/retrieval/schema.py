# src/retrieval/schema.py
"""
Pydantic Schema models for Phase 2.3 Legal Retrieval Pipeline.
Defines the stable public contract for RetrievalResult and RetrievalResultItem.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from src.retrieval.config import RetrievalFilters


class ProvenanceFields(BaseModel):
    """Authoritative legal provenance metadata for every retrieved chunk."""
    document_id: str
    chunk_id: str
    source_type: str  # 'legislation' | 'judgment' | 'other'
    title: Optional[str] = ""
    act: Optional[str] = ""
    case_name: Optional[str] = ""
    citation: Optional[str] = ""
    court: Optional[str] = ""
    jurisdiction: Optional[str] = "central"
    level: Optional[str] = "central"
    state: Optional[str] = ""
    date: Optional[str] = ""
    effective_date: Optional[str] = ""
    is_historical: Optional[bool] = False
    source_url: Optional[str] = ""
    original_source_id: Optional[str] = ""
    dataset_version: Optional[str] = "1.0"
    part: Optional[str] = ""
    chapter: Optional[str] = ""
    section: Optional[str] = ""
    subsection: Optional[str] = ""
    clause: Optional[str] = ""
    paragraph_number: Optional[str] = ""


class RetrievalResultItem(BaseModel):
    """Individual legal chunk match item with score, provenance, and context type."""
    chunk_id: str
    document_id: str
    text: str
    similarity_score: float
    confidence_tier: Literal["high", "low"] = "high"
    match_type: Literal["direct", "parent_context", "sibling_context"] = "direct"
    provenance: ProvenanceFields


class RetrievalTiming(BaseModel):
    """Detailed timing telemetry breakdown in milliseconds."""
    total_latency_ms: float = 0.0
    preprocessing_latency_ms: float = 0.0
    embedding_latency_ms: float = 0.0
    db_search_latency_ms: float = 0.0
    postprocessing_latency_ms: float = 0.0


class RetrievalResult(BaseModel):
    """
    Public result object returned by LegalRetriever.
    Structured, fully serializable to JSON, and compatible with LangChain.
    """
    query: str
    normalized_query: str
    filters_requested: Optional[RetrievalFilters] = None
    filters_applied: Optional[RetrievalFilters] = None
    insufficient_evidence: bool = False
    candidate_count: int = 0
    returned_count: int = 0
    results: List[RetrievalResultItem] = Field(default_factory=list)
    timing: RetrievalTiming = Field(default_factory=RetrievalTiming)
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None
