# src/api/schemas/__init__.py
"""
Pydantic Schemas Package for Phase 3.0 API.
"""

from src.api.schemas.error import APIError
from src.api.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    AuthUserResponse,
    AuthTokenResponse,
)
from src.api.schemas.session import (
    CreateSessionRequest,
    SessionResponse,
    SessionListResponse,
)
from src.api.schemas.turn import (
    TurnRequest,
    CitationResponse,
    GroundedAnswerResponse,
)

__all__ = [
    "APIError",
    "RegisterRequest",
    "LoginRequest",
    "AuthUserResponse",
    "AuthTokenResponse",
    "CreateSessionRequest",
    "SessionResponse",
    "SessionListResponse",
    "TurnRequest",
    "CitationResponse",
    "GroundedAnswerResponse",
]
