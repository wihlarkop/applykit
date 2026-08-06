from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from app.role_match.api_schemas import RoleMatchAnalysisResponse
from app.schemas import (
    ApplicationEntry,
    CoverLetterRequest,
    GeneratedCoverLetterEntry,
)


class RoleMatchCoverLetterRequest(CoverLetterRequest):
    role_match_analysis_id: int


class RoleMatchGeneratedCoverLetterEntry(GeneratedCoverLetterEntry):
    fit_analysis: dict[str, Any] | None = None
    match_score_source: Literal[
        "role_evidence_match",
        "legacy_llm_score",
        "none",
    ] = "none"
    role_match_analysis_id: int | None = None
    role_match_analysis: RoleMatchAnalysisResponse | None = None


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
