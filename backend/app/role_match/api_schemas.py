from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RoleMatchAnalyzeRequest(BaseModel):
    profile_id: int
    job_description: str = Field(min_length=1)
    application_id: int | None = None
    parent_analysis_id: int | None = None


class RoleMatchReanalyzeRequest(BaseModel):
    profile_id: int | None = None
    job_description: str | None = None
    application_id: int | None = None


class RoleMatchEvidenceResponse(BaseModel):
    id: int
    evidence_id: str
    source_type: str
    source_text: str
    relationship: str
    depth: str
    duplicate: bool
    contradiction: bool
    explanation: str | None


class RoleMatchRequirementResponse(BaseModel):
    id: int
    cluster_id: str
    canonical_key: str
    canonical_text: str
    primary_category: str
    importance: str
    mention_count: int
    importance_conflict: bool
    source_quotes: list[str]
    excluded: bool
    exclusion_reason: str | None
    match_level: str | None
    strength: float | None
    explanation: str | None
    evidence: list[RoleMatchEvidenceResponse]


class RoleMatchCategoryResponse(BaseModel):
    category: str
    score: float
    known_coverage: float
    unknown_coverage: float
    known_match: float
    requirement_count: int


class RoleMatchSummaryResponse(BaseModel):
    headline: str
    description: str
    strengths: list[dict[str, Any]] = []
    concerns: list[dict[str, Any]] = []
    next_step: str


class ExcludedAnalysisItemResponse(BaseModel):
    source_id: str
    text: str
    reason: str


class RoleMatchOverrideResponse(BaseModel):
    id: int
    requirement_key: str
    field_name: str
    extracted_value: Any
    effective_value: Any
    reason: str
    source: str
    carry_status: Literal[
        "carried_forward",
        "needs_review",
        "not_applicable",
    ]
    source_override_id: int | None
    created_at: datetime


class RoleMatchAnalysisResponse(BaseModel):
    id: int
    parent_analysis_id: int | None
    created_at: datetime
    state: Literal["success", "needs_review", "failed"]
    score: int | None
    score_band: str | None
    confidence: Literal["high", "medium", "low"] | None
    eligibility: Literal[
        "eligible",
        "likely_eligible",
        "eligibility_unclear",
        "likely_ineligible",
        "ineligible",
    ]
    show_authoritative_score: bool
    summary: RoleMatchSummaryResponse | None
    category_breakdown: list[RoleMatchCategoryResponse]
    requirements: list[RoleMatchRequirementResponse]
    excluded_items: list[ExcludedAnalysisItemResponse]
    overrides: list[RoleMatchOverrideResponse] = []
    override_review_count: int
    rules_version: str
    prompt_version: str
    legacy: bool = False
    failure_code: str | None = None


class RoleMatchVersionItem(BaseModel):
    id: int
    parent_analysis_id: int | None
    created_at: datetime
    state: str
    score: int | None
    confidence: str | None
    eligibility: str
    superseded_by_id: int | None


class RoleMatchVersionsResponse(BaseModel):
    items: list[RoleMatchVersionItem]


class RoleMatchComparisonResponse(BaseModel):
    from_analysis_id: int
    to_analysis_id: int
    score_change: int | None
    added_requirements: list[str]
    removed_requirements: list[str]
    changed_requirements: list[dict[str, Any]]


class RoleMatchOverrideInput(BaseModel):
    requirement_key: str
    field_name: Literal[
        "importance",
        "excluded",
        "experience_status",
        "evidence_unlink",
    ]
    effective_value: Any
    reason: str = Field(min_length=1)


class RoleMatchOverridesRequest(BaseModel):
    overrides: list[RoleMatchOverrideInput] = Field(min_length=1)
