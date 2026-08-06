from app.role_match.domain import AnalysisInsight, AnalysisSummary

_HEADLINES = {
    "exceptional_evidence_match": "Your profile is an exceptional match",
    "strong_evidence_match": "Your profile is a strong match",
    "moderate_evidence_match": "Your profile is a moderate match",
    "limited_evidence_match": "Your profile has limited alignment",
    "weak_evidence_match": "Your profile is not yet a strong match",
}
_DESCRIPTIONS = {
    "exceptional_evidence_match": "Your background strongly supports nearly all important requirements for this role.",
    "strong_evidence_match": "Your background supports most of the role's important requirements. A few areas need clearer evidence, but they do not outweigh your core strengths.",
    "moderate_evidence_match": "You meet several important requirements, while some meaningful gaps deserve attention before applying.",
    "limited_evidence_match": "There is relevant experience, but several core requirements need stronger evidence.",
    "weak_evidence_match": "The current profile does not show enough support for the role's most important requirements.",
}


def present_analysis(
    *,
    display_score: int,
    score_band: str,
    strengths: list[AnalysisInsight],
    concerns: list[AnalysisInsight],
) -> AnalysisSummary:
    del display_score
    if concerns:
        next_step = concerns[0].explanation
    elif strengths:
        next_step = "Use the strongest evidence in your tailored CV and cover letter."
    else:
        next_step = "Review the extracted requirements and add truthful profile evidence where it is missing."
    return AnalysisSummary(
        headline=_HEADLINES[score_band],
        description=_DESCRIPTIONS[score_band],
        strengths=strengths,
        concerns=concerns,
        next_step=next_step,
    )
