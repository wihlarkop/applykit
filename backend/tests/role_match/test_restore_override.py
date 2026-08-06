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
from app.role_match.models import RoleMatchOverride, RoleMatchRequirement
from app.role_match.overrides import apply_user_overrides
from app.role_match.restore import restore_user_override
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


def test_restore_override_creates_new_snapshot_from_original_values() -> None:
    db = db_session()
    original = source_analysis(db)
    overridden = apply_user_overrides(
        db,
        original.id,
        [
            RoleMatchOverrideInput(
                requirement_key="terraform",
                field_name="importance",
                effective_value="supporting",
                reason="Listed as preferred",
            )
        ],
    )
    override = db.query(RoleMatchOverride).filter_by(
        analysis_id=overridden.id
    ).one()

    restored = restore_user_override(db, overridden.id, override.id)

    assert restored.id not in {original.id, overridden.id}
    assert restored.parent_analysis_id == overridden.id
    requirement = db.query(RoleMatchRequirement).filter_by(
        analysis_id=restored.id,
        canonical_key="terraform",
    ).one()
    assert requirement.effective_importance == "critical"
    assert db.query(RoleMatchOverride).filter_by(analysis_id=restored.id).count() == 0
    assert restored.raw_score == original.raw_score
