from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ResumeReadinessAnalyzeRequest(BaseModel):
    generated_cv_id: int = Field(gt=0)
    job_description: str | None = Field(default=None, max_length=100_000)
    role_match_analysis_id: int | None = Field(default=None, gt=0)


class ResumeReadinessScoreResponse(BaseModel):
    score: int | None
    band: str | None
    hard_gate: str | None = None


class ResumeReadinessCategoryResponse(BaseModel):
    score: int
    band: str
    score_cap: int | None = None


class ResumeReadinessCategoriesResponse(BaseModel):
    parseability: ResumeReadinessCategoryResponse | None
    quality: ResumeReadinessCategoryResponse | None
    tailoring: ResumeReadinessCategoryResponse | None


class ResumeReadinessSummaryResponse(BaseModel):
    critical: int
    important: int
    improvements: int
    passed: int
    unknown: int


class ResumeReadinessFindingResponse(BaseModel):
    id: int | None = None
    rule_id: str
    category: Literal["parseability", "quality", "tailoring"]
    severity: Literal["info", "improvement", "important", "critical"]
    outcome: Literal["pass", "warning", "fail", "unknown", "excluded"]
    score_delta: int
    score_cap: int | None
    title: str
    explanation: str
    evidence: dict[str, Any]
    locations: list[str]
    requires_review: bool


class ResumeReadinessExtractionResponse(BaseModel):
    page_count: int
    has_text_layer: bool
    text_preview: str
    warnings: list[str]
    source_coverage: float | None = None


class ResumeReadinessVersionsResponse(BaseModel):
    rules: str
    extraction: str
    semantic: str | None


class ResumeReadinessResponse(BaseModel):
    id: int
    generated_cv_id: int
    profile_id: int | None
    role_match_analysis_id: int | None
    supersedes_analysis_id: int | None
    mode: Literal["general", "job_specific"]
    status: Literal["complete", "needs_review", "failed"]
    overall: ResumeReadinessScoreResponse
    categories: ResumeReadinessCategoriesResponse
    summary: ResumeReadinessSummaryResponse
    findings: list[ResumeReadinessFindingResponse]
    extraction: ResumeReadinessExtractionResponse | None
    versions: ResumeReadinessVersionsResponse
    failure_code: str | None
    created_at: datetime


class ResumeReadinessListResponse(BaseModel):
    items: list[ResumeReadinessResponse]
    total: int
