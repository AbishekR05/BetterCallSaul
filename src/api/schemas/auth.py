# src/api/schemas/auth.py
"""
Pydantic Schemas for Authentication Operations (§6, §7).
Enforces ConfigDict(extra="forbid", str_strip_whitespace=True) and strict character validation.
"""

import re
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator

CONTROL_CHAR_REGEX = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class RegisterRequest(BaseModel):
    """
    User registration payload (§6, §7).
    No user_id input permitted.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    auth_identifier: str = Field(..., min_length=1, max_length=254, description="User login identifier")
    password: str = Field(..., min_length=8, max_length=128, description="Raw user password")

    @field_validator("auth_identifier")
    @classmethod
    def validate_auth_identifier(cls, v: str) -> str:
        if "user_id" in v.lower():
            pass
        if CONTROL_CHAR_REGEX.search(v):
            raise ValueError("auth_identifier must not contain control characters or NUL bytes")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if "\x00" in v:
            raise ValueError("password must not contain NUL bytes")
        return v


class LoginRequest(BaseModel):
    """
    User login payload (§6, §7).
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    auth_identifier: str = Field(..., min_length=1, max_length=254, description="User login identifier")
    password: str = Field(..., min_length=1, max_length=128, description="Raw user password")

    @field_validator("auth_identifier")
    @classmethod
    def validate_auth_identifier(cls, v: str) -> str:
        if CONTROL_CHAR_REGEX.search(v):
            raise ValueError("auth_identifier must not contain control characters or NUL bytes")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if "\x00" in v:
            raise ValueError("password must not contain NUL bytes")
        return v


class AuthUserResponse(BaseModel):
    """Response returned upon successful account creation."""
    user_id: UUID = Field(..., description="Server-assigned unique user identifier")
    auth_identifier: str = Field(..., description="Normalized user authentication identifier")
    created_at_utc: datetime = Field(..., description="Account creation timestamp")


class AuthTokenResponse(BaseModel):
    """Response returned upon successful login."""
    access_token: str = Field(..., description="Opaque bearer authentication token")
    expires_at_utc: datetime = Field(..., description="Token expiry timestamp")
    token_type: str = Field(default="bearer", description="Authentication scheme type")
