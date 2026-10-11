from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session, selectinload

from app.models import GeneratedCV
from app.resume_readiness.constants import EXTRACTION_VERSION, RULES_VERSION
from app.resume_readiness.domain import ReadinessResult
from app.resume_readiness.models import (
    ResumeReadinessAnalysis,
    ResumeReadinessRuleResult,
)
from app.resume_readiness.normalization import normalize_text


def get_generated_cv(db: Session, generated_cv_id: int) -> GeneratedCV | None:
    return db.query(GeneratedCV).filter_by(id=generated_cv_id).first()


def get_analysis(
    db: Session,
    analysis_id: int,
) -> ResumeReadinessAnalysis | None:
    return (
        db.query(ResumeReadinessAnalysis)
        .options(selectinload(ResumeReadinessAnalysis.rule_results))
        .filter_by(id=analysis_id)
        .first()
    )


def get_latest_for_generated_cv(
    db: Session,
    generated_cv_id: int,
) -> ResumeReadinessAnalysis | None:
    return (
        db.query(ResumeReadinessAnalysis)
        .options(selectinload(ResumeReadinessAnalysis.rule_results))
        .filter_by(generated_cv_id=generated_cv_id)
        .order_by(
            ResumeReadinessAnalysis.created_at.desc(),
            ResumeReadinessAnalysis.id.desc(),
        )
        .first()
    )


def list_for_generated_cv(
    db: Session,
    generated_cv_id: int,
) -> list[ResumeReadinessAnalysis]:
    return (
        db.query(ResumeReadinessAnalysis)
        .options(selectinload(ResumeReadinessAnalysis.rule_results))
        .filter_by(generated_cv_id=generated_cv_id)
        .order_by(
            ResumeReadinessAnalysis.created_at.desc(),
            ResumeReadinessAnalysis.id.desc(),
        )
        .all()
    )


def _job_hash(job_description: str | None) -> str | None:
    normalized = normalize_text(job_description)
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _extraction_payload(result: ReadinessResult) -> dict[str, Any] | None:
    if result.extraction is None:
        return None
    return {
        "text": result.extraction.text,
        "page_count": result.extraction.page_count,
        "has_text_layer": result.extraction.has_text_layer,
        "warnings": list(result.extraction.warnings),
        "pages": [
            {
                "page_number": page.page_number,
                "text": page.text,
                "width": page.width,
                "height": page.height,
            }
            for page in result.extraction.pages
        ],
        "source_coverage": result.coverage.coverage if result.coverage else None,
    }


def create_analysis(
    db: Session,
    *,
    result: ReadinessResult,
    generated_cv: GeneratedCV,
    job_description_snapshot: str | None,
    role_match_analysis_id: int | None,
) -> ResumeReadinessAnalysis:
    previous = get_latest_for_generated_cv(db, generated_cv.id)
    row = ResumeReadinessAnalysis(
        generated_cv_id=generated_cv.id,
        profile_id=generated_cv.profile_id,
        role_match_analysis_id=role_match_analysis_id,
        supersedes_analysis_id=previous.id if previous else None,
        mode=result.mode.value,
        status=result.status.value,
        overall_score=result.overall.score,
        overall_band=result.overall.band,
        parseability_score=result.parseability.score if result.parseability else None,
        parseability_band=result.parseability.band if result.parseability else None,
        quality_score=result.quality.score if result.quality else None,
        quality_band=result.quality.band if result.quality else None,
        tailoring_score=result.tailoring.score if result.tailoring else None,
        tailoring_band=result.tailoring.band if result.tailoring else None,
        hard_gate_code=result.overall.hard_gate,
        failure_code=result.failure_code or result.overall.failure_code,
        source_profile_snapshot=generated_cv.profile_snapshot,
        job_description_snapshot=(job_description_snapshot.strip() if job_description_snapshot else None),
        job_description_hash=_job_hash(job_description_snapshot),
        extraction_json=(
            json.dumps(_extraction_payload(result), ensure_ascii=False)
            if _extraction_payload(result) is not None
            else None
        ),
        rules_version=RULES_VERSION,
        extraction_version=EXTRACTION_VERSION,
        semantic_version=None,
    )

    try:
        db.add(row)
        db.flush()
        for finding in result.rule_results:
            db.add(
                ResumeReadinessRuleResult(
                    analysis_id=row.id,
                    rule_id=finding.rule_id,
                    category=finding.category.value,
                    severity=finding.severity.value,
                    outcome=finding.outcome.value,
                    score_delta=finding.score_delta,
                    score_cap=finding.score_cap,
                    title=finding.title,
                    explanation=finding.explanation,
                    evidence_json=json.dumps(finding.evidence, ensure_ascii=False),
                    locations_json=json.dumps(list(finding.locations), ensure_ascii=False),
                    requires_review=finding.requires_review,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return get_analysis(db, row.id) or row
