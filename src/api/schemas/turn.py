# src/api/schemas/turn.py
"""
Pydantic Schemas for Conversation Turn Operations (§7).
"""

from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class TurnRequest(BaseModel):
    """
    Payload for submitting a conversational turn (§7).
    Must not include user_id or session_id in body; user_id is derived from auth, session_id from path.
    """
    query: str = Field(..., min_length=1, max_length=4096, description="User legal query text")


class CitationResponse(BaseModel):
    """
    Public citation reference model (§7).
    """
    document_title: str = Field(..., description="Title of cited statute or case law document")
    document_type: str = Field(..., description="Legal document category")
    jurisdiction: str = Field(..., description="Legal jurisdiction governing document")
    section: Optional[str] = Field(default=None, description="Specific section or article reference")
    source_reference: Optional[str] = Field(default=None, description="Source reference citation text")


class GroundedAnswerResponse(BaseModel):
    """
    Public response model for a grounded conversational turn (§7).
    Intentionally omits internal generation metadata (cost/tokens/model) and safety flags.
    """
    session_id: UUID = Field(..., description="Conversation session identifier")
    turn_index: int = Field(..., description="Ordinal index of turn within session")
    answer_summary: str = Field(..., description="High-level legal answer summary")
    answer_detail: str = Field(..., description="Detailed grounded legal analysis")
    applicable_jurisdiction: str = Field(..., description="Jurisdiction determined for answer")
    evidence_sufficiency: str = Field(..., description="Sufficiency verdict of legal context")
    citations: List[CitationResponse] = Field(default_factory=list, description="Legal citations used")
    caveats: List[str] = Field(default_factory=list, description="Legal disclaimers or caveats")
    clarifying_question: Optional[str] = Field(default=None, description="Optional clarifying question if ambiguous")
