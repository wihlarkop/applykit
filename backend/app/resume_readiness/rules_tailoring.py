from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from app.resume_readiness.constants import KEYWORD_REPETITION_THRESHOLD
from app.resume_readiness.domain import Category, RuleResult, Severity
from app.resume_readiness.normalization import normalize_text

_SUPPORTED_LEVELS = {"strong", "moderate", "weak"}
_STRONG_LEVELS = {"strong", "moderate"}
_UNSUPPORTED_LEVELS = {"no_evidence", "contradictory_evidence"}


def _to_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    raise TypeError("role_match must be a mapping or Pydantic model")


def _flatten_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        values: list[str] = []
        for nested in value.values():
            values.extend(_flatten_strings(nested))
        return values
    if isinstance(value, (list, tuple, set)):
        values = []
        for nested in value:
            values.extend(_flatten_strings(nested))
        return values
    return []


def _snapshot_text(snapshot: dict[str, Any]) -> str:
    return normalize_text(" ".join(_flatten_strings(snapshot)))


def _requirement_term(requirement: Mapping[str, Any]) -> str:
    return str(
        requirement.get("canonical_text")
        or requirement.get("canonical_term")
        or requirement.get("canonical_key")
        or requirement.get("text")
        or ""
    ).strip()


def _importance(requirement: Mapping[str, Any]) -> str:
    return str(requirement.get("importance") or "supporting")


def _match_level(requirement: Mapping[str, Any]) -> str:
    return str(requirement.get("match_level") or requirement.get("status") or "unknown")


def _category(requirement: Mapping[str, Any]) -> str:
    return str(requirement.get("primary_category") or requirement.get("category") or "unknown")


