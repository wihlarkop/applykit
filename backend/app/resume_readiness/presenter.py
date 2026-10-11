from __future__ import annotations

import json
from typing import Any

from app.resume_readiness.models import ResumeReadinessAnalysis
from app.resume_readiness.schemas import (
    ResumeReadinessCategoriesResponse,
    ResumeReadinessCategoryResponse,
    ResumeReadinessExtractionResponse,
    ResumeReadinessFindingResponse,
    ResumeReadinessResponse,
    ResumeReadinessScoreResponse,
    ResumeReadinessSummaryResponse,
    ResumeReadinessVersionsResponse,
)


def _loads(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def _category(
    score: int | None,
    band: str | None,
    findings: list[ResumeReadinessFindingResponse],
    category: str,
) -> ResumeReadinessCategoryResponse | None:
    if score is None or band is None:
        return None
    caps = [
        finding.score_cap
        for finding in findings
        if finding.category == category and finding.score_cap is not None
    ]
    return ResumeReadinessCategoryResponse(
        score=score,
        band=band,
        score_cap=min(caps) if caps else None,
    )


def present_analysis(analysis: ResumeReadinessAnalysis) -> ResumeReadinessResponse:
    findings = [
        ResumeReadinessFindingResponse(
            id=row.id,
            rule_id=row.rule_id,
            category=row.category,
            severity=row.severity,
            outcome=row.outcome,
            score_delta=row.score_delta,
            score_cap=row.score_cap,
            title=row.title,
            explanation=row.explanation,
            evidence=_loads(row.evidence_json, {}),
            locations=_loads(row.locations_json, []),
            requires_review=bool(row.requires_review),
        )
        for row in analysis.rule_results
    ]
    extraction_raw = _loads(analysis.extraction_json, None)
    extraction = None
    if extraction_raw:
        extraction = ResumeReadinessExtractionResponse(
            page_count=int(extraction_raw.get("page_count") or 0),
            has_text_layer=bool(extraction_raw.get("has_text_layer")),
            text_preview=str(extraction_raw.get("text") or "")[:10_000],
            warnings=list(extraction_raw.get("warnings") or []),
            source_coverage=extraction_raw.get("source_coverage"),
        )

    summary = ResumeReadinessSummaryResponse(
        critical=sum(
            item.severity == "critical" and item.outcome in {"fail", "warning"}
            for item in findings
        ),
        important=sum(
            item.severity == "important" and item.outcome in {"fail", "warning"}
            for item in findings
        ),
        improvements=sum(
            item.severity == "improvement" and item.outcome in {"fail", "warning"}
            for item in findings
        ),
        passed=sum(item.outcome == "pass" for item in findings),
        unknown=sum(item.outcome in {"unknown", "excluded"} for item in findings),
    )

    return ResumeReadinessResponse(
        id=analysis.id,
        generated_cv_id=analysis.generated_cv_id,
        profile_id=analysis.profile_id,
        role_match_analysis_id=analysis.role_match_analysis_id,
        supersedes_analysis_id=analysis.supersedes_analysis_id,
        mode=analysis.mode,
        status=analysis.status,
        overall=ResumeReadinessScoreResponse(
            score=analysis.overall_score,
            band=analysis.overall_band,
            hard_gate=analysis.hard_gate_code,
        ),
        categories=ResumeReadinessCategoriesResponse(
            parseability=_category(
                analysis.parseability_score,
                analysis.parseability_band,
                findings,
                "parseability",
            ),
            quality=_category(
                analysis.quality_score,
                analysis.quality_band,
                findings,
                "quality",
            ),
            tailoring=_category(
                analysis.tailoring_score,
                analysis.tailoring_band,
                findings,
                "tailoring",
            ),
        ),
        summary=summary,
        findings=findings,
        extraction=extraction,
        versions=ResumeReadinessVersionsResponse(
            rules=analysis.rules_version,
            extraction=analysis.extraction_version,
            semantic=analysis.semantic_version,
        ),
        failure_code=analysis.failure_code,
        created_at=analysis.created_at,
    )
