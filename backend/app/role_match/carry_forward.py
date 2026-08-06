from __future__ import annotations

from app.role_match.domain import (
    MatchLevel,
    OverrideCarryStatus,
    RequirementAssessment,
    RequirementCluster,
)
from app.role_match.overrides import (
    apply_carried_overrides_to_clusters,
    filter_carried_evidence_links,
    prepare_parent_overrides,
)
from app.role_match.snapshots import SnapshotOverride


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
