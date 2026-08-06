from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher

from app.role_match.constants import (
    AUTOMATIC_CLUSTER_SIMILARITY,
    CLUSTER_REVIEW_SIMILARITY,
)
from app.role_match.domain import (
    AtomicRequirement,
    ClusteringConflict,
    ClusteringResult,
    ClusteringReviewCandidate,
    RequirementCluster,
    RequirementImportance,
)

_IMPORTANCE_ORDER = {
    RequirementImportance.SUPPORTING: 0,
    RequirementImportance.IMPORTANT: 1,
    RequirementImportance.CRITICAL: 2,
}


def normalize_canonical_key(value: str) -> str:
    tokens = re.findall(r"[a-z0-9+#.]+", value.casefold())
    return "-".join(tokens)


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+#.]+", value.casefold()))


def requirement_similarity(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    jaccard = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
    sequence = SequenceMatcher(None, " ".join(sorted(left_tokens)), " ".join(sorted(right_tokens))).ratio()
    return (jaccard + sequence) / 2


def _compatible(left: AtomicRequirement, right: AtomicRequirement) -> bool:
    return (
        left.primary_category == right.primary_category
        and left.is_eligibility == right.is_eligibility
        and left.is_trainable == right.is_trainable
        and left.tool_specificity == right.tool_specificity
    )


def _build_cluster(key: str, items: list[AtomicRequirement]) -> RequirementCluster:
    importance_mentions = {importance: 0 for importance in RequirementImportance}
    for item in items:
        importance_mentions[item.importance] += 1
    importance = max((item.importance for item in items), key=_IMPORTANCE_ORDER.get)
    importance_conflict = sum(1 for count in importance_mentions.values() if count) > 1
    minimum_months_values = [item.minimum_months for item in items if item.minimum_months is not None]
    minimum_months = max(minimum_months_values) if minimum_months_values else None
    representative = items[0]
    return RequirementCluster(
        cluster_id=f"req:{key}",
        canonical_requirement=representative.text,
        canonical_key=key,
        primary_category=representative.primary_category,
        importance=importance,
        mention_count=len(items),
        importance_conflict=importance_conflict,
        importance_mentions=importance_mentions,
        source_quotes=[item.source_quote for item in items],
        source_ids=[item.source_id for item in items],
        is_eligibility=representative.is_eligibility,
        is_trainable=representative.is_trainable,
        volatility=representative.volatility,
        minimum_months=minimum_months,
        tool_specificity=representative.tool_specificity,
        excluded=all(item.excluded for item in items),
        exclusion_reason=next((item.exclusion_reason for item in items if item.exclusion_reason), None),
    )


def cluster_requirements(requirements: list[AtomicRequirement]) -> ClusteringResult:
    grouped: dict[str, list[AtomicRequirement]] = defaultdict(list)
    for requirement in requirements:
        key = normalize_canonical_key(requirement.canonical_key or requirement.text)
        grouped[key].append(requirement)

    clusters: list[RequirementCluster] = []
    conflicts: list[ClusteringConflict] = []
    pending: list[tuple[str, list[AtomicRequirement]]] = []

    for key, items in grouped.items():
        representative = items[0]
        if any(not _compatible(representative, item) for item in items[1:]):
            conflicts.append(
                ClusteringConflict(
                    canonical_key=key,
                    source_ids=[item.source_id for item in items],
                    reason="same_canonical_key_has_materially_different_classification",
                )
            )
            continue
        pending.append((key, items))

    review_candidates: list[ClusteringReviewCandidate] = []
    consumed: set[str] = set()
    for index, (key, items) in enumerate(pending):
        if key in consumed:
            continue
        combined = list(items)
        for other_key, other_items in pending[index + 1 :]:
            if other_key in consumed:
                continue
            similarity = requirement_similarity(
                " ".join(item.text for item in items),
                " ".join(item.text for item in other_items),
            )
            if similarity >= AUTOMATIC_CLUSTER_SIMILARITY and _compatible(items[0], other_items[0]):
                combined.extend(other_items)
                consumed.add(other_key)
            elif similarity >= CLUSTER_REVIEW_SIMILARITY:
                review_candidates.append(
                    ClusteringReviewCandidate(
                        left_key=key,
                        right_key=other_key,
                        similarity=round(similarity, 6),
                    )
                )
        clusters.append(_build_cluster(key, combined))

    return ClusteringResult(
        clusters=clusters,
        review_candidates=review_candidates,
        unresolved_conflicts=conflicts,
    )
