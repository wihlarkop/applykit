from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.role_match.api_schemas import RoleMatchOverrideInput
from app.role_match.domain import (
    AnalysisInsight,
    AnalysisSummary,
    ConfidenceAssessment,
    ConfidenceBand,
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
from app.role_match.models import RoleMatchOverride, RoleMatchRequirement
from app.role_match.overrides import apply_user_overrides, classify_override_carry
from app.role_match.scoring import score_role_match
from app.role_match.snapshots import SnapshotInput, save_analysis_snapshot


def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def cluster(key: str, text: str, importance: RequirementImportance) -> RequirementCluster:
    return RequirementCluster(
        cluster_id=f"req:{key}",
        canonical_requirement=text,
        canonical_key=key,
        primary_category=RequirementCategory.RELEVANT_COMPETENCIES,
        importance=importance,
        mention_count=1,
        importance_conflict=False,
        importance_mentions={
            RequirementImportance.CRITICAL: int(importance == RequirementImportance.CRITICAL),
            RequirementImportance.IMPORTANT: int(importance == RequirementImportance.IMPORTANT),
            RequirementImportance.SUPPORTING: int(importance == RequirementImportance.SUPPORTING),
        },
        source_quotes=[text],
        source_ids=[f"jd:{key}"],
        is_eligibility=False,
        is_trainable=False,
        volatility=TechnologyVolatility.EVOLVING,
        tool_specificity="capability",
    )


def save_source(db):
    python = cluster("python-backend", "Production Python backend capability", RequirementImportance.CRITICAL)
    terraform = cluster("terraform", "Terraform experience", RequirementImportance.CRITICAL)
    python_link = EvidenceLink(
        requirement_id=python.cluster_id,
        evidence_id="work:python",
        source=EvidenceSource.WORK_EXPERIENCE,
        relationship=EvidenceRelationship.EXACT,
        depth=EvidenceDepth.PRODUCTION_OWNERSHIP,
        is_current=True,
        precomputed_strength=1.0,
    )
    assessments = [
        RequirementAssessment(
            cluster_id=python.cluster_id,
            category=python.primary_category,
            importance=python.importance,
            match_level=MatchLevel.STRONG,
            strength=1.0,
            evidence_links=[python_link],
            known=True,
            confidence_evidence_count=1,
        ),
        RequirementAssessment(
            cluster_id=terraform.cluster_id,
            category=terraform.primary_category,
            importance=terraform.importance,
            match_level=MatchLevel.NO_EVIDENCE,
            strength=0.0,
            known=True,
        ),
    ]
    score = score_role_match(assessments)
    return save_analysis_snapshot(
        db,
        SnapshotInput(
            profile_id=None,
            application_id=None,
            parent_analysis_id=None,
            state="success",
            job_description="Python and Terraform backend role",
            safe_profile_json='{"skills":["Python"]}',
            provider="openai",
            model_name="model",
            raw_llm_output="{}",
            clusters=[python, terraform],
            assessments=assessments,
            catalog=[
                EvidenceCatalogItem(
                    evidence_id="work:python",
                    source=EvidenceSource.WORK_EXPERIENCE,
                    text="Built production Python services",
                )
            ],
            score=score,
            confidence=ConfidenceAssessment(
                score=0.8,
                band=ConfidenceBand.HIGH,
                explanation="Direct evidence",
            ),
            eligibility=EligibilityAssessment(
                status=EligibilityStatus.LIKELY_ELIGIBLE
            ),
            show_authoritative_score=True,
            failure_code=None,
            excluded_items=[],
            summary=AnalysisSummary(
                headline="Your profile is a moderate match",
                description="Mixed evidence",
                strengths=[
                    AnalysisInsight(
                        title="Production Python backend capability",
                        explanation="Supported by work evidence.",
                    )
                ],
                concerns=[
                    AnalysisInsight(
                        title="Terraform experience needs clearer evidence",
                        explanation="Add a truthful work example when available.",
                    )
                ],
                next_step="Clarify Terraform evidence.",
            ),
            analysis_date=date(2026, 8, 6),
        ),
    )


def test_user_override_creates_child_and_preserves_parent() -> None:
    db = db_session()
    parent = save_source(db)

    child = apply_user_overrides(
        db,
        parent.id,
        [
            RoleMatchOverrideInput(
                requirement_key="terraform",
                field_name="importance",
                effective_value="supporting",
                reason="The JD lists Terraform as preferred.",
            )
        ],
    )

    assert child.id != parent.id
    assert child.parent_analysis_id == parent.id
    parent_requirement = db.query(RoleMatchRequirement).filter_by(
        analysis_id=parent.id,
        canonical_key="terraform",
    ).one()
    child_requirement = db.query(RoleMatchRequirement).filter_by(
        analysis_id=child.id,
        canonical_key="terraform",
    ).one()
    assert parent_requirement.effective_importance == "critical"
    assert child_requirement.effective_importance == "supporting"
    assert child.raw_score > parent.raw_score
    override = db.query(RoleMatchOverride).filter_by(analysis_id=child.id).one()
    assert override.carry_status == "carried_forward"
    assert override.extracted_value == '"critical"'
    assert override.effective_value == '"supporting"'


def test_exact_override_carries_forward() -> None:
    status, target = classify_override_carry(
        previous_key="python-backend",
        previous_category="relevant_competencies",
        new_clusters=[
            cluster(
                "python-backend",
                "Production Python backend capability",
                RequirementImportance.CRITICAL,
            )
        ],
    )
    assert status == OverrideCarryStatus.CARRIED_FORWARD
    assert target == "python-backend"


def test_material_category_change_needs_review() -> None:
    changed = cluster(
        "python-backend",
        "Build production Python APIs",
        RequirementImportance.CRITICAL,
    ).model_copy(update={"primary_category": RequirementCategory.RELEVANT_WORK_TASKS})
    status, target = classify_override_carry(
        previous_key="python-backend",
        previous_category="relevant_competencies",
        new_clusters=[changed],
    )
    assert status == OverrideCarryStatus.NEEDS_REVIEW
    assert target == "python-backend"


def test_removed_requirement_is_not_applicable() -> None:
    status, target = classify_override_carry(
        previous_key="terraform",
        previous_category="relevant_competencies",
        new_clusters=[
            cluster(
                "python-backend",
                "Production Python backend capability",
                RequirementImportance.CRITICAL,
            )
        ],
    )
    assert status == OverrideCarryStatus.NOT_APPLICABLE
    assert target is None
