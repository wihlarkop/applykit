from app.role_match.clustering import cluster_requirements
from app.role_match.domain import (
    AtomicRequirement,
    RequirementCategory,
    RequirementImportance,
)


def atomic(
    text: str,
    key: str,
    importance: RequirementImportance = RequirementImportance.CRITICAL,
    category: RequirementCategory = RequirementCategory.RELEVANT_COMPETENCIES,
    source_id: str | None = None,
) -> AtomicRequirement:
    return AtomicRequirement(
        source_id=source_id or text.lower().replace(" ", "-")[:20],
        text=text,
        canonical_key=key,
        primary_category=category,
        importance=importance,
        source_quote=text,
    )


def test_repeated_requirement_becomes_one_cluster_with_count() -> None:
    result = cluster_requirements(
        [
            atomic("Strong Python experience", "python-backend", source_id="a"),
            atomic("Build backend services using Python", "python-backend", source_id="b"),
            atomic("Python proficiency is required", "python-backend", source_id="c"),
        ]
    )
    assert len(result.clusters) == 1
    cluster = result.clusters[0]
    assert cluster.mention_count == 3
    assert cluster.importance == RequirementImportance.CRITICAL
    assert cluster.importance_conflict is False
    assert len(cluster.source_quotes) == 3


def test_conflicting_importance_uses_highest_and_records_counts() -> None:
    cluster = cluster_requirements(
        [
            atomic("Python required", "python-backend", RequirementImportance.CRITICAL, source_id="a"),
            atomic("Python preferred", "python-backend", RequirementImportance.SUPPORTING, source_id="b"),
        ]
    ).clusters[0]
    assert cluster.importance == RequirementImportance.CRITICAL
    assert cluster.importance_conflict is True
    assert cluster.importance_mentions == {
        RequirementImportance.CRITICAL: 1,
        RequirementImportance.IMPORTANT: 0,
        RequirementImportance.SUPPORTING: 1,
    }


def test_same_cluster_key_with_different_primary_categories_requires_review() -> None:
    result = cluster_requirements(
        [
            atomic(
                "Python capability",
                "python-backend",
                category=RequirementCategory.RELEVANT_COMPETENCIES,
                source_id="a",
            ),
            atomic(
                "Build Python APIs",
                "python-backend",
                category=RequirementCategory.RELEVANT_WORK_TASKS,
                source_id="b",
            ),
        ]
    )
    assert result.unresolved_conflicts
    assert result.clusters == []
