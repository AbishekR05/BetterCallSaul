# src/conversation/schemas.py
"""
Data Schemas and Pydantic Models for Phase 2.7 Conversational Context & Session Memory.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from src.generation.schemas import GroundedAnswer


class ContextSelectionTrace(BaseModel):
    """
    Debug trace recording which prior turn indices were selected by ContextSelector and why.
    """
    selected_turn_indices: List[int] = Field(default_factory=list)
    selection_reasons: List[str] = Field(default_factory=list)
    estimated_token_cost: int = 0
    window_size: int = 0
    cleared_on_topic_change: bool = False


class RewriteResult(BaseModel):
    """
    Structured output produced by QueryRewriter.
    """
    rewritten_query: Optional[str] = None
    resolution_status: Literal["resolved", "unresolved", "ambiguous"] = "resolved"
    carried_jurisdiction: Optional[str] = None
    carried_domain: Optional[str] = None
    raw_response: Optional[str] = None


class ConversationTurn(BaseModel):
    """
    Represents a single conversational turn in a session.
    """
    turn_id: str
    turn_index: int                               # ordinal within session (1-indexed)
    user_query: str
    rewritten_query: Optional[str] = None
    followup_classification: str = "standalone"    # standalone | simple_followup | topic_change | ambiguous_followup | contradictory_followup
    grounded_answer: GroundedAnswer
    jurisdiction_carried_forward: Optional[str] = None
    domain_carried_forward: Optional[str] = None
    timestamp_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ConversationSession(BaseModel):
    """
    Session container representing state and conversation history.
    """
    session_id: str
    user_id: Optional[str] = None
    created_at_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_active_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at_utc: str
    turns: List[ConversationTurn] = Field(default_factory=list)
    turn_count: int = 0
    status: Literal["active", "expired", "closed"] = "active"


class ConversationTurnResult(BaseModel):
    """
    Public return type of ConversationalOrchestrator.handle_turn().
    """
    session_id: str
    turn: ConversationTurn
    context_selector_debug: ContextSelectionTrace
