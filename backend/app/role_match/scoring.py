from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.role_match.constants import (
    CATEGORY_WEIGHTS,
    IMPORTANCE_WEIGHTS,
    UNKNOWN_ESSENTIAL_CAPS,
    UNSUPPORTED_ESSENTIAL_CAPS,
)
from app.role_match.domain import (
    CategoryAssessment,
    MatchLevel,
    RequirementAssessment,
    RequirementCategory,
    ScoreResult,
)


def shrink_toward_neutral(
    known_match: float,
    known_coverage: float,
    unknown_coverage: float,
) -> float:
    return known_match * known_coverage + 0.50 * unknown_coverage


def score_category(
    category: RequirementCategory,
    assessments: list[RequirementAssessment],
) -> CategoryAssessment:
    relevant = [item for item in assessments if item.category == category]
    if not relevant:
        return CategoryAssessment(
            category=category,
            score=0.50,
            known_coverage=0.0,
            unknown_coverage=1.0,
            known_match=0.50,
            requirement_count=0,
        )
    total_weight = sum(IMPORTANCE_WEIGHTS[item.importance] for item in relevant)
    known = [item for item in relevant if item.known and item.strength is not None]
    known_weight = sum(IMPORTANCE_WEIGHTS[item.importance] for item in known)
    unknown_weight = total_weight - known_weight
    known_coverage = known_weight / total_weight if total_weight else 0.0
    unknown_coverage = unknown_weight / total_weight if total_weight else 1.0
    if known_weight:
        known_match = sum(
            (item.strength or 0.0) * IMPORTANCE_WEIGHTS[item.importance]
            for item in known
        ) / known_weight
    else:
        known_match = 0.50
    score = shrink_toward_neutral(known_match, known_coverage, unknown_coverage)
    return CategoryAssessment(
        category=category,
        score=max(0.0, min(score, 1.0)),
        known_coverage=known_coverage,
        unknown_coverage=unknown_coverage,
        known_match=max(0.0, min(known_match, 1.0)),
        requirement_count=len(relevant),
    )


def weighted_overall_score(categories: dict[RequirementCategory, float]) -> float:
    return sum(categories[category] * weight for category, weight in CATEGORY_WEIGHTS.items())


def _cap_for_count(caps: dict[int, int], count: int) -> int | None:
    if count <= 0:
        return None
    return caps[min(count, max(caps))]


def essential_score_cap(unsupported_count: int, unknown_count: int) -> int | None:
    candidates = [
        value
        for value in (
            _cap_for_count(UNSUPPORTED_ESSENTIAL_CAPS, unsupported_count),
            _cap_for_count(UNKNOWN_ESSENTIAL_CAPS, unknown_count),
        )
        if value is not None
    ]
    return min(candidates) if candidates else None


def round_to_nearest_five(value: float) -> int:
    rounded = (Decimal(str(value)) / Decimal("5")).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ) * Decimal("5")
    return int(max(Decimal("0"), min(rounded, Decimal("100"))))


def _display_cap(cap: int) -> int:
    """Convert an internal cap to the highest allowed five-point display value."""
    return max(0, min(100, (cap // 5) * 5))


def score_band(display_score: int) -> str:
    if display_score >= 85:
        return "exceptional_evidence_match"
    if display_score >= 70:
        return "strong_evidence_match"
    if display_score >= 55:
        return "moderate_evidence_match"
    if display_score >= 40:
        return "limited_evidence_match"
    return "weak_evidence_match"


def score_role_match(assessments: list[RequirementAssessment]) -> ScoreResult:
    category_assessments = [
        score_category(category, assessments) for category in CATEGORY_WEIGHTS
    ]
    raw_fraction = weighted_overall_score(
        {item.category: item.score for item in category_assessments}
    )
    raw_score = raw_fraction * 100
    essential = [
        item
        for item in assessments
        if item.category == RequirementCategory.ESSENTIAL_QUALIFICATIONS
    ]
    unsupported = sum(
        item.match_level in {MatchLevel.NO_EVIDENCE, MatchLevel.CONTRADICTORY}
        for item in essential
    )
    unknown = sum(item.match_level == MatchLevel.UNKNOWN for item in essential)
    cap = essential_score_cap(unsupported, unknown)
    capped_score = min(raw_score, float(cap)) if cap is not None else raw_score
    display_score = round_to_nearest_five(capped_score)
    if cap is not None:
        display_score = min(display_score, _display_cap(cap))
    return ScoreResult(
        category_assessments=category_assessments,
        raw_score=raw_score,
        capped_score=capped_score,
        display_score=display_score,
        score_band=score_band(display_score),
        applied_cap=cap,
        unsupported_essential_count=unsupported,
        unknown_essential_count=unknown,
    )
