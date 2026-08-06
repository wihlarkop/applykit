from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.role_match.confidence import calculate_confidence, decide_authoritative_display
from app.role_match.constants import IMPORTANCE_WEIGHTS, SOURCE_MULTIPLIERS
from app.role_match.dates import calculate_relevant_months
from app.role_match.domain import (
    ConfidenceInputs,
    EligibilitySignal,
    EvidenceCatalogItem,
    EvidenceDepth,
    EvidenceLink,
    EvidenceRelationship,
    MatchLevel,
    RequirementAssessment,
    RequirementCategory,
    RequirementCluster,
    RequirementImportance,
    TechnologyVolatility,
)
from app.role_match.eligibility import assess_eligibility
from app.role_match.evidence_catalog import build_evidence_catalog
from app.role_match.evidence_strength import assess_duration_requirement, combine_evidence
from app.role_match.fairness import evaluate_requirement_fairness
from app.role_match.privacy import build_safe_profile
from app.role_match.scoring import score_role_match
from app.schemas import ProfileData

GOLDEN_DIR = Path(__file__).parents[1] / "golden" / "role_match"


class GoldenRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    text: str
    category: RequirementCategory
    importance: RequirementImportance = RequirementImportance.CRITICAL
    volatility: TechnologyVolatility = TechnologyVolatility.EVOLVING
    tool_specificity: str = "capability"
    minimum_months: int | None = Field(default=None, ge=0)
    actual_months: int | None = Field(default=None, ge=0)
    excluded: bool = False
    exclusion_reason: str | None = None
    is_eligibility: bool = False
    is_trainable: bool = False
    mention_count: int = Field(default=1, ge=1)
    importance_conflict: bool = False

    @property
    def cluster_id(self) -> str:
        return f"req:{self.key}"

    def to_cluster(self) -> RequirementCluster:
        importance_mentions = {
            value: 0 for value in RequirementImportance
        }
        importance_mentions[self.importance] = self.mention_count
        return RequirementCluster(
            cluster_id=self.cluster_id,
            canonical_requirement=self.text,
            canonical_key=self.key,
            primary_category=self.category,
            importance=self.importance,
            mention_count=self.mention_count,
            importance_conflict=self.importance_conflict,
            importance_mentions=importance_mentions,
            source_quotes=[self.text],
            source_ids=[f"jd:{self.key}"],
            is_eligibility=self.is_eligibility,
            is_trainable=self.is_trainable,
            volatility=self.volatility,
            minimum_months=self.minimum_months,
            tool_specificity=self.tool_specificity,
            excluded=self.excluded,
            exclusion_reason=self.exclusion_reason,
        )


class GoldenLink(BaseModel):
    model_config = ConfigDict(frozen=True)

    requirement_key: str
    evidence_id: str
    relationship: EvidenceRelationship = EvidenceRelationship.EXACT
    depth: EvidenceDepth = EvidenceDepth.PRODUCTION_OWNERSHIP
    last_used_date: date | None = None
    is_current: bool = False
    is_duplicate: bool = False
    is_contradiction: bool = False
    precomputed_strength: float | None = Field(default=None, ge=0.0, le=1.0)

    @property
    def requirement_id(self) -> str:
        return f"req:{self.requirement_key}"


class GoldenExpected(BaseModel):
    model_config = ConfigDict(frozen=True)

    display_score_min: int = Field(ge=0, le=100)
    display_score_max: int = Field(ge=0, le=100)
    score_band: str
    confidence: str
    eligibility: str
    show_authoritative_score: bool


class GoldenInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    requirements: list[GoldenRequirement]
    evidence: list[EvidenceCatalogItem]
    links: list[GoldenLink]
    eligibility_signals: list[EligibilitySignal] = Field(default_factory=list)
    unresolved_conflict_count: int = Field(default=0, ge=0)
    invalid_link_count: int = Field(default=0, ge=0)


class GoldenCase(GoldenInput):
    model_config = ConfigDict(frozen=True)

    name: str
    analysis_date: date
    expected: GoldenExpected
    invariants: list[str] = Field(default_factory=list)
    fairness_requirements: list[str] = Field(default_factory=list)
    profile_variants: list[dict[str, Any]] = Field(default_factory=list)
    comparison: GoldenInput | None = None


class GoldenResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    display_score: int
    score_band: str
    confidence: str
    eligibility: str
    show_authoritative_score: bool
    assessments: dict[str, RequirementAssessment]
    duration_months: dict[str, int | None]
    fairness_actions: dict[str, str]
    safe_profile_payloads: list[str]
    evidence_catalog_payloads: list[str]
    comparison_display_score: int | None = None
    comparison_score_band: str | None = None


