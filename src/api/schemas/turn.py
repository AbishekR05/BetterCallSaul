# src/api/schemas/turn.py
"""
Pydantic Schemas for Conversation Turn Operations (§6, §7).
Enforces ConfigDict(extra="forbid", str_strip_whitespace=True) and turn query limits.
"""

import re
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator

CONTROL_CHAR_REGEX = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class TurnRequest(BaseModel):
    """
    Payload for submitting a conversational turn (§6, §7).
    Must not include user_id or session_id in body; query bounded between 1 and 2,000 characters.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(..., min_length=1, max_length=2000, description="User legal query text")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if CONTROL_CHAR_REGEX.search(v):
            raise ValueError("query must not contain control characters or NUL bytes")
        return v


class CitationResponse(BaseModel):
    """
    Public citation reference model.
    """
    document_title: str = Field(..., description="Title of cited statute or case law document")
    document_type: str = Field(..., description="Legal document category")
    jurisdiction: str = Field(..., description="Legal jurisdiction governing document")
    section: Optional[str] = Field(default=None, description="Specific section or article reference")
    source_reference: Optional[str] = Field(default=None, description="Source reference citation text")


class GroundedAnswerResponse(BaseModel):
    """
    Public response model for a grounded conversational turn (§7).
    Intentionally omits internal generation metadata and safety flags.
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
