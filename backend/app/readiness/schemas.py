from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel

ProfileRequirement = Literal[
    "name",
    "email",
    "experience_or_education",
    "skills",
]


class ProfileReadiness(BaseModel):
    profile_id: int
    ready: bool
    completeness: int
    missing_requirements: list[ProfileRequirement]
    recommendations: list[str]


class AiReadinessStatus(str, Enum):
    NOT_CONFIGURED = "not_configured"
    RETEST_REQUIRED = "retest_required"
    CONFIGURATION_CHANGED = "configuration_changed"
    READY = "ready"
    AUTHENTICATION_FAILED = "authentication_failed"
    ENDPOINT_UNREACHABLE = "endpoint_unreachable"
    MODEL_UNAVAILABLE = "model_unavailable"
    RATE_LIMITED = "rate_limited"
    UNKNOWN_FAILURE = "unknown_failure"


class ConnectionFailureCategory(str, Enum):
    AUTHENTICATION_FAILED = "authentication_failed"
    ENDPOINT_UNREACHABLE = "endpoint_unreachable"
    MODEL_UNAVAILABLE = "model_unavailable"
    RATE_LIMITED = "rate_limited"
    UNKNOWN_FAILURE = "unknown_failure"


class AiReadiness(BaseModel):
    ready: bool
    status: AiReadinessStatus
    provider: str | None = None
    model: str | None = None
    tested_at: datetime | None = None
    failure_category: ConnectionFailureCategory | None = None
    message: str
    configuration_fingerprint: str | None = None


class OnboardingState(BaseModel):
    version: int
    seen: bool
    skipped: bool
    should_redirect: bool


class ReadinessResponse(BaseModel):
    onboarding: OnboardingState
    profile: ProfileReadiness
    ai: AiReadiness
    applykit_ready: bool
    checklist_visible: bool
    checklist_fingerprint: str


class ReadinessProfileRequest(BaseModel):
    profile_id: int
