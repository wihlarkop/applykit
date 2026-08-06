from datetime import date

import pytest

from app.role_match.domain import (
    EvidenceDepth,
    EvidenceLink,
    EvidenceRelationship,
    EvidenceSource,
    MatchLevel,
    RequirementCategory,
    RequirementCluster,
    RequirementImportance,
    TechnologyVolatility,
)
from app.role_match.evidence_strength import (
    assess_duration_requirement,
    calculate_base_strength,
    calculate_recency_multiplier,
    combine_evidence,
    strength_to_match_level,
)

ANALYSIS_DATE = date(2026, 8, 6)


def cluster(**updates) -> RequirementCluster:
    payload = {
        "cluster_id": "req:python",
        "canonical_requirement": "Production Python backend capability",
        "canonical_key": "python-backend",
        "primary_category": RequirementCategory.RELEVANT_COMPETENCIES,
        "importance": RequirementImportance.CRITICAL,
        "mention_count": 1,
        "importance_conflict": False,
        "importance_mentions": {
            RequirementImportance.CRITICAL: 1,
            RequirementImportance.IMPORTANT: 0,
            RequirementImportance.SUPPORTING: 0,
        },
        "source_quotes": ["Python required"],
        "source_ids": ["a"],
        "is_eligibility": False,
        "is_trainable": False,
        "volatility": TechnologyVolatility.EVOLVING,
        "minimum_months": None,
        "tool_specificity": "capability",
    }
    payload.update(updates)
    return RequirementCluster(**payload)


def link(**updates) -> EvidenceLink:
    payload = {
        "requirement_id": "req:python",
        "evidence_id": "work:0:bullet:0",
        "source": EvidenceSource.WORK_EXPERIENCE,
        "relationship": EvidenceRelationship.EXACT,
        "depth": EvidenceDepth.PRODUCTION_OWNERSHIP,
        "volatility": TechnologyVolatility.EVOLVING,
        "last_used_date": ANALYSIS_DATE,
        "is_current": True,
    }
    payload.update(updates)
    return EvidenceLink(**payload)


def test_direct_recent_work_ownership_is_full_strength() -> None:
    assert calculate_base_strength(link(), ANALYSIS_DATE) == 1.0


def test_skill_only_exposure_is_weak() -> None:
    value = calculate_base_strength(
        link(
            source=EvidenceSource.SKILLS_LIST,
            depth=EvidenceDepth.EXPOSURE_ONLY,
        ),
        ANALYSIS_DATE,
    )
    assert value == pytest.approx(0.1575)
    assert strength_to_match_level(value) == MatchLevel.WEAK


def test_adjacent_skill_only_evidence_is_too_weak_to_count() -> None:
    value = calculate_base_strength(
        link(
            relationship=EvidenceRelationship.ADJACENT,
            source=EvidenceSource.SKILLS_LIST,
            depth=EvidenceDepth.EXPOSURE_ONLY,
        ),
        ANALYSIS_DATE,
    )
    assert value == pytest.approx(0.063)
    assert strength_to_match_level(value) == MatchLevel.NO_EVIDENCE


def test_tool_specific_equivalent_is_capped_at_moderate() -> None:
    assessment = combine_evidence(
        [link(relationship=EvidenceRelationship.FUNCTIONAL_EQUIVALENT)],
        cluster(tool_specificity="specific"),
        ANALYSIS_DATE,
    )
    assert assessment.match_level == MatchLevel.MODERATE
    assert assessment.strength == pytest.approx(0.749)


def test_operational_equivalent_is_capped_at_weak() -> None:
    assessment = combine_evidence(
        [link(relationship=EvidenceRelationship.FUNCTIONAL_EQUIVALENT)],
        cluster(tool_specificity="operational"),
        ANALYSIS_DATE,
    )
    assert assessment.match_level == MatchLevel.WEAK
    assert assessment.strength == pytest.approx(0.449)


def test_top_three_independent_links_add_capped_bonus() -> None:
    links = [
        link(evidence_id="a", precomputed_strength=0.72),
        link(evidence_id="b", precomputed_strength=0.60),
        link(evidence_id="c", precomputed_strength=0.40),
        link(evidence_id="d", precomputed_strength=0.20),
    ]
    assessment = combine_evidence(links, cluster(), ANALYSIS_DATE)
    assert assessment.strength == pytest.approx(0.792)
    assert assessment.confidence_evidence_count == 4


def test_duplicate_evidence_does_not_receive_bonus() -> None:
    assessment = combine_evidence(
        [
            link(evidence_id="work:a", precomputed_strength=0.72),
            link(evidence_id="summary:a", precomputed_strength=0.72, is_duplicate=True),
        ],
        cluster(),
        ANALYSIS_DATE,
    )
    assert assessment.strength == pytest.approx(0.72)


@pytest.mark.parametrize(
    ("volatility", "last_used", "expected"),
    [
        (TechnologyVolatility.STABLE, date(2018, 1, 1), 0.90),
        (TechnologyVolatility.EVOLVING, date(2021, 8, 6), 0.85),
        (TechnologyVolatility.EVOLVING, date(2018, 8, 6), 0.70),
        (TechnologyVolatility.FAST_MOVING, date(2023, 8, 6), 0.75),
        (TechnologyVolatility.FAST_MOVING, date(2020, 8, 6), 0.50),
    ],
)
def test_recency_tables(volatility, last_used, expected) -> None:
    assert calculate_recency_multiplier(volatility, last_used, ANALYSIS_DATE) == expected


@pytest.mark.parametrize(
    ("required", "actual", "expected"),
    [
        (60, 60, MatchLevel.STRONG),
        (60, 51, MatchLevel.MODERATE),
        (60, 36, MatchLevel.WEAK),
        (60, 35, MatchLevel.NO_EVIDENCE),
        (60, None, MatchLevel.UNKNOWN),
    ],
)
def test_duration_thresholds(required, actual, expected) -> None:
    assert assess_duration_requirement(required, actual).match_level == expected
