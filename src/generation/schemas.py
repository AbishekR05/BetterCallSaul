# src/generation/schemas.py
"""
Data Schemas and Pydantic Models for Phase 2.6 Grounded RAG Answer Generation.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class Citation(BaseModel):
    """
    Resolved full provenance citation object.
    Traces directly back to a real chunk_id retrieved from the database.
    """
    local_id: str                          # e.g., "E1", "E2"
    chunk_id: str
    document_id: str
    document_type: str = "legislation"     # legislation | judgment | other
    title: str = ""
    act: Optional[str] = ""
    section: Optional[str] = ""
    court: Optional[str] = ""
    jurisdiction: str = "central"
    source_url: Optional[str] = ""
    relevance_score: float = 0.0


class LLMResponse(BaseModel):
    """
    Raw telemetry response object returned by LLMClient implementations.
    """
    raw_text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    model_name: str = ""
    model_version: str = ""
    finish_reason: str = "stop"


class RawAnswerModel(BaseModel):
    """
    Intermediate JSON schema expected from the LLM generation response (§6).
    """
    answer_summary: str
    answer_detail: str
    applicable_jurisdiction: str = "unclear"  # central | <state/UT> | multiple | unclear
    evidence_sufficiency: Literal["sufficient", "partial", "insufficient"] = "insufficient"
    citations_used: List[str] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)
    clarifying_question: Optional[str] = None


class GenerationMetadata(BaseModel):
    """
    Telemetry and performance metadata recorded for every generation call (§11).
    """
    llm_provider: str
    llm_model: str
    prompt_version: str
    retrieval_adapter_used: str = "Phase2.5_Hybrid_Reranked_Calibrated"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: Optional[float] = None
    latency_ms_retrieval: float = 0.0
    latency_ms_generation: float = 0.0
    latency_ms_total: float = 0.0
    parse_retry_count: int = 0
    timestamp_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class GroundedAnswer(BaseModel):
    """
    Final public structured response returned by Phase 2.6 pipeline (§7.2).
    """
    query: str
    answer_summary: str
    answer_detail: str
    applicable_jurisdiction: str
    evidence_sufficiency: Literal["sufficient", "partial", "insufficient"]
    citations: List[Citation] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)
    clarifying_question: Optional[str] = None
    unused_evidence_count: int = 0
    generation_metadata: GenerationMetadata
    safety_flags: List[str] = Field(default_factory=list)
