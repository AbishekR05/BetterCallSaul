# src/api/schemas/session.py
"""
Pydantic Schemas for Conversation Session Operations (§6, §7).
Enforces ConfigDict(extra="forbid", str_strip_whitespace=True).
"""

from datetime import datetime
from typing import List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class CreateSessionRequest(BaseModel):
    """
    Request payload to create a new session (§6, §7).
    No extra fields or user_id allowed; user_id is assigned from token.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SessionResponse(BaseModel):
    """
    Response model for session details.
    """
    session_id: UUID = Field(..., description="Unique conversation session identifier")
    created_at_utc: datetime = Field(..., description="Session creation timestamp")
    last_active_utc: datetime = Field(..., description="Last active timestamp")
    expires_at_utc: datetime = Field(..., description="Session expiration timestamp")
    status: str = Field(..., description="Session status ('active', 'expired', 'closed')")
    turn_count: int = Field(default=0, description="Total conversation turns in session")
    turns: List[Dict[str, Any]] = Field(default_factory=list, description="List of turns in session")


class SessionListResponse(BaseModel):
    """
    Response container listing caller's owned sessions.
    """
    sessions: List[SessionResponse] = Field(default_factory=list, description="List of owned sessions")
