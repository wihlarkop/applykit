from app.role_match.carry_policy import classify_override_carry
from app.role_match.domain import (
    OverrideCarryStatus,
    RequirementCategory,
    RequirementCluster,
    RequirementImportance,
    TechnologyVolatility,
)


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


def test_unconfirmed_override_stays_needs_review_even_on_exact_match() -> None:
    status, target = classify_override_carry(
        previous_key="terraform",
        previous_category="relevant_competencies",
        previous_status="needs_review",
        new_clusters=[cluster()],
    )
    assert status == OverrideCarryStatus.NEEDS_REVIEW
    assert target == "terraform"


def test_not_applicable_override_remains_inactive() -> None:
    status, target = classify_override_carry(
        previous_key="terraform",
        previous_category="relevant_competencies",
        previous_status="not_applicable",
        new_clusters=[cluster()],
    )
    assert status == OverrideCarryStatus.NOT_APPLICABLE
    assert target is None
