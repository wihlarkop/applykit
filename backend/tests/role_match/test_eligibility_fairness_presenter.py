import pytest

from app.role_match.domain import (
    AnalysisInsight,
    EligibilitySignal,
    EligibilityStatus,
    FairnessDecision,
)
from app.role_match.eligibility import assess_eligibility
from app.role_match.fairness import evaluate_requirement_fairness
from app.role_match.presenter import present_analysis


def test_missing_work_authorization_is_unclear_not_ineligible() -> None:
    result = assess_eligibility(
        [
            EligibilitySignal(
                requirement_id="work-auth",
                mandatory=True,
                unknown=True,
                reason="Work authorization is not stated",
            )
        ]
    )
    assert result.status == EligibilityStatus.UNCLEAR


def test_explicit_contradiction_can_be_ineligible() -> None:
    result = assess_eligibility(
        [
            EligibilitySignal(
                requirement_id="sponsorship",
                mandatory=True,
                explicit_contradiction=True,
                unknown=False,
                reason="Candidate requires sponsorship but none is available",
            )
        ]
    )
    assert result.status == EligibilityStatus.INELIGIBLE


def test_no_eligibility_requirements_is_likely_eligible() -> None:
    assert assess_eligibility([]).status == EligibilityStatus.LIKELY_ELIGIBLE


@pytest.mark.parametrize(
    "requirement_text",
    [
        "Candidate must be under 30",
        "Only unmarried applicants",
        "Female candidate preferred",
        "Include a recent photo",
    ],
)
def test_non_job_related_requirement_is_excluded(requirement_text: str) -> None:
    decision = evaluate_requirement_fairness(requirement_text)
    assert decision == FairnessDecision(
        excluded=True,
        action="exclude_warn_continue",
        reason="potentially_non_job_related",
    )


def test_job_related_language_requirement_is_not_excluded() -> None:
    decision = evaluate_requirement_fairness(
        "Japanese fluency is required to support Japanese-speaking customers"
    )
    assert decision.excluded is False
    assert decision.action == "include"


def test_nationality_requirement_needs_review_not_proxy_scoring() -> None:
    decision = evaluate_requirement_fairness("Applicant must be a Japanese citizen")
    assert decision.excluded is False
    assert decision.action == "review"


def test_presenter_uses_human_friendly_language() -> None:
    summary = present_analysis(
        display_score=80,
        score_band="strong_evidence_match",
        strengths=[
            AnalysisInsight(
                title="Strong production Python backend experience",
                explanation="Supported by recent work examples.",
                evidence_label="Work experience",
            )
        ],
        concerns=[
            AnalysisInsight(
                title="Terraform experience needs clearer proof",
                explanation="Add a real work example if available.",
                evidence_label="Preferred skill",
            )
        ],
    )
    assert summary.headline == "Your profile is a strong match"
    assert summary.concerns[0].title == "Terraform experience needs clearer proof"
    serialized = summary.model_dump_json()
    for forbidden in ["raw_score", "soft cap", "unsupported essential", "contradictory evidence"]:
        assert forbidden not in serialized
