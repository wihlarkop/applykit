from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, GeneratedCV
from app.resume_readiness import models as readiness_models  # noqa: F401
from app.resume_readiness.domain import (
    AnalysisMode,
    AnalysisStatus,
    Category,
    CategoryResult,
    OverallResult,
    ReadinessResult,
)
from app.resume_readiness.schemas import ResumeReadinessAnalyzeRequest
from app.routes import resume_readiness as routes
from app.role_match import models as role_match_models  # noqa: F401


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _result() -> ReadinessResult:
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
        rule_results=(),
    )


def test_create_general_readiness_analysis(monkeypatch):
    db = make_session()
    try:
        cv = GeneratedCV(
            profile_snapshot='{"name":"Edo","email":"edo@example.com"}'
        )
        db.add(cv)
        db.commit()
        monkeypatch.setattr(routes, "analyze_generated_cv", lambda value: _result())

        response = routes.create_resume_readiness_analysis(
            ResumeReadinessAnalyzeRequest(generated_cv_id=cv.id),
            db,
        )

        assert response.generated_cv_id == cv.id
        assert response.mode == "general"
        assert response.categories.tailoring is None
        assert response.overall.score == 88
    finally:
        db.close()


def test_latest_legacy_cv_without_analysis_returns_404():
    db = make_session()
    try:
        cv = GeneratedCV(profile_snapshot='{"name":"Edo","email":"e@example.com"}')
        db.add(cv)
        db.commit()

        try:
            routes.read_latest_resume_readiness(cv.id, db)
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 404
        else:
            raise AssertionError("Expected HTTP 404")
    finally:
        db.close()


def test_invalid_profile_snapshot_is_persisted_as_failed():
    db = make_session()
    try:
        cv = GeneratedCV(profile_snapshot="not-json")
        db.add(cv)
        db.commit()

        response = routes.create_resume_readiness_analysis(
            ResumeReadinessAnalyzeRequest(generated_cv_id=cv.id),
            db,
        )

        assert response.status == "failed"
        assert response.failure_code == "INVALID_PROFILE_SNAPSHOT"
        assert response.overall.score is None
    finally:
        db.close()


def test_deleted_source_profile_does_not_attach_unrelated_role_match(monkeypatch):
    analysis = SimpleNamespace(
        id=17,
        profile_id=99,
        job_description="Backend engineer role requiring Python and API design.",
    )
    monkeypatch.setattr(routes, "get_role_match_analysis", lambda db, value: analysis)
    monkeypatch.setattr(
        routes,
        "serialize_role_match_analysis",
        lambda db, value: {"id": value.id},
    )

    role_match, job_description, effective_id = routes._load_role_match(
        object(),
        role_match_analysis_id=17,
        generated_cv_profile_id=None,
        requested_job_description=None,
    )

    assert role_match is None
    assert effective_id is None
    assert job_description == analysis.job_description


def test_role_match_from_another_profile_is_rejected(monkeypatch):
    analysis = SimpleNamespace(
        id=17,
        profile_id=99,
        job_description="Backend engineer role requiring Python and API design.",
    )
    monkeypatch.setattr(routes, "get_role_match_analysis", lambda db, value: analysis)

    try:
        routes._load_role_match(
            object(),
            role_match_analysis_id=17,
            generated_cv_profile_id=1,
            requested_job_description=None,
        )
    except HTTPException as exc:
        assert exc.status_code == 422
        assert "different career profile" in str(exc.detail)
    else:
        raise AssertionError("Expected incompatible profile rejection")
