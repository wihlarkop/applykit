from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from app.schemas import (
    ApplicationEntry,
    CoverLetterRequest,
    GeneratedCoverLetterEntry,
)


class RoleMatchCoverLetterRequest(CoverLetterRequest):
    role_match_analysis_id: int


class CompactRoleMatchAnalysis(BaseModel):
    id: int
    state: str
    score: int | None
    score_band: str | None
    confidence: str | None
    eligibility: str
    show_authoritative_score: bool
    summary: dict[str, Any] | None
    failure_code: str | None
    rules_version: str


class RoleMatchGeneratedCoverLetterEntry(GeneratedCoverLetterEntry):
    match_score_source: Literal[
        "role_evidence_match",
        "legacy_llm_score",
        "none",
    ] = "none"
    role_match_analysis_id: int | None = None
    role_match_analysis: CompactRoleMatchAnalysis | None = None


class RoleMatchGeneratedCoverLetterListResponse(BaseModel):
    items: list[RoleMatchGeneratedCoverLetterEntry]
    total: int


class RoleMatchApplicationEntry(ApplicationEntry):
    match_score_source: Literal[
        "role_evidence_match",
        "legacy_llm_score",
        "none",
    ] = "none"
    role_match_analysis_id: int | None = None


class RoleMatchApplicationListResponse(BaseModel):
    items: list[RoleMatchApplicationEntry]
    total: int
