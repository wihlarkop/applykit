from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.exceptions import InvalidRequestError, RoleMatchAnalysisNotFoundError
from app.role_match.api_schemas import RoleMatchOverrideInput
from app.role_match.clustering import requirement_similarity
from app.role_match.confidence import calculate_confidence, decide_authoritative_display
from app.role_match.constants import (
    AUTOMATIC_OVERRIDE_CARRY_SIMILARITY,
    IMPORTANCE_WEIGHTS,
    OVERRIDE_REVIEW_SIMILARITY,
    SOURCE_MULTIPLIERS,
)
from app.role_match.domain import (
    AnalysisInsight,
    ConfidenceInputs,
    EligibilityAssessment,
    EligibilityStatus,
    EvidenceCatalogItem,
    EvidenceDepth,
    EvidenceLink,
    EvidenceRelationship,
    EvidenceSource,
    MatchLevel,
    OverrideCarryStatus,
    RequirementAssessment,
    RequirementCategory,
    RequirementCluster,
    RequirementImportance,
    TechnologyVolatility,
)
from app.role_match.evidence_strength import combine_evidence
from app.role_match.models import (
    RoleMatchAnalysis,
    RoleMatchEvidence,
    RoleMatchOverride,
    RoleMatchRequirement,
)
from app.role_match.presenter import present_analysis
from app.role_match.scoring import score_role_match
from app.role_match.snapshots import SnapshotInput, SnapshotOverride, save_analysis_snapshot


def _loads(raw: str | None, default: Any) -> Any:
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def classify_override_carry(
    *,
    previous_key: str,
    previous_category: str,
    new_clusters: list[RequirementCluster],
) -> tuple[OverrideCarryStatus, str | None]:
    exact = next(
        (cluster for cluster in new_clusters if cluster.canonical_key == previous_key),
        None,
    )
    if exact is not None:
        if exact.primary_category.value == previous_category:
            return OverrideCarryStatus.CARRIED_FORWARD, exact.canonical_key
        return OverrideCarryStatus.NEEDS_REVIEW, exact.canonical_key

    scored = [
        (
            requirement_similarity(
                previous_key.replace("-", " "),
                f"{cluster.canonical_key.replace('-', ' ')} {cluster.canonical_requirement}",
            ),
            cluster,
        )
        for cluster in new_clusters
    ]
    if not scored:
        return OverrideCarryStatus.NOT_APPLICABLE, None
    similarity, target = max(scored, key=lambda item: item[0])
    if (
        similarity >= AUTOMATIC_OVERRIDE_CARRY_SIMILARITY
        and target.primary_category.value == previous_category
    ):
        return OverrideCarryStatus.CARRIED_FORWARD, target.canonical_key
    if similarity >= OVERRIDE_REVIEW_SIMILARITY:
        return OverrideCarryStatus.NEEDS_REVIEW, target.canonical_key
    return OverrideCarryStatus.NOT_APPLICABLE, None


def prepare_parent_overrides(
    db: Session,
    parent_analysis_id: int | None,
    new_clusters: list[RequirementCluster],
) -> tuple[SnapshotOverride, ...]:
    if parent_analysis_id is None:
        return ()
    previous_requirements = {
        item.canonical_key: item
        for item in db.query(RoleMatchRequirement)
        .filter_by(analysis_id=parent_analysis_id)
        .all()
    }
    previous_overrides = (
        db.query(RoleMatchOverride)
        .filter_by(analysis_id=parent_analysis_id)
        .order_by(RoleMatchOverride.id.asc())
        .all()
    )
    prepared: list[SnapshotOverride] = []
    for item in previous_overrides:
        previous_requirement = previous_requirements.get(item.requirement_key)
        previous_category = (
            previous_requirement.primary_category
            if previous_requirement is not None
            else ""
        )
        status, target_key = classify_override_carry(
            previous_key=item.requirement_key,
            previous_category=previous_category,
            new_clusters=new_clusters,
        )
        prepared.append(
            SnapshotOverride(
                requirement_key=target_key or item.requirement_key,
                field_name=item.field_name,
                extracted_value=_loads(item.extracted_value, None),
                effective_value=_loads(item.effective_value, None),
                reason=item.reason,
                source="carry_forward",
                carry_status=status.value,
                source_override_id=item.id,
            )
        )
    return tuple(prepared)


