from app.role_match.constants import CONFIDENCE_WEIGHTS, DISPLAY_RULES
from app.role_match.domain import (
    ConfidenceAssessment,
    ConfidenceBand,
    ConfidenceInputs,
    DisplayDecision,
)


def calculate_confidence(inputs: ConfidenceInputs) -> ConfidenceAssessment:
    score = (
        inputs.known_coverage * CONFIDENCE_WEIGHTS["known_coverage"]
        + inputs.evidence_reliability * CONFIDENCE_WEIGHTS["evidence_reliability"]
        + inputs.evidence_consistency * CONFIDENCE_WEIGHTS["evidence_consistency"]
    )
    if score >= 0.80:
        band = ConfidenceBand.HIGH
        explanation = "Based on several direct and consistent examples from the profile."
    elif score >= 0.55:
        band = ConfidenceBand.MEDIUM
        explanation = "Some important requirements rely on indirect or incomplete evidence."
    else:
        band = ConfidenceBand.LOW
        explanation = "Too much information is missing or inconsistent for a confident assessment."
    return ConfidenceAssessment(score=score, band=band, explanation=explanation)


def decide_authoritative_display(
    *,
    known_coverage: float,
    confidence: float,
    conflict_rate: float,
    requirement_count: int,
    scoring_succeeded: bool,
) -> DisplayDecision:
    if not scoring_succeeded:
        return DisplayDecision(show_score=False, reason="scoring_failed")
    if requirement_count < DISPLAY_RULES.minimum_atomic_requirements:
        return DisplayDecision(show_score=False, reason="insufficient_requirements")
    if known_coverage < DISPLAY_RULES.minimum_known_coverage:
        return DisplayDecision(show_score=False, reason="insufficient_known_coverage")
    if confidence < DISPLAY_RULES.minimum_confidence:
        return DisplayDecision(show_score=False, reason="low_confidence")
    if conflict_rate > DISPLAY_RULES.maximum_unresolved_conflict_rate:
        return DisplayDecision(show_score=False, reason="too_many_unresolved_conflicts")
    return DisplayDecision(show_score=True)
