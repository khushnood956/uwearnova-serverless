"""
Pydantic Schemas for Authentication & Identity
Provides strict request validation and sanitized response structures.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Valid customer email address")
    password: str = Field(..., min_length=8, max_length=128, description="Minimum 8 characters")
    phone: Optional[str] = Field(None, max_length=32, description="Optional phone number")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered account email")
    password: str = Field(..., min_length=1, description="Account password")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes in seconds


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, description="Active refresh token string")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, description="Current account password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password (minimum 8 chars)")


class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address associated with account")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(..., min_length=1, description="One-time password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password (minimum 8 chars)")


class UserResponse(BaseModel):
    """Sanitized user profile safe for API responses (never exposes password_hash)."""

    id: int
    email: str
    phone: Optional[str] = None
    status: str
    user_type: str
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str
