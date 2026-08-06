from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from app.role_match.carry_forward import (
    apply_carried_experience_overrides,
    apply_carried_overrides_to_clusters,
    filter_carried_evidence_links,
    prepare_parent_overrides,
)
from app.role_match.clustering import cluster_requirements
from app.role_match.confidence import calculate_confidence, decide_authoritative_display
from app.role_match.constants import IMPORTANCE_WEIGHTS, SOURCE_MULTIPLIERS
from app.role_match.dates import calculate_relevant_months
from app.role_match.domain import (
    AnalysisInsight,
    AnalysisState,
    ConfidenceInputs,
    EligibilitySignal,
    EvidenceRelationship,
    MatchLevel,
    RequirementAssessment,
    RequirementCategory,
)
from app.role_match.eligibility import assess_eligibility
from app.role_match.evidence_catalog import build_evidence_catalog
from app.role_match.evidence_strength import assess_duration_requirement, combine_evidence
from app.role_match.extraction import extract_atomic_requirements
from app.role_match.fairness import evaluate_requirement_fairness
from app.role_match.linking import link_candidate_evidence
from app.role_match.presenter import present_analysis
from app.role_match.privacy import build_safe_profile
from app.role_match.scoring import score_role_match
from app.role_match.snapshots import SnapshotInput, save_analysis_snapshot
from app.schemas import ProfileData

_LOCATION_HINTS = re.compile(
    r"\b(work authorization|visa|sponsorship|relocat(?:e|ion)|on[- ]?site|location)\b",
    re.IGNORECASE,
)


def _save_unscored(
    *,
    db: Session,
    profile: ProfileData,
    job_description: str,
    provider: str | None,
    application_id: int | None,
    parent_analysis_id: int | None,
    analysis_date: date,
    state: AnalysisState,
    failure_code: str,
    raw_output: str | None,
):
    safe = build_safe_profile(
        profile,
        bool(_LOCATION_HINTS.search(job_description)),
    )
    return save_analysis_snapshot(
        db,
        SnapshotInput(
            profile_id=profile.id,
            application_id=application_id,
            parent_analysis_id=parent_analysis_id,
            state=state.value,
            job_description=job_description,
            safe_profile_json=safe.model_dump_json(),
            provider=provider,
            model_name=provider,
            raw_llm_output=raw_output,
            clusters=[],
            assessments=[],
            catalog=build_evidence_catalog(safe),
            score=None,
            confidence=None,
            eligibility=assess_eligibility([]),
            show_authoritative_score=False,
            failure_code=failure_code,
            excluded_items=[],
            summary=None,
            analysis_date=analysis_date,
        ),
    )


def _known_coverage(assessments: list[RequirementAssessment]) -> float:
    total = sum(IMPORTANCE_WEIGHTS[item.importance] for item in assessments)
    known = sum(
        IMPORTANCE_WEIGHTS[item.importance]
        for item in assessments
        if item.known and item.strength is not None
    )
    return known / total if total else 0.0


def _reliability(assessments: list[RequirementAssessment]) -> float:
    values: list[float] = []
    for item in assessments:
        links = [link for link in item.evidence_links if not link.is_duplicate]
        if links:
            values.append(max(SOURCE_MULTIPLIERS[link.source] for link in links))
        elif item.known and item.strength is not None:
            values.append(1.0)
    return sum(values) / len(values) if values else 0.0


def _consistency(clusters, unresolved: int, invalid_links: int) -> tuple[float, float]:
    denominator = max(len(clusters) + unresolved, 1)
    issues = (
        sum(cluster.importance_conflict for cluster in clusters)
        + unresolved
        + invalid_links
    )
    rate = min(issues / denominator, 1.0)
    return 1.0 - rate, rate


