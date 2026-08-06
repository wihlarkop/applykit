from app.role_match.domain import (
    EligibilityAssessment,
    EligibilitySignal,
    EligibilityStatus,
)


def assess_eligibility(signals: list[EligibilitySignal]) -> EligibilityAssessment:
    mandatory = [signal for signal in signals if signal.mandatory]
    if not mandatory:
        return EligibilityAssessment(status=EligibilityStatus.LIKELY_ELIGIBLE)
    explicit = [signal for signal in mandatory if signal.explicit_contradiction]
    if explicit:
        return EligibilityAssessment(
            status=EligibilityStatus.INELIGIBLE,
            reasons=[signal.reason for signal in explicit if signal.reason],
        )
    likely = [signal for signal in mandatory if signal.likely_contradiction]
    if likely:
        return EligibilityAssessment(
            status=EligibilityStatus.LIKELY_INELIGIBLE,
            reasons=[signal.reason for signal in likely if signal.reason],
        )
    unknown = [signal for signal in mandatory if signal.unknown]
    if unknown:
        return EligibilityAssessment(
            status=EligibilityStatus.UNCLEAR,
            reasons=[signal.reason for signal in unknown if signal.reason],
        )
    if all(signal.explicit_support for signal in mandatory):
        return EligibilityAssessment(status=EligibilityStatus.ELIGIBLE)
    return EligibilityAssessment(status=EligibilityStatus.LIKELY_ELIGIBLE)