def evaluate_tailoring(
    snapshot: dict[str, Any],
    job_snapshot: str | None,
    role_match: Mapping[str, Any] | Any | None,
) -> list[RuleResult]:
    if not job_snapshot:
        return [
            RuleResult.excluded(
                rule_id="TAILOR-009",
                category=Category.TAILORING,
                title="Job Tailoring was not assessed",
                explanation="No target job description was supplied.",
            )
        ]

    if len(normalize_text(job_snapshot)) < 80:
        return [
            RuleResult.warning(
                rule_id="TAILOR-010",
                category=Category.TAILORING,
                score_delta=-10,
                score_cap=60,
                title="Job description is too incomplete for reliable tailoring",
                explanation="The target job text is too short to support a complete tailoring assessment.",
                evidence={"character_count": len(job_snapshot.strip())},
                severity=Severity.IMPORTANT,
                requires_review=True,
            )
        ]

    if role_match is None:
        return [
            RuleResult.warning(
                rule_id="TAILOR-008",
                category=Category.TAILORING,
                score_delta=-10,
                score_cap=60,
                title="Role Evidence Match is unavailable",
                explanation="Job Tailoring needs a compatible evidence analysis to avoid unsupported keyword advice.",
                severity=Severity.IMPORTANT,
                requires_review=True,
            )
        ]

    match = _to_mapping(role_match)
    state = str(match.get("state") or "success")
    authoritative = bool(match.get("show_authoritative_score", state == "success"))
    if state != "success" or not authoritative:
        return [
            RuleResult.warning(
                rule_id="TAILOR-008",
                category=Category.TAILORING,
                score_delta=-10,
                score_cap=60,
                title="Role Evidence Match needs review",
                explanation="The referenced role analysis is not authoritative enough for tailoring.",
                evidence={"state": state},
                severity=Severity.IMPORTANT,
                requires_review=True,
            )
        ]

    requirements = [
        item
        for item in (match.get("requirements") or [])
        if not bool(_to_mapping(item).get("excluded"))
    ]
    resume_text = _snapshot_text(snapshot)
    results: list[RuleResult] = []

    missing_critical: list[dict[str, Any]] = []
    missing_supported: list[dict[str, Any]] = []
    unsupported_present: list[dict[str, Any]] = []
    supported_categories: Counter[str] = Counter()
    covered_categories: Counter[str] = Counter()

    for raw_requirement in requirements:
        requirement = _to_mapping(raw_requirement)
        term = _requirement_term(requirement)
        normalized_term = normalize_text(term)
        if not normalized_term:
            continue
        level = _match_level(requirement)
        importance = _importance(requirement)
        category = _category(requirement)
        present = normalized_term in resume_text

        if level in _SUPPORTED_LEVELS:
            supported_categories[category] += 1
            if present:
                covered_categories[category] += 1
            elif level in _STRONG_LEVELS and importance == "critical":
                missing_critical.append(
                    {
                        "term": term,
                        "importance": importance,
                        "match_level": level,
                        "category": category,
                    }
                )
            else:
                missing_supported.append(
                    {
                        "term": term,
                        "importance": importance,
                        "match_level": level,
                        "category": category,
                    }
                )
        elif level in _UNSUPPORTED_LEVELS and present:
            unsupported_present.append(
                {
                    "term": term,
                    "match_level": level,
                    "category": category,
                }
            )

    if missing_critical:
        results.append(
            RuleResult.fail(
                rule_id="TAILOR-001",
                category=Category.TAILORING,
                score_delta=max(-24, -8 * len(missing_critical)),
                title="Supported essential evidence is missing from the resume",
                explanation="The profile strongly supports important requirements that the resume does not surface.",
                evidence={"requirements": missing_critical},
                severity=Severity.IMPORTANT,
            )
        )

    if missing_supported:
        results.append(
            RuleResult.warning(
                rule_id="TAILOR-002",
                category=Category.TAILORING,
                score_delta=max(-12, -3 * len(missing_supported)),
                title="Supported requirements could be represented more clearly",
                explanation="Some supported preferred or lower-priority requirements are absent from the resume.",
                evidence={"requirements": missing_supported},
            )
        )

    missing_terms = [item["term"] for item in missing_critical + missing_supported]
    if missing_terms:
        results.append(
            RuleResult.warning(
                rule_id="TAILOR-003",
                category=Category.TAILORING,
                score_delta=max(-8, -1 * len(missing_terms)),
                title="Relevant supported terminology is absent",
                explanation="Use supported job terminology where it accurately describes existing evidence.",
                evidence={"terms": missing_terms},
            )
        )

    if unsupported_present:
        results.append(
            RuleResult.fail(
                rule_id="TAILOR-004",
                category=Category.TAILORING,
                score_delta=max(-30, -15 * len(unsupported_present)),
                score_cap=60,
                title="Resume includes unsupported job terminology",
                explanation="Terms appear in the resume even though the role analysis found no supporting profile evidence.",
                evidence={"requirements": unsupported_present},
            )
        )

    repeated_terms: list[dict[str, Any]] = []
    for raw_requirement in requirements:
        requirement = _to_mapping(raw_requirement)
        term = _requirement_term(requirement)
        normalized_term = normalize_text(term)
        if not normalized_term:
            continue
        count = resume_text.count(normalized_term)
        if count > KEYWORD_REPETITION_THRESHOLD:
            repeated_terms.append({"term": term, "count": count})
    if repeated_terms:
        results.append(
            RuleResult.warning(
                rule_id="TAILOR-005",
                category=Category.TAILORING,
                score_delta=max(-10, -5 * len(repeated_terms)),
                title="Potential keyword stuffing detected",
                explanation="Repeated terminology should be supported by distinct evidence rather than repetition alone.",
                evidence={"terms": repeated_terms},
                severity=Severity.IMPORTANT,
            )
        )

    if missing_critical:
        results.append(
            RuleResult.warning(
                rule_id="TAILOR-006",
                category=Category.TAILORING,
                score_delta=-4,
                title="Important supported evidence is under-emphasized",
                explanation="Recent or strong evidence should be easier to find in the tailored resume.",
                evidence={"requirements": missing_critical},
                severity=Severity.IMPORTANT,
            )
        )

    represented = [category for category, count in covered_categories.items() if count > 0]
    if len(supported_categories) >= 3 and len(represented) <= 1:
        results.append(
            RuleResult.warning(
                rule_id="TAILOR-007",
                category=Category.TAILORING,
                score_delta=-6,
                title="Tailoring coverage is concentrated in one area",
                explanation="The resume represents supported evidence from too few requirement categories.",
                evidence={
                    "supported_categories": dict(supported_categories),
                    "covered_categories": dict(covered_categories),
                },
            )
        )

    if not results:
        results.append(
            RuleResult.passed(
                rule_id="TAILOR-003",
                category=Category.TAILORING,
                title="Supported job terminology is represented",
                explanation="The resume surfaces the supported requirements found in the target role.",
            )
        )

    return results