def _eligibility(clusters, links_by_requirement) -> list[EligibilitySignal]:
    signals = []
    for cluster in clusters:
        if not (
            cluster.is_eligibility
            or cluster.primary_category == RequirementCategory.ELIGIBILITY
        ):
            continue
        links = links_by_requirement.get(cluster.cluster_id, [])
        contradiction = any(link.is_contradiction for link in links)
        support = any(
            not link.is_contradiction
            and link.relationship != EvidenceRelationship.UNRELATED
            for link in links
        )
        signals.append(
            EligibilitySignal(
                requirement_id=cluster.cluster_id,
                mandatory=cluster.importance.value == "critical",
                explicit_support=support,
                explicit_contradiction=contradiction,
                unknown=not support and not contradiction,
                reason=(
                    f"{cluster.canonical_requirement} is explicitly contradicted."
                    if contradiction
                    else f"{cluster.canonical_requirement} is supported."
                    if support
                    else f"{cluster.canonical_requirement} needs confirmation."
                ),
            )
        )
    return signals


def _human_summary(clusters, assessments, score):
    cluster_map = {cluster.cluster_id: cluster for cluster in clusters}
    strengths, concerns = [], []
    ordered = sorted(
        assessments,
        key=lambda item: (
            IMPORTANCE_WEIGHTS[item.importance],
            item.strength if item.strength is not None else -1,
        ),
        reverse=True,
    )
    for item in ordered:
        cluster = cluster_map[item.cluster_id]
        if item.match_level in {MatchLevel.STRONG, MatchLevel.MODERATE}:
            sources = sorted(
                {
                    link.source.value.replace("_", " ")
                    for link in item.evidence_links
                    if not link.is_duplicate
                }
            )
            strengths.append(
                AnalysisInsight(
                    title=cluster.canonical_requirement,
                    explanation="Supported by direct profile evidence.",
                    evidence_label=", ".join(sources) or None,
                )
            )
        elif item.match_level == MatchLevel.UNKNOWN:
            concerns.append(
                AnalysisInsight(
                    title=f"{cluster.canonical_requirement} needs confirmation",
                    explanation="Add truthful evidence when this experience exists.",
                    evidence_label="Needs confirmation",
                )
            )
        else:
            concerns.append(
                AnalysisInsight(
                    title=f"{cluster.canonical_requirement} needs clearer evidence",
                    explanation="Add a concrete work or project example when factually accurate.",
                    evidence_label="Evidence gap",
                )
            )
    return present_analysis(
        display_score=score.display_score,
        score_band=score.score_band,
        strengths=strengths[:3],
        concerns=concerns[:3],
    )


