from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.role_match.constants import PROMPT_VERSION, RULES_VERSION
from app.role_match.domain import (
    AnalysisSummary,
    ConfidenceAssessment,
    EligibilityAssessment,
    EvidenceCatalogItem,
    RequirementAssessment,
    RequirementCluster,
    ScoreResult,
)
from app.role_match.evidence_strength import calculate_base_strength, calculate_recency_multiplier
from app.role_match.models import (
    RoleMatchAnalysis,
    RoleMatchEvidence,
    RoleMatchOverride,
    RoleMatchRequirement,
)


@dataclass(frozen=True)
class SnapshotOverride:
    requirement_key: str
    field_name: str
    extracted_value: Any
    effective_value: Any
    reason: str
    source: str = "user"
    carry_status: str = "carried_forward"
    source_override_id: int | None = None


@dataclass(frozen=True)
class SnapshotInput:
    profile_id: int | None
    application_id: int | None
    parent_analysis_id: int | None
    state: str
    job_description: str
    safe_profile_json: str
    provider: str | None
    model_name: str | None
    raw_llm_output: str | None
    clusters: list[RequirementCluster]
    assessments: list[RequirementAssessment]
    catalog: list[EvidenceCatalogItem]
    score: ScoreResult | None
    confidence: ConfidenceAssessment | None
    eligibility: EligibilityAssessment
    show_authoritative_score: bool
    failure_code: str | None
    excluded_items: list[dict]
    summary: AnalysisSummary | None
    analysis_date: date
    overrides: tuple[SnapshotOverride, ...] = ()


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def save_analysis_snapshot(db: Session, value: SnapshotInput) -> RoleMatchAnalysis:
    normalized_payload = json.dumps(
        {
            "clusters": [item.model_dump(mode="json") for item in value.clusters],
            "summary": value.summary.model_dump(mode="json") if value.summary else None,
        },
        ensure_ascii=False,
    )
    scoring_payload = json.dumps(
        {
            "assessments": [item.model_dump(mode="json") for item in value.assessments],
            "score": value.score.model_dump(mode="json") if value.score else None,
            "confidence": value.confidence.model_dump(mode="json") if value.confidence else None,
            "eligibility": value.eligibility.model_dump(mode="json"),
        },
        ensure_ascii=False,
    )
    analysis = RoleMatchAnalysis(
        parent_analysis_id=value.parent_analysis_id,
        profile_id=value.profile_id,
        application_id=value.application_id,
        state=value.state,
        analysis_date=value.analysis_date,
        job_description=value.job_description,
        job_description_hash=_sha256(value.job_description),
        safe_profile_snapshot=value.safe_profile_json,
        safe_profile_hash=_sha256(value.safe_profile_json),
        rules_version=RULES_VERSION,
        prompt_version=PROMPT_VERSION,
        model_provider=value.provider,
        model_name=value.model_name,
        raw_llm_output=value.raw_llm_output,
        normalized_payload=normalized_payload,
        scoring_payload=scoring_payload,
        raw_score=value.score.raw_score if value.score else None,
        display_score=value.score.display_score if value.score and value.show_authoritative_score else None,
        score_band=value.score.score_band if value.score and value.show_authoritative_score else None,
        confidence_score=value.confidence.score if value.confidence else None,
        confidence_band=value.confidence.band.value if value.confidence else None,
        eligibility_status=value.eligibility.status.value,
        show_authoritative_score=value.show_authoritative_score,
        failure_code=value.failure_code,
        excluded_items=json.dumps(value.excluded_items, ensure_ascii=False),
    )
    db.add(analysis)
    db.flush()

    assessment_map = {item.cluster_id: item for item in value.assessments}
    catalog_map = {item.evidence_id: item for item in value.catalog}
    importance_overrides = {
        item.requirement_key: item
        for item in value.overrides
        if item.field_name == "importance" and item.carry_status == "carried_forward"
    }
    for index, cluster in enumerate(value.clusters):
        assessment = assessment_map.get(cluster.cluster_id)
        importance_override = importance_overrides.get(cluster.canonical_key)
        extracted_importance = (
            str(importance_override.extracted_value)
            if importance_override is not None
            else cluster.importance.value
        )
        requirement = RoleMatchRequirement(
            analysis_id=analysis.id,
            cluster_id=cluster.cluster_id,
            canonical_key=cluster.canonical_key,
            canonical_text=cluster.canonical_requirement,
            primary_category=cluster.primary_category.value,
            extracted_importance=extracted_importance,
            effective_importance=cluster.importance.value,
            mention_count=cluster.mention_count,
            importance_conflict=cluster.importance_conflict,
            importance_mentions=json.dumps(
                {key.value: count for key, count in cluster.importance_mentions.items()}
            ),
            source_quotes=json.dumps(cluster.source_quotes, ensure_ascii=False),
            volatility=cluster.volatility.value,
            minimum_months=cluster.minimum_months,
            tool_specificity=cluster.tool_specificity,
            excluded=cluster.excluded,
            exclusion_reason=cluster.exclusion_reason,
            match_level=assessment.match_level.value if assessment else None,
            strength=assessment.strength if assessment else None,
            explanation=assessment.explanation if assessment else None,
            sort_order=index,
        )
        db.add(requirement)
        db.flush()
        for rank, link in enumerate(assessment.evidence_links if assessment else []):
            item = catalog_map.get(link.evidence_id)
            if item is None:
                continue
            recency = calculate_recency_multiplier(
                link.volatility,
                link.last_used_date,
                value.analysis_date,
                is_current=link.is_current,
            )
            db.add(
                RoleMatchEvidence(
                    analysis_id=analysis.id,
                    requirement_id=requirement.id,
                    evidence_id=link.evidence_id,
                    source_type=link.source.value,
                    source_text=item.text,
                    relationship=link.relationship.value,
                    depth=link.depth.value,
                    recency_multiplier=recency,
                    base_strength=calculate_base_strength(link, value.analysis_date),
                    duplicate=link.is_duplicate,
                    contradiction=link.is_contradiction,
                    explanation=link.explanation,
                    rank=rank,
                )
            )

    for item in value.overrides:
        db.add(
            RoleMatchOverride(
                analysis_id=analysis.id,
                requirement_key=item.requirement_key,
                field_name=item.field_name,
                extracted_value=json.dumps(item.extracted_value, ensure_ascii=False),
                effective_value=json.dumps(item.effective_value, ensure_ascii=False),
                reason=item.reason,
                source=item.source,
                carry_status=item.carry_status,
                source_override_id=item.source_override_id,
            )
        )

    if value.parent_analysis_id:
        parent = db.query(RoleMatchAnalysis).filter_by(id=value.parent_analysis_id).first()
        if parent:
            parent.superseded_by_id = analysis.id
    db.commit()
    db.refresh(analysis)
    return analysis
