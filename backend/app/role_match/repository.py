from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.role_match.api_schemas import (
    RoleMatchAnalysisResponse,
    RoleMatchCategoryResponse,
    RoleMatchComparisonResponse,
    RoleMatchEvidenceResponse,
    RoleMatchRequirementResponse,
    RoleMatchSummaryResponse,
    RoleMatchVersionItem,
    RoleMatchVersionsResponse,
)
from app.role_match.models import (
    RoleMatchAnalysis,
    RoleMatchEvidence,
    RoleMatchOverride,
    RoleMatchRequirement,
)


def get_analysis(db: Session, analysis_id: int) -> RoleMatchAnalysis | None:
    return db.query(RoleMatchAnalysis).filter_by(id=analysis_id).first()


def _loads(raw: str | None, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def serialize_analysis(
    db: Session,
    analysis: RoleMatchAnalysis,
) -> RoleMatchAnalysisResponse:
    requirements = (
        db.query(RoleMatchRequirement)
        .filter_by(analysis_id=analysis.id)
        .order_by(
            RoleMatchRequirement.sort_order.asc(),
            RoleMatchRequirement.id.asc(),
        )
        .all()
    )
    requirement_ids = [item.id for item in requirements]
    evidence_rows = (
        db.query(RoleMatchEvidence)
        .filter(RoleMatchEvidence.requirement_id.in_(requirement_ids))
        .order_by(RoleMatchEvidence.rank.asc(), RoleMatchEvidence.id.asc())
        .all()
        if requirement_ids
        else []
    )
    evidence_by_requirement: dict[int, list[RoleMatchEvidence]] = defaultdict(list)
    for row in evidence_rows:
        evidence_by_requirement[row.requirement_id].append(row)

    requirement_payload = [
        RoleMatchRequirementResponse(
            id=item.id,
            cluster_id=item.cluster_id,
            canonical_key=item.canonical_key,
            canonical_text=item.canonical_text,
            primary_category=item.primary_category,
            importance=item.effective_importance,
            mention_count=item.mention_count,
            importance_conflict=bool(item.importance_conflict),
            source_quotes=_loads(item.source_quotes, []),
            excluded=bool(item.excluded),
            exclusion_reason=item.exclusion_reason,
            match_level=item.match_level,
            strength=item.strength,
            explanation=item.explanation,
            evidence=[
                RoleMatchEvidenceResponse(
                    id=evidence.id,
                    evidence_id=evidence.evidence_id,
                    source_type=evidence.source_type,
                    source_text=evidence.source_text,
                    relationship=evidence.relationship,
                    depth=evidence.depth,
                    duplicate=bool(evidence.duplicate),
                    contradiction=bool(evidence.contradiction),
                    explanation=evidence.explanation,
                )
                for evidence in evidence_by_requirement[item.id]
            ],
        )
        for item in requirements
    ]

    normalized = _loads(analysis.normalized_payload, {})
    scoring = _loads(analysis.scoring_payload, {})
    summary_raw = normalized.get("summary")
    summary = RoleMatchSummaryResponse(**summary_raw) if summary_raw else None
    category_breakdown = [
        RoleMatchCategoryResponse(**item)
        for item in (scoring.get("score") or {}).get("category_assessments", [])
    ]
    review_count = (
        db.query(RoleMatchOverride)
        .filter_by(analysis_id=analysis.id, carry_status="needs_review")
        .count()
    )
    return RoleMatchAnalysisResponse(
        id=analysis.id,
        parent_analysis_id=analysis.parent_analysis_id,
        created_at=analysis.created_at,
        state=analysis.state,
        score=analysis.display_score,
        score_band=analysis.score_band,
        confidence=analysis.confidence_band,
        eligibility=analysis.eligibility_status,
        show_authoritative_score=bool(analysis.show_authoritative_score),
        summary=summary,
        category_breakdown=category_breakdown,
        requirements=requirement_payload,
        excluded_items=_loads(analysis.excluded_items, []),
        override_review_count=review_count,
        rules_version=analysis.rules_version,
        prompt_version=analysis.prompt_version,
        failure_code=analysis.failure_code,
    )


def list_versions(
    db: Session,
    analysis: RoleMatchAnalysis,
) -> RoleMatchVersionsResponse:
    root = analysis
    seen: set[int] = set()
    while root.parent_analysis_id and root.id not in seen:
        seen.add(root.id)
        parent = get_analysis(db, root.parent_analysis_id)
        if parent is None:
            break
        root = parent
    items: list[RoleMatchAnalysis] = []
    frontier = [root]
    while frontier:
        current = frontier.pop(0)
        items.append(current)
        frontier.extend(
            db.query(RoleMatchAnalysis)
            .filter_by(parent_analysis_id=current.id)
            .order_by(RoleMatchAnalysis.created_at.asc())
            .all()
        )
    return RoleMatchVersionsResponse(
        items=[
            RoleMatchVersionItem(
                id=item.id,
                parent_analysis_id=item.parent_analysis_id,
                created_at=item.created_at,
                state=item.state,
                score=item.display_score,
                confidence=item.confidence_band,
                eligibility=item.eligibility_status,
                superseded_by_id=item.superseded_by_id,
            )
            for item in items
        ]
    )


def compare_analyses(
    db: Session,
    before: RoleMatchAnalysis,
    after: RoleMatchAnalysis,
) -> RoleMatchComparisonResponse:
    before_rows = {
        row.canonical_key: row
        for row in db.query(RoleMatchRequirement)
        .filter_by(analysis_id=before.id)
        .all()
    }
    after_rows = {
        row.canonical_key: row
        for row in db.query(RoleMatchRequirement)
        .filter_by(analysis_id=after.id)
        .all()
    }
    changed: list[dict[str, Any]] = []
    for key in sorted(before_rows.keys() & after_rows.keys()):
        left, right = before_rows[key], after_rows[key]
        fields = {}
        for field in (
            "effective_importance",
            "match_level",
            "strength",
            "excluded",
        ):
            left_value = getattr(left, field)
            right_value = getattr(right, field)
            if left_value != right_value:
                fields[field] = {"from": left_value, "to": right_value}
        if fields:
            changed.append({"canonical_key": key, "changes": fields})
    score_change = None
    if before.display_score is not None and after.display_score is not None:
        score_change = after.display_score - before.display_score
    return RoleMatchComparisonResponse(
        from_analysis_id=before.id,
        to_analysis_id=after.id,
        score_change=score_change,
        added_requirements=sorted(after_rows.keys() - before_rows.keys()),
        removed_requirements=sorted(before_rows.keys() - after_rows.keys()),
        changed_requirements=changed,
    )
