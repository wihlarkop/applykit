import re

from app.role_match.domain import FairnessDecision

_EXCLUDE_PATTERNS = [
    re.compile(r"\b(under|below|younger than)\s+\d{2}\b", re.IGNORECASE),
    re.compile(r"\b(unmarried|single applicants?|marital status|married only)\b", re.IGNORECASE),
    re.compile(r"\b(male|female|man|woman)\s+(candidate|applicant)?\s*(preferred|required|only)?\b", re.IGNORECASE),
    re.compile(r"\b(recent|professional)?\s*photo(graph)?\b", re.IGNORECASE),
    re.compile(r"\b(religion|race|ethnicity)\b", re.IGNORECASE),
]
_CITIZENSHIP_PATTERN = re.compile(r"\b(citizen|citizenship|nationality)\b", re.IGNORECASE)
_LANGUAGE_PATTERN = re.compile(r"\b(language|fluency|fluent|speaking|speakers?)\b", re.IGNORECASE)
_TASK_REASON_PATTERN = re.compile(r"\b(customer|client|support|translate|translation|localization|work)\b", re.IGNORECASE)


def evaluate_requirement_fairness(requirement_text: str) -> FairnessDecision:
    text = requirement_text.strip()
    if any(pattern.search(text) for pattern in _EXCLUDE_PATTERNS):
        return FairnessDecision(
            excluded=True,
            action="exclude_warn_continue",
            reason="potentially_non_job_related",
        )
    if _CITIZENSHIP_PATTERN.search(text):
        return FairnessDecision(
            excluded=False,
            action="review",
            reason="citizenship_or_nationality_requires_job_related_review",
        )
    if _LANGUAGE_PATTERN.search(text) and _TASK_REASON_PATTERN.search(text):
        return FairnessDecision(
            excluded=False,
            action="include",
            reason="explicit_job_related_language_requirement",
        )
    return FairnessDecision(
        excluded=False,
        action="include",
        reason="no_fairness_exclusion_detected",
    )
