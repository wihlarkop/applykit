from __future__ import annotations

import re
from collections import Counter
from typing import Any
from urllib.parse import urlparse

from app.resume_readiness.constants import (
    BULLET_MAX_WORDS,
    BULLET_MIN_WORDS,
    SUMMARY_MAX_WORDS,
)
from app.resume_readiness.domain import Category, ExtractedDocument, RuleResult, Severity
from app.resume_readiness.normalization import normalize_text

_ACTION_VERBS = {
    "achieved",
    "automated",
    "built",
    "created",
    "delivered",
    "designed",
    "developed",
    "drove",
    "implemented",
    "improved",
    "increased",
    "launched",
    "led",
    "managed",
    "migrated",
    "optimized",
    "reduced",
    "resolved",
    "scaled",
    "shipped",
    "streamlined",
}
_RESULT_MARKERS = {
    "by",
    "resulting",
    "increased",
    "reduced",
    "improved",
    "saved",
    "faster",
    "lower",
    "higher",
    "%",
}
_GENERIC_PATTERNS = (
    "responsible for",
    "worked on",
    "helped with",
    "various tasks",
    "multiple projects",
)
_CURRENT_DATE_VALUES = {"present", "current", "now"}
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?%?\b")


def _all_bullets(snapshot: dict[str, Any]) -> list[tuple[str, str]]:
    bullets: list[tuple[str, str]] = []
    for experience_index, experience in enumerate(snapshot.get("work_experience") or []):
        for bullet_index, bullet in enumerate(experience.get("bullets") or []):
            if str(bullet).strip():
                bullets.append(
                    (
                        f"work_experience[{experience_index}].bullets[{bullet_index}]",
                        str(bullet).strip(),
                    )
                )
    return bullets


def _date_rank(value: str | None) -> tuple[int, int]:
    if not value:
        return (9999, 12)
    lowered = value.casefold()
    if lowered in _CURRENT_DATE_VALUES:
        return (9999, 12)
    match = _YEAR_RE.search(value)
    year = int(match.group()) if match else 0
    month = 0
    month_match = re.search(r"(?:^|[-/])(0?[1-9]|1[0-2])(?:$|[-/])", value)
    if month_match:
        month = int(month_match.group(1))
    return (year, month)


def _date_style(value: str | None) -> str | None:
    if not value:
        return None
    if value.casefold() in _CURRENT_DATE_VALUES:
        return None
    if "/" in value:
        return "slash"
    if "-" in value:
        return "hyphen"
    if re.search(r"[A-Za-z]", value):
        return "text"
    return "numeric"


def _valid_url(value: str | None) -> bool:
    if not value:
        return True
    parsed = urlparse(value if "://" in value else f"https://{value}")
    return bool(parsed.netloc and "." in parsed.netloc)


