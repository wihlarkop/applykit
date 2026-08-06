from app.role_match.constants import (
    CATEGORY_WEIGHTS,
    CONFIDENCE_WEIGHTS,
    DISPLAY_RULES,
    IMPORTANCE_WEIGHTS,
)
from app.role_match.domain import (
    EvidenceRelationship,
    RequirementCategory,
    RequirementImportance,
)


def test_category_weights_sum_to_one() -> None:
    assert CATEGORY_WEIGHTS == {
        RequirementCategory.ESSENTIAL_QUALIFICATIONS: 0.30,
        RequirementCategory.RELEVANT_COMPETENCIES: 0.30,
        RequirementCategory.RELEVANT_WORK_TASKS: 0.25,
        RequirementCategory.PREFERRED_QUALIFICATIONS: 0.10,
        RequirementCategory.CONTEXTUAL_ALIGNMENT: 0.05,
    }
    assert sum(CATEGORY_WEIGHTS.values()) == 1.0


def test_fixed_importance_weights() -> None:
    assert IMPORTANCE_WEIGHTS == {
        RequirementImportance.CRITICAL: 1.00,
        RequirementImportance.IMPORTANT: 0.70,
        RequirementImportance.SUPPORTING: 0.40,
    }


def test_confidence_weights_are_fixed() -> None:
    assert CONFIDENCE_WEIGHTS == {
        "known_coverage": 0.45,
        "evidence_reliability": 0.35,
        "evidence_consistency": 0.20,
    }


def test_display_rules_match_approved_thresholds() -> None:
    assert DISPLAY_RULES.minimum_known_coverage == 0.60
    assert DISPLAY_RULES.minimum_confidence == 0.55
    assert DISPLAY_RULES.maximum_unresolved_conflict_rate == 0.20
    assert DISPLAY_RULES.minimum_atomic_requirements == 3


def test_relationship_values_are_stable() -> None:
    assert EvidenceRelationship.EXACT.value == "exact"
    assert EvidenceRelationship.FUNCTIONAL_EQUIVALENT.value == "functional_equivalent"
    assert EvidenceRelationship.ADJACENT.value == "adjacent"
    assert EvidenceRelationship.UNRELATED.value == "unrelated"
