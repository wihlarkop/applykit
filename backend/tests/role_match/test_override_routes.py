from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.role_match.api_schemas import (
    RoleMatchOverrideInput,
    RoleMatchOverridesRequest,
)
from app.role_match.domain import (
    AnalysisSummary,
    ConfidenceAssessment,
    ConfidenceBand,
    EligibilityAssessment,
    EligibilityStatus,
    RequirementAssessment,
    RequirementCategory,
    RequirementCluster,
    RequirementImportance,
    TechnologyVolatility,
)
from app.role_match.scoring import score_role_match
from app.role_match.snapshots import SnapshotInput, save_analysis_snapshot
from app.routes.analyze import apply_role_match_overrides


def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def source_analysis(db):
    cluster = RequirementCluster(
        cluster_id="req:terraform",
        canonical_requirement="Terraform experience",
        canonical_key="terraform",
        primary_category=RequirementCategory.RELEVANT_COMPETENCIES,
        importance=RequirementImportance.CRITICAL,
        mention_count=1,
        importance_conflict=False,
        importance_mentions={
            RequirementImportance.CRITICAL: 1,
            RequirementImportance.IMPORTANT: 0,
            RequirementImportance.SUPPORTING: 0,
        },
        source_quotes=["Terraform experience"],
        source_ids=["jd:terraform"],
        is_eligibility=False,
        is_trainable=False,
        volatility=TechnologyVolatility.EVOLVING,
        tool_specificity="capability",
    )
    assessment = RequirementAssessment(
        cluster_id=cluster.cluster_id,
        category=cluster.primary_category,
        importance=cluster.importance,
        match_level="no_evidence",
        strength=0.0,
        known=True,
    )
    score = score_role_match([assessment])
    return save_analysis_snapshot(
        db,
        SnapshotInput(
            profile_id=None,
            application_id=None,
            parent_analysis_id=None,
            state="needs_review",
            job_description="Terraform role",
            safe_profile_json="{}",
            provider="openai",
            model_name="model",
            raw_llm_output="{}",
            clusters=[cluster],
            assessments=[assessment],
            catalog=[],
            score=score,
            confidence=ConfidenceAssessment(
                score=0.6,
                band=ConfidenceBand.MEDIUM,
                explanation="Limited evidence",
            ),
            eligibility=EligibilityAssessment(
                status=EligibilityStatus.LIKELY_ELIGIBLE
            ),
            show_authoritative_score=False,
            failure_code="insufficient_requirements",
            excluded_items=[],
            summary=AnalysisSummary(
                headline="Analysis needs review",
                description="Review extracted requirements.",
                next_step="Review Terraform.",
            ),
            analysis_date=date(2026, 8, 6),
        ),
    )


def test_override_route_returns_new_immutable_snapshot() -> None:
    db = db_session()
    parent = source_analysis(db)
    response = apply_role_match_overrides(
        parent.id,
        RoleMatchOverridesRequest(
            overrides=[
                RoleMatchOverrideInput(
                    requirement_key="terraform",
                    field_name="importance",
                    effective_value="supporting",
                    reason="Listed as preferred",
                )
            ]
        ),
        db,
    )
    assert response.id != parent.id
    assert response.parent_analysis_id == parent.id
    assert response.requirements[0].importance == "supporting"