def evaluate_quality(
    snapshot: dict[str, Any],
    extracted: ExtractedDocument | None,
) -> list[RuleResult]:
    results: list[RuleResult] = []
    bullets = _all_bullets(snapshot)

    missing_identity = [field for field in ("name", "email") if not snapshot.get(field)]
    if missing_identity:
        results.append(
            RuleResult.fail(
                rule_id="QUALITY-001",
                category=Category.QUALITY,
                score_delta=-25,
                score_cap=55,
                title="Essential identity information is missing",
                explanation="A resume should include a name and email address.",
                evidence={"missing_fields": missing_identity},
            )
        )

    summary = str(snapshot.get("summary") or "").strip()
    summary_words = len(summary.split())
    if summary_words > SUMMARY_MAX_WORDS:
        results.append(
            RuleResult.warning(
                rule_id="QUALITY-002",
                category=Category.QUALITY,
                score_delta=-5,
                title="Professional summary is too long",
                explanation="The summary is longer than the configured readability guidance.",
                evidence={"word_count": summary_words, "limit": SUMMARY_MAX_WORDS},
            )
        )
    if not summary:
        results.append(
            RuleResult.warning(
                rule_id="QUALITY-003",
                category=Category.QUALITY,
                score_delta=-4,
                title="Professional summary is empty",
                explanation="A concise summary can help a reviewer understand the candidate quickly.",
            )
        )

    experiences = snapshot.get("work_experience") or []
    ranks = [_date_rank(item.get("start_date")) for item in experiences]
    if ranks and ranks != sorted(ranks, reverse=True):
        results.append(
            RuleResult.warning(
                rule_id="QUALITY-004",
                category=Category.QUALITY,
                score_delta=-6,
                title="Experience ordering is inconsistent",
                explanation="Experience entries are not ordered from most recent to oldest.",
                evidence={"start_dates": [item.get("start_date") for item in experiences]},
                severity=Severity.IMPORTANT,
            )
        )

    date_styles = {
        style
        for experience in experiences
        for value in (experience.get("start_date"), experience.get("end_date"))
        if (style := _date_style(value)) is not None
    }
    if len(date_styles) > 1:
        results.append(
            RuleResult.warning(
                rule_id="QUALITY-005",
                category=Category.QUALITY,
                score_delta=-4,
                title="Date formatting is inconsistent",
                explanation="Experience dates use multiple formatting styles.",
                evidence={"styles": sorted(date_styles)},
            )
        )

    long_locations = [
        location
        for location, bullet in bullets
        if len(bullet.split()) > BULLET_MAX_WORDS
    ]
    if long_locations:
        results.append(
            RuleResult.warning(
                rule_id="QUALITY-006",
                category=Category.QUALITY,
                score_delta=max(-10, -2 * len(long_locations)),
                title="Some bullets are difficult to scan",
                explanation="One or more bullets exceed the configured word guidance.",
                evidence={"count": len(long_locations), "limit": BULLET_MAX_WORDS},
                locations=tuple(long_locations),
            )
        )

    weak_locations = [
        location
        for location, bullet in bullets
        if len(bullet.split()) < BULLET_MIN_WORDS
        or any(pattern in bullet.casefold() for pattern in _GENERIC_PATTERNS)
    ]
    if weak_locations:
        results.append(
            RuleResult.warning(
                rule_id="QUALITY-007",
                category=Category.QUALITY,
                score_delta=max(-12, -3 * len(weak_locations)),
                title="Some bullets are too generic",
                explanation="Short or responsibility-only bullets provide little evidence of contribution.",
                evidence={"count": len(weak_locations)},
                locations=tuple(weak_locations),
            )
        )

    normalized_bullets = [
        (location, normalize_text(bullet)) for location, bullet in bullets
    ]
    counts = Counter(value for _, value in normalized_bullets if value)
    duplicate_values = {value for value, count in counts.items() if count > 1}
    duplicate_locations = [
        location for location, value in normalized_bullets if value in duplicate_values
    ]
    if duplicate_locations:
        results.append(
            RuleResult.warning(
                rule_id="QUALITY-008",
                category=Category.QUALITY,
                score_delta=-8,
                title="Duplicate bullet content detected",
                explanation="Repeated bullets reduce the amount of distinct evidence in the resume.",
                evidence={"duplicate_count": len(duplicate_locations)},
                locations=tuple(duplicate_locations),
                severity=Severity.IMPORTANT,
            )
        )

    action_missing: list[str] = []
    outcome_missing: list[str] = []
    for location, bullet in bullets:
        normalized = normalize_text(bullet)
        first_word = normalized.split(maxsplit=1)[0] if normalized else ""
        if first_word not in _ACTION_VERBS:
            action_missing.append(location)
        has_result = bool(_NUMBER_RE.search(bullet)) or any(
            marker in bullet.casefold() for marker in _RESULT_MARKERS
        )
        if first_word in _ACTION_VERBS and len(bullet.split()) >= 8 and not has_result:
            outcome_missing.append(location)

    if action_missing:
        results.append(
            RuleResult.warning(
                rule_id="QUALITY-009",
                category=Category.QUALITY,
                score_delta=max(-10, -2 * len(action_missing)),
                title="Some bullets lack a clear action",
                explanation="A direct action verb can make ownership easier to understand.",
                evidence={"count": len(action_missing)},
                locations=tuple(action_missing),
            )
        )

    if outcome_missing:
        results.append(
            RuleResult.warning(
                rule_id="QUALITY-010",
                category=Category.QUALITY,
                score_delta=max(-8, -1 * len(outcome_missing)),
                title="Some bullets do not explain the result",
                explanation="Where evidence exists, describing the outcome makes a contribution clearer.",
                evidence={"count": len(outcome_missing)},
                locations=tuple(outcome_missing),
            )
        )

    results.append(
        RuleResult.unknown(
            rule_id="QUALITY-011",
            category=Category.QUALITY,
            title="Quantified-claim provenance was not assessed",
            explanation="The MVP does not have a separate immutable pre-enhancement snapshot for comparison.",
        )
    )

    if extracted and extracted.page_count > 2:
        results.append(
            RuleResult.warning(
                rule_id="QUALITY-012",
                category=Category.QUALITY,
                score_delta=-4,
                title="Resume is longer than the default guidance",
                explanation="The generated resume exceeds two pages.",
                evidence={"page_count": extracted.page_count},
            )
        )

    if not experiences and not snapshot.get("education") and not snapshot.get("skills"):
        results.append(
            RuleResult.fail(
                rule_id="QUALITY-013",
                category=Category.QUALITY,
                score_delta=-20,
                score_cap=59,
                title="Core resume sections are empty",
                explanation="The resume does not contain experience, education, or skills.",
                severity=Severity.IMPORTANT,
            )
        )

    malformed_links = [
        field
        for field in ("linkedin", "github", "portfolio")
        if not _valid_url(snapshot.get(field))
    ]
    if malformed_links:
        results.append(
            RuleResult.warning(
                rule_id="QUALITY-014",
                category=Category.QUALITY,
                score_delta=-3,
                title="Professional links are malformed",
                explanation="One or more professional links cannot be parsed as valid URLs.",
                evidence={"fields": malformed_links},
            )
        )

    ending_styles = {
        "period" if bullet.rstrip().endswith(".") else "none"
        for _, bullet in bullets
        if bullet.strip()
    }
    if len(ending_styles) > 1:
        results.append(
            RuleResult.warning(
                rule_id="QUALITY-015",
                category=Category.QUALITY,
                score_delta=-3,
                title="Bullet punctuation is inconsistent",
                explanation="Some bullets end with punctuation while others do not.",
                evidence={"styles": sorted(ending_styles)},
            )
        )

    return results