def apply_carried_overrides_to_clusters(
    clusters: list[RequirementCluster],
    prepared: tuple[SnapshotOverride, ...],
) -> list[RequirementCluster]:
    by_key = {item.canonical_key: item for item in clusters}
    for item in prepared:
        if item.carry_status != OverrideCarryStatus.CARRIED_FORWARD.value:
            continue
        cluster = by_key.get(item.requirement_key)
        if cluster is None:
            continue
        if item.field_name == "importance":
            try:
                importance = RequirementImportance(str(item.effective_value))
            except ValueError:
                continue
            by_key[item.requirement_key] = cluster.model_copy(
                update={"importance": importance}
            )
        elif item.field_name == "excluded" and isinstance(item.effective_value, bool):
            if (
                cluster.exclusion_reason == "potentially_non_job_related"
                and item.effective_value is False
            ):
                continue
            by_key[item.requirement_key] = cluster.model_copy(
                update={
                    "excluded": item.effective_value,
                    "exclusion_reason": (
                        "user_excluded" if item.effective_value else None
                    ),
                }
            )
    return [by_key[item.canonical_key] for item in clusters]


def filter_carried_evidence_links(
    links: list[EvidenceLink],
    prepared: tuple[SnapshotOverride, ...],
) -> list[EvidenceLink]:
    removed = {
        (item.requirement_key, str(item.effective_value))
        for item in prepared
        if item.carry_status == OverrideCarryStatus.CARRIED_FORWARD.value
        and item.field_name == "evidence_unlink"
    }
    return [
        link
        for link in links
        if (link.requirement_id.removeprefix("req:"), link.evidence_id) not in removed
        and not any(
            item.field_name == "evidence_unlink"
            and item.carry_status == OverrideCarryStatus.CARRIED_FORWARD.value
            and item.requirement_key in {
                link.requirement_id,
                link.requirement_id.removeprefix("req:"),
            }
            and str(item.effective_value) == link.evidence_id
            for item in prepared
        )
    ]


def _reconstruct_source(
    db: Session,
    source: RoleMatchAnalysis,
) -> tuple[
    list[RequirementCluster],
    list[RequirementAssessment],
    list[EvidenceCatalogItem],
]:
    requirements = (
        db.query(RoleMatchRequirement)
        .filter_by(analysis_id=source.id)
        .order_by(RoleMatchRequirement.sort_order.asc())
        .all()
    )
    evidence_rows = (
        db.query(RoleMatchEvidence)
        .filter_by(analysis_id=source.id)
        .order_by(RoleMatchEvidence.rank.asc())
        .all()
    )
    evidence_by_requirement: dict[int, list[RoleMatchEvidence]] = defaultdict(list)
    for row in evidence_rows:
        evidence_by_requirement[row.requirement_id].append(row)

    clusters: list[RequirementCluster] = []
    assessments: list[RequirementAssessment] = []
    catalog_by_id: dict[str, EvidenceCatalogItem] = {}
    for row in requirements:
        category = RequirementCategory(row.primary_category)
        importance = RequirementImportance(row.effective_importance)
        importance_mentions = {
            RequirementImportance(key): int(value)
            for key, value in _loads(row.importance_mentions, {}).items()
        }
        for importance_key in RequirementImportance:
            importance_mentions.setdefault(importance_key, 0)
        cluster = RequirementCluster(
            cluster_id=row.cluster_id,
            canonical_requirement=row.canonical_text,
            canonical_key=row.canonical_key,
            primary_category=category,
            importance=importance,
            mention_count=row.mention_count,
            importance_conflict=bool(row.importance_conflict),
            importance_mentions=importance_mentions,
            source_quotes=_loads(row.source_quotes, []),
            source_ids=[],
            is_eligibility=category == RequirementCategory.ELIGIBILITY,
            is_trainable=category == RequirementCategory.TRAINABLE,
            volatility=TechnologyVolatility(row.volatility),
            minimum_months=row.minimum_months,
            tool_specificity=row.tool_specificity,
            excluded=bool(row.excluded),
            exclusion_reason=row.exclusion_reason,
        )
        clusters.append(cluster)
        if row.match_level is None:
            continue
        links: list[EvidenceLink] = []
        for evidence in evidence_by_requirement[row.id]:
            source_type = EvidenceSource(evidence.source_type)
            catalog_by_id.setdefault(
                evidence.evidence_id,
                EvidenceCatalogItem(
                    evidence_id=evidence.evidence_id,
                    source=source_type,
                    text=evidence.source_text,
                ),
            )
            links.append(
                EvidenceLink(
                    requirement_id=row.cluster_id,
                    evidence_id=evidence.evidence_id,
                    source=source_type,
                    relationship=EvidenceRelationship(evidence.relationship),
                    depth=EvidenceDepth(evidence.depth),
                    volatility=TechnologyVolatility(row.volatility),
                    is_duplicate=bool(evidence.duplicate),
                    is_contradiction=bool(evidence.contradiction),
                    explanation=evidence.explanation or "",
                    precomputed_strength=evidence.base_strength,
                )
            )
        match_level = MatchLevel(row.match_level)
        assessments.append(
            RequirementAssessment(
                cluster_id=row.cluster_id,
                category=category,
                importance=importance,
                match_level=match_level,
                strength=row.strength,
                evidence_links=links,
                explanation=row.explanation or "",
                known=match_level != MatchLevel.UNKNOWN,
                confidence_evidence_count=len(
                    [link for link in links if not link.is_duplicate]
                ),
            )
        )
    return clusters, assessments, list(catalog_by_id.values())


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
    for assessment in assessments:
        links = [link for link in assessment.evidence_links if not link.is_duplicate]
        if links:
            values.append(max(SOURCE_MULTIPLIERS[link.source] for link in links))
        elif assessment.known and assessment.strength is not None:
            values.append(1.0)
    return sum(values) / len(values) if values else 0.0


