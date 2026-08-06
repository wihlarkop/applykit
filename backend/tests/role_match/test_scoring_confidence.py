import pytest

from app.role_match.confidence import calculate_confidence, decide_authoritative_display
from app.role_match.domain import (
    ConfidenceBand,
    ConfidenceInputs,
    MatchLevel,
    RequirementAssessment,
    RequirementCategory,
    RequirementImportance,
)
from app.role_match.scoring import (
    essential_score_cap,
    round_to_nearest_five,
    score_band,
    score_category,
    score_role_match,
    shrink_toward_neutral,
    weighted_overall_score,
)


def assessment(category, importance, level, strength=None) -> RequirementAssessment:
    return RequirementAssessment(
        cluster_id=f"{category.value}:{importance.value}:{level.value}",
        category=category,
        importance=importance,
        match_level=level,
        strength=strength,
        known=level != MatchLevel.UNKNOWN,
    )


def test_unknown_weight_shrinks_known_score_toward_neutral() -> None:
    assert shrink_toward_neutral(0.80, 0.80, 0.20) == pytest.approx(0.74)


def test_category_scoring_uses_importance_and_unknown_coverage() -> None:
    result = score_category(
        RequirementCategory.RELEVANT_COMPETENCIES,
        [
            assessment(
                RequirementCategory.RELEVANT_COMPETENCIES,
                RequirementImportance.CRITICAL,
                MatchLevel.STRONG,
                0.80,
            ),
            assessment(
                RequirementCategory.RELEVANT_COMPETENCIES,
                RequirementImportance.IMPORTANT,
                MatchLevel.UNKNOWN,
                None,
            ),
        ],
    )
    assert result.known_coverage == pytest.approx(1 / 1.7)
    assert result.unknown_coverage == pytest.approx(0.7 / 1.7)
    assert result.known_match == pytest.approx(0.80)
    assert result.score == pytest.approx(0.6764705882)


def test_category_weights_produce_raw_score() -> None:
    categories = {
        RequirementCategory.ESSENTIAL_QUALIFICATIONS: 0.80,
        RequirementCategory.RELEVANT_COMPETENCIES: 0.90,
        RequirementCategory.RELEVANT_WORK_TASKS: 0.70,
        RequirementCategory.PREFERRED_QUALIFICATIONS: 0.60,
        RequirementCategory.CONTEXTUAL_ALIGNMENT: 0.50,
    }
    assert weighted_overall_score(categories) == pytest.approx(0.77)


@pytest.mark.parametrize(
    ("unsupported", "unknown", "expected_cap"),
    [
        (0, 0, None),
        (1, 0, 74),
        (2, 0, 59),
        (3, 0, 44),
        (0, 1, 89),
        (0, 2, 79),
        (0, 3, 69),
        (1, 1, 74),
    ],
)
def test_essential_caps(unsupported, unknown, expected_cap) -> None:
    assert essential_score_cap(unsupported, unknown) == expected_cap


def test_display_rounding_and_band() -> None:
    assert round_to_nearest_five(82.4) == 80
    assert round_to_nearest_five(82.5) == 85
    assert score_band(85) == "exceptional_evidence_match"
    assert score_band(80) == "strong_evidence_match"


def test_score_role_match_applies_essential_cap() -> None:
    result = score_role_match(
        [
            assessment(
                RequirementCategory.ESSENTIAL_QUALIFICATIONS,
                RequirementImportance.CRITICAL,
                MatchLevel.NO_EVIDENCE,
                0.0,
            ),
            assessment(
                RequirementCategory.RELEVANT_COMPETENCIES,
                RequirementImportance.CRITICAL,
                MatchLevel.STRONG,
                1.0,
            ),
            assessment(
                RequirementCategory.RELEVANT_WORK_TASKS,
                RequirementImportance.CRITICAL,
                MatchLevel.STRONG,
                1.0,
            ),
            assessment(
                RequirementCategory.PREFERRED_QUALIFICATIONS,
                RequirementImportance.CRITICAL,
                MatchLevel.STRONG,
                1.0,
            ),
            assessment(
                RequirementCategory.CONTEXTUAL_ALIGNMENT,
                RequirementImportance.CRITICAL,
                MatchLevel.STRONG,
                1.0,
            ),
        ]
    )
    assert result.applied_cap == 74
    assert result.display_score <= 74


def test_confidence_formula() -> None:
    result = calculate_confidence(
        ConfidenceInputs(
            known_coverage=0.80,
            evidence_reliability=0.90,
            evidence_consistency=0.70,
        )
    )
    assert result.score == pytest.approx(0.815)
    assert result.band == ConfidenceBand.HIGH


def test_low_coverage_hides_authoritative_score() -> None:
    decision = decide_authoritative_display(
        known_coverage=0.59,
        confidence=0.80,
        conflict_rate=0.0,
        requirement_count=10,
        scoring_succeeded=True,
    )
    assert decision.show_score is False
    assert decision.reason == "insufficient_known_coverage"


def test_medium_confidence_is_enough_to_show_score() -> None:
    decision = decide_authoritative_display(
        known_coverage=0.70,
        confidence=0.55,
        conflict_rate=0.10,
        requirement_count=3,
        scoring_succeeded=True,
    )
    assert decision.show_score is True