def _known_coverage(assessments: list[RequirementAssessment]) -> float:
    total = sum(IMPORTANCE_WEIGHTS[item.importance] for item in assessments)
    known = sum(
        IMPORTANCE_WEIGHTS[item.importance]
        for item in assessments
        if item.known and item.strength is not None
    )
    return known / total if total else 0.0


def _evidence_reliability(assessments: list[RequirementAssessment]) -> float:
    values: list[float] = []
    for assessment in assessments:
        independent = [
            link for link in assessment.evidence_links if not link.is_duplicate
        ]
        if independent:
            values.append(max(SOURCE_MULTIPLIERS[link.source] for link in independent))
        elif assessment.known and assessment.strength is not None:
            values.append(1.0)
    return sum(values) / len(values) if values else 0.0


def _evaluate_input(
    value: GoldenInput,
    analysis_date: date,
) -> tuple[
    int,
    str,
    str,
    str,
    bool,
    dict[str, RequirementAssessment],
    dict[str, int | None],
]:
    clusters = [item.to_cluster() for item in value.requirements]
    catalog = {item.evidence_id: item for item in value.evidence}
    cluster_map = {item.cluster_id: item for item in clusters}
    links_by_requirement: dict[str, list[EvidenceLink]] = defaultdict(list)

    for item in value.links:
        cluster = cluster_map[item.requirement_id]
        evidence = catalog[item.evidence_id]
        links_by_requirement[item.requirement_id].append(
            EvidenceLink(
                requirement_id=item.requirement_id,
                evidence_id=item.evidence_id,
                source=evidence.source,
                relationship=item.relationship,
                depth=item.depth,
                volatility=cluster.volatility,
                last_used_date=item.last_used_date,
                is_current=item.is_current,
                is_duplicate=item.is_duplicate,
                is_contradiction=item.is_contradiction,
                precomputed_strength=item.precomputed_strength,
            )
        )

    assessments: list[RequirementAssessment] = []
    duration_months: dict[str, int | None] = {}
    input_by_cluster = {item.cluster_id: item for item in value.requirements}
    for cluster in clusters:
        if cluster.excluded or cluster.is_eligibility or cluster.is_trainable:
            continue
        links = links_by_requirement.get(cluster.cluster_id, [])
        requirement_input = input_by_cluster[cluster.cluster_id]
        if cluster.minimum_months is not None:
            actual_months = requirement_input.actual_months
            if actual_months is None:
                actual_months = calculate_relevant_months(
                    list(catalog.values()),
                    {link.evidence_id for link in links},
                    analysis_date,
                )
            duration_months[cluster.cluster_id] = actual_months
            assessment = assess_duration_requirement(
                cluster.minimum_months,
                actual_months,
                cluster_id=cluster.cluster_id,
                category=cluster.primary_category,
                importance=cluster.importance,
            ).model_copy(update={"evidence_links": links})
        else:
            assessment = combine_evidence(links, cluster, analysis_date)
        assessments.append(assessment)

    score = score_role_match(assessments)
    known_coverage = _known_coverage(assessments)
    issue_count = (
        sum(cluster.importance_conflict for cluster in clusters)
        + value.unresolved_conflict_count
        + value.invalid_link_count
    )
    conflict_rate = min(issue_count / max(len(clusters), 1), 1.0)
    confidence = calculate_confidence(
        ConfidenceInputs(
            known_coverage=known_coverage,
            evidence_reliability=_evidence_reliability(assessments),
            evidence_consistency=1.0 - conflict_rate,
        )
    )
    eligibility = assess_eligibility(value.eligibility_signals)
    display = decide_authoritative_display(
        known_coverage=known_coverage,
        confidence=confidence.score,
        conflict_rate=conflict_rate,
        requirement_count=len([item for item in clusters if not item.excluded]),
        scoring_succeeded=True,
    )
    return (
        score.display_score,
        score.score_band,
        confidence.band.value,
        eligibility.status.value,
        display.show_score,
        {item.cluster_id: item for item in assessments},
        duration_months,
    )


