import hashlib
import json
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.exceptions import InvalidRequestError
from app.models import Application, Base, GeneratedCoverLetter, Profile
from app.role_match.integration import (
    build_cover_letter_role_match_context,
    enrich_cover_letter_role_match,
    resolve_application_match_scores,
)
from app.role_match.models import RoleMatchAnalysis


def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def add_profile(db, profile_id: int = 1) -> Profile:
    profile = Profile(
        id=profile_id,
        label="Default",
        color="#6366f1",
        icon="💼",
        name="Candidate",
        email="candidate@example.com",
    )
    db.add(profile)
    db.flush()
    return profile


def add_application(db, profile_id: int = 1) -> Application:
    application = Application(
        company_name="Example",
        role_title="Backend Engineer",
        status="applied",
        profile_id=profile_id,
        job_description="Python backend role",
    )
    db.add(application)
    db.flush()
    return application


def add_analysis(
    db,
    *,
    profile_id: int,
    job_description: str = "Python backend role",
    application_id: int | None = None,
    score: int | None = 80,
    authoritative: bool = True,
    created_at: datetime | None = None,
) -> RoleMatchAnalysis:
    summary = {
        "headline": "Your profile is a strong match",
        "description": "Strong Python backend evidence.",
        "strengths": [
            {
                "title": "Production Python backend capability",
                "explanation": "Supported by recent work evidence.",
                "evidence_label": "Work experience",
            }
        ],
        "concerns": [],
        "next_step": "Use the production Python example in your application.",
    }
    analysis = RoleMatchAnalysis(
        profile_id=profile_id,
        application_id=application_id,
        created_at=created_at or datetime.now(UTC),
        analysis_date=date(2026, 8, 6),
        state="success" if authoritative else "needs_review",
        job_description=job_description,
        job_description_hash=hashlib.sha256(job_description.encode()).hexdigest(),
        safe_profile_snapshot="{}",
        safe_profile_hash=hashlib.sha256(b"{}").hexdigest(),
        rules_version="role-match-v1",
        prompt_version="role-match-extraction-v1",
        model_provider="openai",
        model_name="model",
        raw_llm_output="{}",
        normalized_payload=json.dumps({"clusters": [], "summary": summary}),
        scoring_payload="{}",
        raw_score=float(score) if score is not None else None,
        display_score=score if authoritative else None,
        score_band="strong_evidence_match" if authoritative else None,
        confidence_score=0.8,
        confidence_band="high",
        eligibility_status="likely_eligible",
        show_authoritative_score=authoritative,
        failure_code=None if authoritative else "insufficient_known_coverage",
        excluded_items="[]",
    )
    db.add(analysis)
    db.flush()
    return analysis


def add_cover_letter(
    db,
    *,
    profile_id: int,
    application_id: int | None,
    legacy_score: int | None,
    role_match_analysis_id: int | None = None,
    created_at: datetime | None = None,
) -> GeneratedCoverLetter:
    entry = GeneratedCoverLetter(
        created_at=created_at or datetime.now(UTC),
        company_name="Example",
        role_title="Backend Engineer",
        job_description="Python backend role",
        cover_letter_text="Hello",
        profile_id=profile_id,
        application_id=application_id,
        role_match_analysis_id=role_match_analysis_id,
        match_score=legacy_score,
        tone="professional",
    )
    db.add(entry)
    db.flush()
    return entry


def test_cover_letter_context_uses_server_analysis_values() -> None:
    db = db_session()
    add_profile(db)
    analysis = add_analysis(db, profile_id=1, score=80)

    context = build_cover_letter_role_match_context(
        db,
        analysis_id=analysis.id,
        profile_id=1,
        job_description="Python backend role",
    )

    assert context.analysis_id == analysis.id
    assert context.match_score == 80
    assert "Production Python backend capability" in context.fit_context
    assert "Use the production Python example" in context.fit_context


