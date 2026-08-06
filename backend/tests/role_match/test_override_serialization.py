from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.role_match.api_schemas import RoleMatchOverrideInput
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
from app.role_match.overrides import apply_user_overrides
from app.role_match.repository import serialize_analysis
from app.role_match.scoring import score_role_match
from app.role_match.snapshots import SnapshotInput, save_analysis_snapshot


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


def test_serialized_analysis_exposes_override_audit_fields() -> None:
    db = db_session()
    parent = source_analysis(db)
    child = apply_user_overrides(
        db,
        parent.id,
        [
            RoleMatchOverrideInput(
                requirement_key="terraform",
                field_name="importance",
                effective_value="supporting",
                reason="Listed as preferred",
            )
        ],
    )
    response = serialize_analysis(db, child)
    assert len(response.overrides) == 1
    override = response.overrides[0]
    assert override.requirement_key == "terraform"
    assert override.field_name == "importance"
    assert override.extracted_value == "critical"
    assert override.effective_value == "supporting"
    assert override.reason == "Listed as preferred"
    assert override.carry_status == "carried_forward"
