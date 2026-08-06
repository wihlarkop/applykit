from __future__ import annotations

from app.role_match.clustering import requirement_similarity
from app.role_match.constants import (
    AUTOMATIC_OVERRIDE_CARRY_SIMILARITY,
    OVERRIDE_REVIEW_SIMILARITY,
)
from app.role_match.domain import OverrideCarryStatus, RequirementCluster


def _best_similarity_target(
    previous_key: str,
    new_clusters: list[RequirementCluster],
) -> tuple[float, RequirementCluster | None]:
    if not new_clusters:
        return 0.0, None
    return max(
        (
            requirement_similarity(
                previous_key.replace("-", " "),
                f"{cluster.canonical_key.replace('-', ' ')} "
                f"{cluster.canonical_requirement}",
            ),
            cluster,
        )
        for cluster in new_clusters
    )


def classify_override_carry(
    *,
    previous_key: str,
    previous_category: str,
    new_clusters: list[RequirementCluster],
    previous_status: str = OverrideCarryStatus.CARRIED_FORWARD.value,
) -> tuple[OverrideCarryStatus, str | None]:
    if previous_status == OverrideCarryStatus.NOT_APPLICABLE.value:
        return OverrideCarryStatus.NOT_APPLICABLE, None

    exact = next(
        (cluster for cluster in new_clusters if cluster.canonical_key == previous_key),
        None,
    )

    if previous_status == OverrideCarryStatus.NEEDS_REVIEW.value:
        if exact is not None:
            return OverrideCarryStatus.NEEDS_REVIEW, exact.canonical_key
        similarity, target = _best_similarity_target(previous_key, new_clusters)
        if target is not None and similarity >= OVERRIDE_REVIEW_SIMILARITY:
            return OverrideCarryStatus.NEEDS_REVIEW, target.canonical_key
        return OverrideCarryStatus.NOT_APPLICABLE, None

    if exact is not None:
        if exact.primary_category.value == previous_category:
            return OverrideCarryStatus.CARRIED_FORWARD, exact.canonical_key
        return OverrideCarryStatus.NEEDS_REVIEW, exact.canonical_key

    similarity, target = _best_similarity_target(previous_key, new_clusters)
    if target is None:
        return OverrideCarryStatus.NOT_APPLICABLE, None
    if (
        similarity >= AUTOMATIC_OVERRIDE_CARRY_SIMILARITY
        and target.primary_category.value == previous_category
    ):
        return OverrideCarryStatus.CARRIED_FORWARD, target.canonical_key
    if similarity >= OVERRIDE_REVIEW_SIMILARITY:
        return OverrideCarryStatus.NEEDS_REVIEW, target.canonical_key
    return OverrideCarryStatus.NOT_APPLICABLE, None