def analyze_role_match(
    *,
    db: Session,
    profile: ProfileData,
    job_description: str,
    provider: str,
    api_key: str,
    application_id: int | None,
    parent_analysis_id: int | None,
    analysis_date: date,
):
    include_location = bool(_LOCATION_HINTS.search(job_description))
    safe = build_safe_profile(profile, include_location)
    catalog = build_evidence_catalog(safe)
    try:
        extraction = extract_atomic_requirements(
            job_description,
            provider,
            api_key,
            profile_id=profile.id,
        )
    except Exception:
        return _save_unscored(
            db=db,
            profile=profile,
            job_description=job_description,
            provider=provider,
            application_id=application_id,
            parent_analysis_id=parent_analysis_id,
            analysis_date=analysis_date,
            state=AnalysisState.FAILED,
            failure_code="provider_failure",
            raw_output=None,
        )
    if extraction.state != AnalysisState.EXTRACTED:
        return _save_unscored(
            db=db,
            profile=profile,
            job_description=job_description,
            provider=provider,
            application_id=application_id,
            parent_analysis_id=parent_analysis_id,
            analysis_date=analysis_date,
            state=AnalysisState.NEEDS_REVIEW,
            failure_code=extraction.failure_code or "invalid_requirement_extraction",
            raw_output=json.dumps(extraction.raw_outputs, ensure_ascii=False),
        )

    requirements, excluded_items, fairness_reviews = [], [], 0
    for requirement in extraction.requirements:
        decision = evaluate_requirement_fairness(requirement.text)
        if decision.excluded:
            requirement = requirement.model_copy(
                update={
                    "excluded": True,
                    "exclusion_reason": decision.reason,
                }
            )
            excluded_items.append(
                {
                    "source_id": requirement.source_id,
                    "text": requirement.text,
                    "reason": decision.reason,
                }
            )
        elif decision.action == "review":
            fairness_reviews += 1
        requirements.append(requirement)

    clustering = cluster_requirements(requirements)
    prepared_overrides = prepare_parent_overrides(
        db,
        parent_analysis_id,
        clustering.clusters,
    )
    clusters = apply_carried_overrides_to_clusters(
        clustering.clusters,
        prepared_overrides,
    )
    try:
        linking = link_candidate_evidence(
            clusters,
            catalog,
            provider,
            api_key,
            profile_id=profile.id,
        )
    except Exception:
        return _save_unscored(
            db=db,
            profile=profile,
            job_description=job_description,
            provider=provider,
            application_id=application_id,
            parent_analysis_id=parent_analysis_id,
            analysis_date=analysis_date,
            state=AnalysisState.FAILED,
            failure_code="provider_failure",
            raw_output=json.dumps(extraction.raw_outputs, ensure_ascii=False),
        )

    links_by_requirement = defaultdict(list)
    filtered_links = filter_carried_evidence_links(
        linking.valid_links,
        prepared_overrides,
    )
    for link in filtered_links:
        links_by_requirement[link.requirement_id].append(link)

    assessments = []
    for cluster in clusters:
        if cluster.excluded or cluster.is_eligibility or cluster.is_trainable:
            continue
        if cluster.primary_category in {
            RequirementCategory.ELIGIBILITY,
            RequirementCategory.TRAINABLE,
        }:
            continue
        links = links_by_requirement.get(cluster.cluster_id, [])
        if cluster.minimum_months is not None:
            months = calculate_relevant_months(
                catalog,
                {link.evidence_id for link in links},
                analysis_date,
            )
            item = assess_duration_requirement(
                cluster.minimum_months,
                months,
                cluster_id=cluster.cluster_id,
                category=cluster.primary_category,
                importance=cluster.importance,
            ).model_copy(update={"evidence_links": links})
        else:
            item = combine_evidence(links, cluster, analysis_date)
        assessments.append(item)

    assessments = apply_carried_experience_overrides(
        assessments,
        clusters,
        prepared_overrides,
    )
    score = score_role_match(assessments)
    known_coverage = _known_coverage(assessments)
    consistency, conflict_rate = _consistency(
        clusters,
        len(clustering.unresolved_conflicts) + fairness_reviews,
        linking.invalid_link_count,
    )
    confidence = calculate_confidence(
        ConfidenceInputs(
            known_coverage=known_coverage,
            evidence_reliability=_reliability(assessments),
            evidence_consistency=consistency,
        )
    )
    eligibility = assess_eligibility(_eligibility(clusters, links_by_requirement))
    display = decide_authoritative_display(
        known_coverage=known_coverage,
        confidence=confidence.score,
        conflict_rate=conflict_rate,
        requirement_count=len([cluster for cluster in clusters if not cluster.excluded]),
        scoring_succeeded=True,
    )
    state = AnalysisState.SUCCESS if display.show_score else AnalysisState.NEEDS_REVIEW
    summary = _human_summary(clusters, assessments, score)
    return save_analysis_snapshot(
        db,
        SnapshotInput(
            profile_id=profile.id,
            application_id=application_id,
            parent_analysis_id=parent_analysis_id,
            state=state.value,
            job_description=job_description,
            safe_profile_json=safe.model_dump_json(),
            provider=provider,
            model_name=provider,
            raw_llm_output=json.dumps(
                {
                    "extraction": extraction.raw_outputs,
                    "linking": linking.raw_output,
                },
                ensure_ascii=False,
            ),
            clusters=clusters,
            assessments=assessments,
            catalog=catalog,
            score=score,
            confidence=confidence,
            eligibility=eligibility,
            show_authoritative_score=display.show_score,
            failure_code=None if display.show_score else display.reason,
            excluded_items=excluded_items,
            summary=summary,
            analysis_date=analysis_date,
            overrides=prepared_overrides,
        ),
    )
