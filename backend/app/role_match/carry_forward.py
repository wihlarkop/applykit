from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.role_match.carry_policy import classify_override_carry
from app.role_match.domain import (
    MatchLevel,
    OverrideCarryStatus,
    RequirementAssessment,
    RequirementCluster,
)
from app.role_match.models import RoleMatchOverride, RoleMatchRequirement
from app.role_match.overrides import (
    apply_carried_overrides_to_clusters,
    filter_carried_evidence_links,
)
from app.role_match.snapshots import SnapshotOverride


def _loads(raw: str | None, default: Any) -> Any:
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def prepare_parent_overrides(
    db: Session,
    parent_analysis_id: int | None,
    new_clusters: list[RequirementCluster],
) -> tuple[SnapshotOverride, ...]:
    if parent_analysis_id is None:
        return ()
    previous_requirements = {
        item.canonical_key: item
        for item in db.query(RoleMatchRequirement)
        .filter_by(analysis_id=parent_analysis_id)
        .all()
    }
    previous_overrides = (
        db.query(RoleMatchOverride)
        .filter_by(analysis_id=parent_analysis_id)
        .order_by(RoleMatchOverride.id.asc())
        .all()
    )
    prepared: list[SnapshotOverride] = []
    for item in previous_overrides:
        previous_requirement = previous_requirements.get(item.requirement_key)
        previous_category = (
            previous_requirement.primary_category
            if previous_requirement is not None
            else ""
        )
        status, target_key = classify_override_carry(
            previous_key=item.requirement_key,
            previous_category=previous_category,
            previous_status=item.carry_status,
            new_clusters=new_clusters,
        )
        prepared.append(
            SnapshotOverride(
                requirement_key=target_key or item.requirement_key,
                field_name=item.field_name,
                extracted_value=_loads(item.extracted_value, None),
                effective_value=_loads(item.effective_value, None),
                reason=item.reason,
                source="carry_forward",
                carry_status=status.value,
                source_override_id=item.id,
            )
        )
    return tuple(prepared)


def apply_carried_experience_overrides(
    assessments: list[RequirementAssessment],
    clusters: list[RequirementCluster],
    prepared: tuple[SnapshotOverride, ...],
) -> list[RequirementAssessment]:
    cluster_by_key = {item.canonical_key: item for item in clusters}
    assessment_by_cluster = {item.cluster_id: item for item in assessments}

    for item in prepared:
        if (
            item.carry_status != OverrideCarryStatus.CARRIED_FORWARD.value
            or item.field_name != "experience_status"
        ):
            continue
        cluster = cluster_by_key.get(item.requirement_key)
        if cluster is None or cluster.excluded:
            continue
        status = str(item.effective_value)
        if status == "no_experience":
            assessment_by_cluster[cluster.cluster_id] = RequirementAssessment(
                cluster_id=cluster.cluster_id,
                category=cluster.primary_category,
                importance=cluster.importance,
                match_level=MatchLevel.NO_EVIDENCE,
                strength=0.0,
                evidence_links=[],
                explanation="The user previously confirmed they do not have this experience.",
                known=True,
            )
        elif status == "not_in_profile":
            assessment_by_cluster[cluster.cluster_id] = RequirementAssessment(
                cluster_id=cluster.cluster_id,
                category=cluster.primary_category,
                importance=cluster.importance,
                match_level=MatchLevel.UNKNOWN,
                strength=None,
                evidence_links=[],
                explanation="The user previously indicated this evidence is not included in the profile.",
                known=False,
            )

    return [
        assessment_by_cluster[item.cluster_id]
        for item in clusters
        if not item.excluded and item.cluster_id in assessment_by_cluster
    ]


__all__ = [
    "apply_carried_experience_overrides",
    "apply_carried_overrides_to_clusters",
    "filter_carried_evidence_links",
    "prepare_parent_overrides",
]
