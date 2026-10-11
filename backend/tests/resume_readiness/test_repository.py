from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import configure_sqlite_security
from app.models import Base, GeneratedCV, Profile
from app.resume_readiness import models as readiness_models  # noqa: F401
from app.resume_readiness.domain import (
    AnalysisMode,
    AnalysisStatus,
    Category,
    CategoryResult,
    OverallResult,
    ReadinessResult,
    RuleResult,
)
from app.resume_readiness.models import (
    ResumeReadinessAnalysis,
    ResumeReadinessRuleResult,
)
from app.resume_readiness.repository import (
    create_analysis,
    get_latest_for_generated_cv,
    list_for_generated_cv,
)
from app.role_match import models as role_match_models  # noqa: F401


def make_session():
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", configure_sqlite_security)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _complete_result() -> ReadinessResult:
    parseability = CategoryResult(
        category=Category.PARSEABILITY,
        raw_score=95,
        score=95,
        band="excellent",
        score_cap=None,
    )
    quality = CategoryResult(
        category=Category.QUALITY,
        raw_score=80,
        score=80,
        band="good",
        score_cap=None,
    )
    return ReadinessResult(
        mode=AnalysisMode.GENERAL,
        status=AnalysisStatus.COMPLETE,
        overall=OverallResult(
            status=AnalysisStatus.COMPLETE,
            score=88,
            band="good",
        ),
        parseability=parseability,
        quality=quality,
        tailoring=None,
        rule_results=(
            RuleResult.passed(
                rule_id="PARSE-001",
                category=Category.PARSEABILITY,
                title="Text detected",
                explanation="Selectable text is available.",
            ),
        ),
    )


def test_old_generated_cv_requires_no_readiness_row():
    db = make_session()
    try:
        cv = GeneratedCV(profile_snapshot='{"name":"Edo","email":"e@example.com"}')
        db.add(cv)
        db.commit()

        assert get_latest_for_generated_cv(db, cv.id) is None
    finally:
        db.close()


def test_create_analysis_persists_rules_atomically():
    db = make_session()
    try:
        profile = Profile(
            name="Edo",
            email="e@example.com",
            work_experience="[]",
            education="[]",
            skills="[]",
            projects="[]",
            certifications="[]",
        )
        db.add(profile)
        db.flush()
        cv = GeneratedCV(
            profile_id=profile.id,
            profile_snapshot='{"name":"Edo","email":"e@example.com"}',
        )
        db.add(cv)
        db.commit()

        analysis = create_analysis(
            db,
            result=_complete_result(),
            generated_cv=cv,
            job_description_snapshot=None,
            role_match_analysis_id=None,
        )

        assert analysis.generated_cv_id == cv.id
        assert analysis.profile_id == profile.id
        assert len(analysis.rule_results) == 1
        assert analysis.rule_results[0].rule_id == "PARSE-001"
    finally:
        db.close()


def test_new_analysis_supersedes_previous_analysis():
    db = make_session()
    try:
        cv = GeneratedCV(profile_snapshot='{"name":"Edo","email":"e@example.com"}')
        db.add(cv)
        db.commit()

        first = create_analysis(
            db,
            result=_complete_result(),
            generated_cv=cv,
            job_description_snapshot=None,
            role_match_analysis_id=None,
        )
        second = create_analysis(
            db,
            result=_complete_result(),
            generated_cv=cv,
            job_description_snapshot=None,
            role_match_analysis_id=None,
        )

        assert second.supersedes_analysis_id == first.id
        assert [item.id for item in list_for_generated_cv(db, cv.id)] == [
            second.id,
            first.id,
        ]
    finally:
        db.close()


def test_deleting_generated_cv_cascades_analysis_and_rule_results():
    db = make_session()
    try:
        cv = GeneratedCV(profile_snapshot='{"name":"Edo","email":"e@example.com"}')
        db.add(cv)
        db.commit()
        create_analysis(
            db,
            result=_complete_result(),
            generated_cv=cv,
            job_description_snapshot=None,
            role_match_analysis_id=None,
        )

        assert db.query(ResumeReadinessAnalysis).count() == 1
        assert db.query(ResumeReadinessRuleResult).count() == 1

        db.delete(cv)
        db.commit()

        assert db.query(ResumeReadinessAnalysis).count() == 0
        assert db.query(ResumeReadinessRuleResult).count() == 0
    finally:
        db.close()