def evaluate_normalized_case(case: GoldenCase) -> GoldenResult:
    (
        display_score,
        score_band,
        confidence,
        eligibility,
        show_score,
        assessments,
        duration_months,
    ) = _evaluate_input(case, case.analysis_date)

    fairness_actions = {
        requirement: evaluate_requirement_fairness(requirement).action
        for requirement in case.fairness_requirements
    }
    safe_profiles = [
        build_safe_profile(ProfileData.model_validate(profile), False)
        for profile in case.profile_variants
    ]
    safe_profile_payloads = [item.model_dump_json() for item in safe_profiles]
    evidence_catalog_payloads = [
        "|".join(
            item.model_dump_json()
            for item in build_evidence_catalog(safe_profile)
        )
        for safe_profile in safe_profiles
    ]

    comparison_display_score = None
    comparison_score_band = None
    if case.comparison is not None:
        comparison = _evaluate_input(case.comparison, case.analysis_date)
        comparison_display_score = comparison[0]
        comparison_score_band = comparison[1]

    return GoldenResult(
        display_score=display_score,
        score_band=score_band,
        confidence=confidence,
        eligibility=eligibility,
        show_authoritative_score=show_score,
        assessments=assessments,
        duration_months=duration_months,
        fairness_actions=fairness_actions,
        safe_profile_payloads=safe_profile_payloads,
        evidence_catalog_payloads=evidence_catalog_payloads,
        comparison_display_score=comparison_display_score,
        comparison_score_band=comparison_score_band,
    )


def assert_invariants(case: GoldenCase, result: GoldenResult) -> None:
    for invariant in case.invariants:
        if invariant == "duplicate_keywords_do_not_add_corroboration":
            duplicate_assessments = [
                assessment
                for assessment in result.assessments.values()
                if any(link.is_duplicate for link in assessment.evidence_links)
            ]
            assert duplicate_assessments
            for assessment in duplicate_assessments:
                best = max(
                    link.precomputed_strength or 0.0
                    for link in assessment.evidence_links
                    if not link.is_duplicate
                )
                assert assessment.strength == best
        elif invariant == "skills_only_evidence_is_not_strong":
            skills_only = [
                assessment
                for assessment in result.assessments.values()
                if assessment.evidence_links
                and all(
                    link.source.value == "skills_list"
                    for link in assessment.evidence_links
                )
            ]
            assert skills_only
            assert all(
                assessment.match_level != MatchLevel.STRONG
                for assessment in skills_only
            )
        elif invariant == "production_evidence_outranks_keyword_stuffing":
            production = result.assessments["req:production-python"]
            keywords = result.assessments["req:keyword-python"]
            assert (production.strength or 0) > (keywords.strength or 0)
        elif invariant == "functional_equivalent_is_credited":
            equivalents = [
                assessment
                for assessment in result.assessments.values()
                if any(
                    link.relationship == EvidenceRelationship.FUNCTIONAL_EQUIVALENT
                    for link in assessment.evidence_links
                )
            ]
            assert equivalents
            assert all((item.strength or 0) > 0 for item in equivalents)
        elif invariant == "tool_specific_equivalent_not_strong":
            assert all(
                assessment.match_level != MatchLevel.STRONG
                for assessment in result.assessments.values()
                if any(
                    link.relationship == EvidenceRelationship.FUNCTIONAL_EQUIVALENT
                    for link in assessment.evidence_links
                )
            )
        elif invariant == "old_experience_remains_valid":
            assert (result.assessments["req:django"].strength or 0) > 0
        elif invariant == "duration_shortfall_is_not_ineligible":
            assert result.eligibility not in {"likely_ineligible", "ineligible"}
        elif invariant == "overlapping_intervals_not_double_counted":
            assert result.duration_months["req:backend-duration"] == 42
        elif invariant == "unknown_is_not_failure":
            assert any(
                item.match_level == MatchLevel.UNKNOWN
                for item in result.assessments.values()
            )
            assert result.display_score > 0
        elif invariant == "missing_eligibility_is_unclear":
            assert result.eligibility == "eligibility_unclear"
        elif invariant == "protected_fields_do_not_change_payload":
            assert len(result.safe_profile_payloads) == 2
            assert len(set(result.safe_profile_payloads)) == 1
            assert len(set(result.evidence_catalog_payloads)) == 1
        elif invariant == "excluded_requirement_not_scored":
            assert "exclude_warn_continue" in result.fairness_actions.values()
            excluded_ids = {
                item.cluster_id for item in case.requirements if item.excluded
            }
            assert excluded_ids
            assert excluded_ids.isdisjoint(result.assessments)
        elif invariant == "normalized_variants_score_equally":
            assert result.comparison_display_score == result.display_score
            assert result.comparison_score_band == result.score_band
        else:
            raise AssertionError(f"Unknown golden invariant: {invariant}")
