from __future__ import annotations

from datetime import date

from app.role_match.constants import (
    DEPTH_MULTIPLIERS,
    RELATIONSHIP_MULTIPLIERS,
    SOURCE_MULTIPLIERS,
)
from app.role_match.domain import (
    EvidenceLink,
    EvidenceRelationship,
    MatchLevel,
    RequirementAssessment,
    RequirementCluster,
    RequirementImportance,
    TechnologyVolatility,
)


def _years_since(last_used: date, analysis_date: date) -> float:
    days = max((analysis_date - last_used).days, 0)
    return days / 365.2425


def calculate_recency_multiplier(
    volatility: TechnologyVolatility,
    last_used_date: date | None,
    analysis_date: date,
    *,
    is_current: bool = False,
) -> float:
    if is_current or last_used_date is None:
        return 1.0
    years = _years_since(last_used_date, analysis_date)
    if volatility == TechnologyVolatility.STABLE:
        return 1.0 if years <= 5 else 0.90
    if volatility == TechnologyVolatility.EVOLVING:
        if years <= 3:
            return 1.0
        if years <= 6:
            return 0.85
        return 0.70
    if years <= 2:
        return 1.0
    if years <= 4:
        return 0.75
    return 0.50


def calculate_base_strength(link: EvidenceLink, analysis_date: date) -> float:
    if link.precomputed_strength is not None:
        return link.precomputed_strength
    recency = calculate_recency_multiplier(
        link.volatility,
        link.last_used_date,
        analysis_date,
        is_current=link.is_current,
    )
    return (
        RELATIONSHIP_MULTIPLIERS[link.relationship]
        * SOURCE_MULTIPLIERS[link.source]
        * DEPTH_MULTIPLIERS[link.depth]
        * recency
    )


def strength_to_match_level(value: float) -> MatchLevel:
    if value >= 0.75:
        return MatchLevel.STRONG
    if value >= 0.45:
        return MatchLevel.MODERATE
    if value >= 0.10:
        return MatchLevel.WEAK
    return MatchLevel.NO_EVIDENCE


def _relationship_ceiling(
    requirement: RequirementCluster,
    links: list[EvidenceLink],
) -> float:
    if not links:
        return 1.0
    strongest_relationship = max(
        links,
        key=lambda item: RELATIONSHIP_MULTIPLIERS[item.relationship],
    ).relationship
    if strongest_relationship == EvidenceRelationship.UNRELATED:
        return 0.0
    if strongest_relationship == EvidenceRelationship.ADJACENT:
        return 0.449
    if strongest_relationship == EvidenceRelationship.FUNCTIONAL_EQUIVALENT:
        if requirement.tool_specificity == "operational":
            return 0.449
        if requirement.tool_specificity == "specific":
            return 0.749
    return 1.0


def combine_evidence(
    links: list[EvidenceLink],
    requirement: RequirementCluster,
    analysis_date: date,
) -> RequirementAssessment:
    if any(link.is_contradiction for link in links):
        return RequirementAssessment(
            cluster_id=requirement.cluster_id,
            category=requirement.primary_category,
            importance=requirement.importance,
            match_level=MatchLevel.CONTRADICTORY,
            strength=0.0,
            evidence_links=links,
            explanation="Explicit contradictory evidence was found.",
            known=True,
            confidence_evidence_count=len(links),
        )
    independent = [link for link in links if not link.is_duplicate]
    if not independent:
        return RequirementAssessment(
            cluster_id=requirement.cluster_id,
            category=requirement.primary_category,
            importance=requirement.importance,
            match_level=MatchLevel.UNKNOWN,
            strength=None,
            evidence_links=links,
            explanation="The available profile information is not sufficient to assess this requirement.",
            known=False,
            confidence_evidence_count=len(links),
        )
    scored = sorted(
        (calculate_base_strength(link, analysis_date) for link in independent),
        reverse=True,
    )
    combined = scored[0]
    if len(scored) > 1:
        combined += scored[1] * 0.10
    if len(scored) > 2:
        combined += scored[2] * 0.03
    combined = min(combined, 1.0, _relationship_ceiling(requirement, independent))
    return RequirementAssessment(
        cluster_id=requirement.cluster_id,
        category=requirement.primary_category,
        importance=requirement.importance,
        match_level=strength_to_match_level(combined),
        strength=combined,
        evidence_links=links,
        explanation="Evidence strength was calculated from relationship, source, depth, recency, and independent corroboration.",
        known=True,
        confidence_evidence_count=len(independent),
    )


def assess_duration_requirement(
    required_months: int,
    actual_months: int | None,
    *,
    cluster_id: str = "duration",
    category=None,
    importance: RequirementImportance = RequirementImportance.CRITICAL,
) -> RequirementAssessment:
    from app.role_match.domain import RequirementCategory

    resolved_category = category or RequirementCategory.ESSENTIAL_QUALIFICATIONS
    if actual_months is None:
        return RequirementAssessment(
            cluster_id=cluster_id,
            category=resolved_category,
            importance=importance,
            match_level=MatchLevel.UNKNOWN,
            strength=None,
            known=False,
            explanation="The relevant experience duration could not be verified.",
        )
    ratio = actual_months / required_months if required_months > 0 else 1.0
    if ratio >= 1.0:
        level, strength = MatchLevel.STRONG, 1.0
        explanation = "Meets or exceeds the stated experience requirement."
    elif ratio >= 0.85:
        level, strength = MatchLevel.MODERATE, 0.70
        years = required_months / 12
        years_text = str(int(years)) if years.is_integer() else f"{years:g}"
        explanation = (
            "Slightly below the stated experience requirement; "
            f"relevant experience is close to the requested {years_text} years."
        )
    elif ratio >= 0.60:
        level, strength = MatchLevel.WEAK, 0.35
        explanation = "Relevant experience is meaningfully below the stated duration."
    else:
        level, strength = MatchLevel.NO_EVIDENCE, 0.0
        explanation = "Relevant experience is substantially below the stated duration."
    return RequirementAssessment(
        cluster_id=cluster_id,
        category=resolved_category,
        importance=importance,
        match_level=level,
        strength=strength,
        known=True,
        explanation=explanation,
    )