def _summary(
    clusters: list[RequirementCluster],
    assessments: list[RequirementAssessment],
    display_score: int,
    score_band: str,
):
    cluster_map = {item.cluster_id: item for item in clusters}
    strengths: list[AnalysisInsight] = []
    concerns: list[AnalysisInsight] = []
    for assessment in assessments:
        cluster = cluster_map[assessment.cluster_id]
        if assessment.match_level in {MatchLevel.STRONG, MatchLevel.MODERATE}:
            strengths.append(
                AnalysisInsight(
                    title=cluster.canonical_requirement,
                    explanation="Supported by profile evidence.",
                )
            )
        elif assessment.match_level == MatchLevel.UNKNOWN:
            concerns.append(
                AnalysisInsight(
                    title=f"{cluster.canonical_requirement} needs confirmation",
                    explanation="Review the requirement and add truthful evidence when available.",
                )
            )
        else:
            concerns.append(
                AnalysisInsight(
                    title=f"{cluster.canonical_requirement} needs clearer evidence",
                    explanation="Add a concrete work or project example when factually accurate.",
                )
            )
    return present_analysis(
        display_score=display_score,
        score_band=score_band,
        strengths=strengths[:3],
        concerns=concerns[:3],
    )


def apply_user_overrides(
    db: Session,
    source_analysis_id: int,
    override_inputs: list[RoleMatchOverrideInput],
) -> RoleMatchAnalysis:
    source = db.query(RoleMatchAnalysis).filter_by(id=source_analysis_id).first()
    if source is None:
        raise RoleMatchAnalysisNotFoundError(source_analysis_id)

    clusters, assessments, catalog = _reconstruct_source(db, source)
    cluster_map = {item.canonical_key: item for item in clusters}
    assessment_map = {item.cluster_id: item for item in assessments}
    snapshot_overrides: list[SnapshotOverride] = []

    for request in override_inputs:
        cluster = cluster_map.get(request.requirement_key)
        if cluster is None:
            raise InvalidRequestError("Requirement was not found in this analysis")
        extracted_value: Any
        if request.field_name == "importance":
            extracted_value = cluster.importance.value
            try:
                importance = RequirementImportance(str(request.effective_value))
            except ValueError as exc:
                raise InvalidRequestError("Invalid requirement importance") from exc
            cluster = cluster.model_copy(update={"importance": importance})
            cluster_map[cluster.canonical_key] = cluster
            assessment = assessment_map.get(cluster.cluster_id)
            if assessment is not None:
                assessment_map[cluster.cluster_id] = assessment.model_copy(
                    update={"importance": importance}
                )
        elif request.field_name == "excluded":
            extracted_value = cluster.excluded
            if not isinstance(request.effective_value, bool):
                raise InvalidRequestError("Excluded override must be true or false")
            if (
                cluster.exclusion_reason == "potentially_non_job_related"
                and request.effective_value is False
            ):
                raise InvalidRequestError(
                    "Potentially non-job-related requirements cannot be restored to scoring"
                )
            cluster = cluster.model_copy(
                update={
                    "excluded": request.effective_value,
                    "exclusion_reason": (
                        "user_excluded" if request.effective_value else None
                    ),
                }
            )
            cluster_map[cluster.canonical_key] = cluster
            if request.effective_value:
                assessment_map.pop(cluster.cluster_id, None)
        elif request.field_name == "experience_status":
            assessment = assessment_map.get(cluster.cluster_id)
            extracted_value = assessment.match_level.value if assessment else "unknown"
            status = str(request.effective_value)
            if status == "no_experience":
                assessment_map[cluster.cluster_id] = RequirementAssessment(
                    cluster_id=cluster.cluster_id,
                    category=cluster.primary_category,
                    importance=cluster.importance,
                    match_level=MatchLevel.NO_EVIDENCE,
                    strength=0.0,
                    evidence_links=[],
                    explanation="The user confirmed they do not have this experience.",
                    known=True,
                )
            elif status == "not_in_profile":
                assessment_map[cluster.cluster_id] = RequirementAssessment(
                    cluster_id=cluster.cluster_id,
                    category=cluster.primary_category,
                    importance=cluster.importance,
                    match_level=MatchLevel.UNKNOWN,
                    strength=None,
                    evidence_links=[],
                    explanation="The user indicated this evidence is not included in the profile.",
                    known=False,
                )
            else:
                raise InvalidRequestError(
                    "Experience status must be no_experience or not_in_profile"
                )
        elif request.field_name == "evidence_unlink":
            evidence_id = str(request.effective_value)
            assessment = assessment_map.get(cluster.cluster_id)
            if assessment is None or not any(
                link.evidence_id == evidence_id for link in assessment.evidence_links
            ):
                raise InvalidRequestError("Evidence link was not found for this requirement")
            extracted_value = evidence_id
            remaining = [
                link for link in assessment.evidence_links if link.evidence_id != evidence_id
            ]
            if cluster.minimum_months is not None:
                replacement = RequirementAssessment(
                    cluster_id=cluster.cluster_id,
                    category=cluster.primary_category,
                    importance=cluster.importance,
                    match_level=MatchLevel.UNKNOWN,
                    strength=None,
                    evidence_links=remaining,
                    explanation="Duration needs review after evidence was unlinked.",
                    known=False,
                    confidence_evidence_count=len(remaining),
                )
            else:
                replacement = combine_evidence(remaining, cluster, source.analysis_date)
            assessment_map[cluster.cluster_id] = replacement
        else:
            raise InvalidRequestError("Unsupported role match override")

        snapshot_overrides.append(
            SnapshotOverride(
                requirement_key=cluster.canonical_key,
                field_name=request.field_name,
                extracted_value=extracted_value,
                effective_value=request.effective_value,
                reason=request.reason,
            )
        )

    updated_clusters = [cluster_map[item.canonical_key] for item in clusters]
    updated_assessments = [
        assessment_map[item.cluster_id]
        for item in updated_clusters
        if not item.excluded and item.cluster_id in assessment_map
    ]
    score = score_role_match(updated_assessments)
    known_coverage = _known_coverage(updated_assessments)
    conflict_rate = (
        sum(item.importance_conflict for item in updated_clusters)
        / max(len(updated_clusters), 1)
    )
    confidence = calculate_confidence(
        ConfidenceInputs(
            known_coverage=known_coverage,
            evidence_reliability=_reliability(updated_assessments),
            evidence_consistency=1.0 - min(conflict_rate, 1.0),
        )
    )
    display = decide_authoritative_display(
        known_coverage=known_coverage,
        confidence=confidence.score,
        conflict_rate=conflict_rate,
        requirement_count=len([item for item in updated_clusters if not item.excluded]),
        scoring_succeeded=True,
    )
    summary = _summary(
        updated_clusters,
        updated_assessments,
        score.display_score,
        score.score_band,
    )
    excluded_items = _loads(source.excluded_items, [])
    for item in updated_clusters:
        if item.excluded and not any(
            existing.get("text") == item.canonical_requirement
            for existing in excluded_items
        ):
            excluded_items.append(
                {
                    "source_id": item.cluster_id,
                    "text": item.canonical_requirement,
                    "reason": item.exclusion_reason or "user_excluded",
                }
            )

    return save_analysis_snapshot(
        db,
        SnapshotInput(
            profile_id=source.profile_id,
            application_id=source.application_id,
            parent_analysis_id=source.id,
            state="success" if display.show_score else "needs_review",
            job_description=source.job_description,
            safe_profile_json=source.safe_profile_snapshot,
            provider=source.model_provider,
            model_name=source.model_name,
            raw_llm_output=source.raw_llm_output,
            clusters=updated_clusters,
            assessments=updated_assessments,
            catalog=catalog,
            score=score,
            confidence=confidence,
            eligibility=EligibilityAssessment(
                status=EligibilityStatus(source.eligibility_status)
            ),
            show_authoritative_score=display.show_score,
            failure_code=None if display.show_score else display.reason,
            excluded_items=excluded_items,
            summary=summary,
            analysis_date=source.analysis_date,
            overrides=tuple(snapshot_overrides),
        ),
    )
