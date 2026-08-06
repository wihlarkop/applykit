from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.exceptions import InvalidRequestError, RoleMatchAnalysisNotFoundError
from app.role_match.domain import (
    AnalysisSummary,
    ConfidenceAssessment,
    ConfidenceBand,
    EligibilityAssessment,
    EligibilityStatus,
)
from app.role_match.models import RoleMatchAnalysis, RoleMatchOverride
from app.role_match.overrides import _reconstruct_source
from app.role_match.scoring import score_role_match
from app.role_match.snapshots import SnapshotInput, save_analysis_snapshot


def _loads(raw: str | None, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def restore_user_override(
    db: Session,
    analysis_id: int,
    override_id: int,
) -> RoleMatchAnalysis:
    current = db.query(RoleMatchAnalysis).filter_by(id=analysis_id).first()
    if current is None:
        raise RoleMatchAnalysisNotFoundError(analysis_id)
    override = db.query(RoleMatchOverride).filter_by(
        id=override_id,
        analysis_id=analysis_id,
    ).first()
    if override is None:
        raise InvalidRequestError("Override was not found in this analysis")
    if current.parent_analysis_id is None:
        raise InvalidRequestError("This analysis does not have an original snapshot")

    original = db.query(RoleMatchAnalysis).filter_by(
        id=current.parent_analysis_id
    ).first()
    if original is None:
        raise RoleMatchAnalysisNotFoundError(current.parent_analysis_id)

    clusters, assessments, catalog = _reconstruct_source(db, original)
    score = score_role_match(assessments) if assessments else None
    normalized = _loads(original.normalized_payload, {})
    summary_raw = normalized.get("summary")
    summary = AnalysisSummary.model_validate(summary_raw) if summary_raw else None
    confidence = None
    if original.confidence_score is not None and original.confidence_band is not None:
        confidence = ConfidenceAssessment(
            score=original.confidence_score,
            band=ConfidenceBand(original.confidence_band),
            explanation="Restored from the original audited analysis.",
        )

    return save_analysis_snapshot(
        db,
        SnapshotInput(
            profile_id=original.profile_id,
            application_id=original.application_id,
            parent_analysis_id=current.id,
            state=original.state,
            job_description=original.job_description,
            safe_profile_json=original.safe_profile_snapshot,
            provider=original.model_provider,
            model_name=original.model_name,
            raw_llm_output=original.raw_llm_output,
            clusters=clusters,
            assessments=assessments,
            catalog=catalog,
            score=score,
            confidence=confidence,
            eligibility=EligibilityAssessment(
                status=EligibilityStatus(original.eligibility_status)
            ),
            show_authoritative_score=bool(original.show_authoritative_score),
            failure_code=original.failure_code,
            excluded_items=_loads(original.excluded_items, []),
            summary=summary,
            analysis_date=original.analysis_date,
        ),
    )