def test_cover_letter_context_rejects_wrong_profile() -> None:
    db = db_session()
    add_profile(db, 1)
    add_profile(db, 2)
    analysis = add_analysis(db, profile_id=1)

    with pytest.raises(InvalidRequestError, match="same profile"):
        build_cover_letter_role_match_context(
            db,
            analysis_id=analysis.id,
            profile_id=2,
            job_description="Python backend role",
        )


def test_cover_letter_context_rejects_changed_job_description() -> None:
    db = db_session()
    add_profile(db)
    analysis = add_analysis(db, profile_id=1)

    with pytest.raises(InvalidRequestError, match="job description"):
        build_cover_letter_role_match_context(
            db,
            analysis_id=analysis.id,
            profile_id=1,
            job_description="Different role",
        )


def test_non_authoritative_analysis_links_without_exposing_score() -> None:
    db = db_session()
    add_profile(db)
    analysis = add_analysis(db, profile_id=1, authoritative=False)

    context = build_cover_letter_role_match_context(
        db,
        analysis_id=analysis.id,
        profile_id=1,
        job_description="Python backend role",
    )

    assert context.analysis_id == analysis.id
    assert context.match_score is None
    assert context.fit_context is None


def test_history_labels_evidence_and_legacy_scores() -> None:
    db = db_session()
    add_profile(db)
    analysis = add_analysis(db, profile_id=1, score=80)
    modern = add_cover_letter(
        db,
        profile_id=1,
        application_id=None,
        legacy_score=99,
        role_match_analysis_id=analysis.id,
    )
    legacy = add_cover_letter(
        db,
        profile_id=1,
        application_id=None,
        legacy_score=72,
    )

    modern_payload = enrich_cover_letter_role_match(db, modern)
    legacy_payload = enrich_cover_letter_role_match(db, legacy)

    assert modern_payload["match_score"] == 80
    assert modern_payload["match_score_source"] == "role_evidence_match"
    assert modern_payload["role_match_analysis_id"] == analysis.id
    assert modern_payload["role_match_analysis"]["confidence"] == "high"
    assert legacy_payload["match_score"] == 72
    assert legacy_payload["match_score_source"] == "legacy_llm_score"
    assert legacy_payload["role_match_analysis"] is None


def test_application_prefers_latest_direct_authoritative_analysis() -> None:
    db = db_session()
    add_profile(db)
    application = add_application(db)
    old = datetime.now(UTC) - timedelta(days=2)
    linked_analysis = add_analysis(
        db,
        profile_id=1,
        application_id=None,
        score=75,
        created_at=old,
    )
    add_cover_letter(
        db,
        profile_id=1,
        application_id=application.id,
        legacy_score=95,
        role_match_analysis_id=linked_analysis.id,
        created_at=old,
    )
    direct = add_analysis(
        db,
        profile_id=1,
        application_id=application.id,
        score=85,
        created_at=datetime.now(UTC),
    )

    resolved = resolve_application_match_scores(db, [application.id])

    assert resolved[application.id].score == 85
    assert resolved[application.id].source == "role_evidence_match"
    assert resolved[application.id].analysis_id == direct.id


def test_application_uses_cover_letter_analysis_before_legacy_score() -> None:
    db = db_session()
    add_profile(db)
    application = add_application(db)
    analysis = add_analysis(db, profile_id=1, score=80)
    add_cover_letter(
        db,
        profile_id=1,
        application_id=application.id,
        legacy_score=95,
        role_match_analysis_id=analysis.id,
    )

    resolved = resolve_application_match_scores(db, [application.id])

    assert resolved[application.id].score == 80
    assert resolved[application.id].source == "role_evidence_match"


def test_non_authoritative_analysis_does_not_replace_legacy_score() -> None:
    db = db_session()
    add_profile(db)
    application = add_application(db)
    analysis = add_analysis(db, profile_id=1, authoritative=False)
    add_cover_letter(
        db,
        profile_id=1,
        application_id=application.id,
        legacy_score=70,
        role_match_analysis_id=analysis.id,
    )

    resolved = resolve_application_match_scores(db, [application.id])

    assert resolved[application.id].score == 70
    assert resolved[application.id].source == "legacy_llm_score"
    assert resolved[application.id].analysis_id is None
