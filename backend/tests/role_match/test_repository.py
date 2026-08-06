from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.role_match.domain import (
    AnalysisState,
    AnalysisSummary,
    ConfidenceAssessment,
    ConfidenceBand,
    EligibilityAssessment,
    EligibilityStatus,
    ScoreResult,
)
from app.role_match.repository import compare_analyses, list_versions, serialize_analysis
from app.role_match.snapshots import SnapshotInput, save_analysis_snapshot


def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def save(db, *, parent=None, score=80):
    return save_analysis_snapshot(
        db,
        SnapshotInput(
            profile_id=None,
            application_id=None,
            parent_analysis_id=parent.id if parent else None,
            state=AnalysisState.SUCCESS.value,
            job_description="Python backend role",
            safe_profile_json='{"skills":["Python"]}',
            provider="openai",
            model_name="model",
            raw_llm_output="{}",
            clusters=[],
            assessments=[],
            catalog=[],
            score=ScoreResult(
                category_assessments=[],
                raw_score=float(score),
                capped_score=float(score),
                display_score=score,
                score_band="strong_evidence_match",
            ),
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
                headline="Your profile is a strong match",
                description="Strong evidence",
                next_step="Apply",
            ),
            analysis_date=date(2026, 8, 6),
        ),
    )


def test_serialize_analysis_exposes_human_summary() -> None:
    db = db_session()
    analysis = save(db)
    response = serialize_analysis(db, analysis)
    assert response.score == 80
    assert response.summary is not None
    assert response.summary.headline == "Your profile is a strong match"
    assert response.requirements == []


def test_versions_follow_immutable_parent_chain() -> None:
    db = db_session()
    parent = save(db, score=70)
    child = save(db, parent=parent, score=80)
    response = list_versions(db, child)
    assert [item.id for item in response.items] == [parent.id, child.id]
    db.refresh(parent)
    assert parent.superseded_by_id == child.id


def test_compare_reports_score_change() -> None:
    db = db_session()
    before = save(db, score=70)
    after = save(db, parent=before, score=80)
    response = compare_analyses(db, before, after)
    assert response.score_change == 10
    assert response.added_requirements == []
    assert response.removed_requirements == []
