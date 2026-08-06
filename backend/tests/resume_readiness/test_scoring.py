from app.resume_readiness.domain import (
    AnalysisMode,
    Category,
    OverallResult,
    RuleResult,
)
from app.resume_readiness.scoring import (
    calculate_category_score,
    calculate_overall_result,
)


def test_category_score_applies_lowest_cap():
    rules = [
        RuleResult.fail(
            rule_id="PARSE-004",
            category=Category.PARSEABILITY,
            score_delta=-15,
            score_cap=60,
            title="Email was not extracted",
            explanation="The source contains an email but extraction does not.",
            evidence={"source": "user@example.com"},
        ),
        RuleResult.warning(
            rule_id="PARSE-013",
            category=Category.PARSEABILITY,
            score_delta=-5,
            title="Extraction coverage is partial",
            explanation="Coverage is between 70 and 85 percent.",
            evidence={"coverage": 0.8},
        ),
    ]

    result = calculate_category_score(Category.PARSEABILITY, rules)

    assert result.raw_score == 80
    assert result.score == 60
    assert result.band == "needs_improvement"


def test_job_specific_weights_are_deterministic():
    result = calculate_overall_result(
        mode=AnalysisMode.JOB_SPECIFIC,
        parseability_score=90,
        quality_score=80,
        tailoring_score=70,
        hard_gate=None,
    )

    assert result.score == 81
    assert result.band == "good"


def test_general_mode_excludes_tailoring():
    result = calculate_overall_result(
        mode=AnalysisMode.GENERAL,
        parseability_score=90,
        quality_score=80,
        tailoring_score=None,
        hard_gate=None,
    )

    assert result.score == 86
    assert result.band == "good"


def test_operational_failure_has_no_score():
    result = OverallResult.failed("PDF_PARSE_FAILED")

    assert result.status == "failed"
    assert result.score is None
    assert result.band is None
