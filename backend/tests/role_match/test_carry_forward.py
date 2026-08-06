from app.role_match.domain import (
    MatchLevel,
    RequirementAssessment,
    RequirementCategory,
    RequirementCluster,
    RequirementImportance,
    TechnologyVolatility,
)
from app.role_match.overrides import (
    apply_carried_experience_overrides,
    apply_carried_overrides_to_clusters,
)
from app.role_match.snapshots import SnapshotOverride


def cluster() -> RequirementCluster:
    return RequirementCluster(
        cluster_id="req:terraform",
        canonical_requirement="Terraform experience",
        canonical_key="terraform",
        primary_category=RequirementCategory.RELEVANT_COMPETENCIES,
        importance=RequirementImportance.CRITICAL,
        mention_count=1,
        importance_conflict=False,
        importance_mentions={
            RequirementImportance.CRITICAL: 1,
            RequirementImportance.IMPORTANT: 0,
            RequirementImportance.SUPPORTING: 0,
        },
        source_quotes=["Terraform experience"],
        source_ids=["jd:terraform"],
        is_eligibility=False,
        is_trainable=False,
        volatility=TechnologyVolatility.EVOLVING,
        tool_specificity="capability",
    )


def assessment() -> RequirementAssessment:
    return RequirementAssessment(
        cluster_id="req:terraform",
        category=RequirementCategory.RELEVANT_COMPETENCIES,
        importance=RequirementImportance.CRITICAL,
        match_level=MatchLevel.WEAK,
        strength=0.3,
        known=True,
    )


def test_carried_importance_override_changes_new_cluster() -> None:
    result = apply_carried_overrides_to_clusters(
        [cluster()],
        (
            SnapshotOverride(
                requirement_key="terraform",
                field_name="importance",
                extracted_value="critical",
                effective_value="supporting",
                reason="Listed as preferred",
                source="carry_forward",
                carry_status="carried_forward",
            ),
        ),
    )
    assert result[0].importance == RequirementImportance.SUPPORTING


def test_needs_review_override_does_not_change_new_cluster() -> None:
    result = apply_carried_overrides_to_clusters(
        [cluster()],
        (
            SnapshotOverride(
                requirement_key="terraform",
                field_name="importance",
                extracted_value="critical",
                effective_value="supporting",
                reason="Old override",
                source="carry_forward",
                carry_status="needs_review",
            ),
        ),
    )
    assert result[0].importance == RequirementImportance.CRITICAL


def test_carried_no_experience_override_replaces_assessment() -> None:
    result = apply_carried_experience_overrides(
        [assessment()],
        [cluster()],
        (
            SnapshotOverride(
                requirement_key="terraform",
                field_name="experience_status",
                extracted_value="weak",
                effective_value="no_experience",
                reason="User confirmed no experience",
                source="carry_forward",
                carry_status="carried_forward",
            ),
        ),
    )
    assert result[0].match_level == MatchLevel.NO_EVIDENCE
    assert result[0].strength == 0.0
    assert result[0].known is True
