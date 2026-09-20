# src/api/schemas/auth.py
"""
Pydantic Schemas for Authentication Operations (§7).
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


class RegisterRequest(BaseModel):
    """
    User registration payload (§7).
    No user_id input permitted.
    """
    auth_identifier: str = Field(..., description="User login identifier (e.g. email or username)")
    password: str = Field(..., min_length=8, description="Raw user password")


class LoginRequest(BaseModel):
    """
    User login payload (§7).
    """
    auth_identifier: str = Field(..., description="User login identifier")
    password: str = Field(..., description="Raw user password")


class AuthUserResponse(BaseModel):
    """
    Response returned upon successful account creation (§7).
    """
    user_id: UUID = Field(..., description="Server-assigned unique user identifier")
    auth_identifier: str = Field(..., description="Normalized user authentication identifier")
    created_at_utc: datetime = Field(..., description="Account creation timestamp")


class AuthTokenResponse(BaseModel):
    """
    Response returned upon successful login (§7).
    """
    access_token: str = Field(..., description="Opaque bearer authentication token")
    expires_at_utc: datetime = Field(..., description="Token expiry timestamp")
    token_type: str = Field(default="bearer", description="Authentication scheme type")
