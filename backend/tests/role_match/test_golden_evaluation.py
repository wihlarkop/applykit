from pathlib import Path

import pytest

from tests.role_match.golden_harness import (
    GOLDEN_DIR,
    GoldenCase,
    assert_invariants,
    evaluate_normalized_case,
)


FIXTURES = sorted(GOLDEN_DIR.glob("*.json"))


def test_golden_suite_has_all_required_scenarios() -> None:
    assert {path.stem for path in FIXTURES} == {
        "duration_near_threshold",
        "eligibility_unclear",
        "equivalent_messaging",
        "fairness_invariance",
        "incomplete_profile",
        "keyword_stuffing",
        "model_variation",
        "non_job_related_requirement",
        "older_django_current_python",
        "overlapping_roles",
        "strong_python_backend",
        "tool_specific_kafka",
    }


@pytest.mark.parametrize("fixture_path", FIXTURES, ids=lambda path: path.stem)
def test_golden_role_match_case(fixture_path: Path) -> None:
    case = GoldenCase.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    result = evaluate_normalized_case(case)

    assert case.expected.display_score_min <= result.display_score <= (
        case.expected.display_score_max
    )
    assert result.score_band == case.expected.score_band
    assert result.confidence == case.expected.confidence
    assert result.eligibility == case.expected.eligibility
    assert result.show_authoritative_score is case.expected.show_authoritative_score
    assert_invariants(case, result)
