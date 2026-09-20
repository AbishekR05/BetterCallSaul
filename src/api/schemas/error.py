# src/api/schemas/error.py
"""
Pydantic Schema for Standard API Errors (§7, §11).
"""

from pydantic import BaseModel, Field


class APIError(BaseModel):
    """
    Standardized, safe API error response model (§7, §11).
    Never leaks internal stack traces or provider error details to the client.
    """
    error_code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="Human-readable, non-leaking generic error message")
    request_id: str = Field(..., description="Unique request tracing identifier")
