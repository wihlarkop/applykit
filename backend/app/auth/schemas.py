"""Request and response schemas for Community protected mode."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class OwnerSetupRequest(BaseModel):
    setup_token: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=256)
    display_name: str | None = Field(default=None, max_length=80)


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)
    remember_device: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class AuthStatusResponse(BaseModel):
    auth_mode: Literal["disabled", "password"]
    setup_required: bool
    authenticated: bool
    session_expires_at: datetime | None = None


class AuthenticatedSessionResponse(BaseModel):
    authenticated: Literal[True] = True
    remember_device: bool
    session_expires_at: datetime


class SecuritySummaryResponse(BaseModel):
    other_sessions: int


class RevokeSessionsResponse(BaseModel):
    revoked_sessions: int
