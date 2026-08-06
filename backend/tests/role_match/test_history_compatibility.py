import hashlib
import json
from datetime import UTC, date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, GeneratedCoverLetter, Profile
from app.role_match.integration import enrich_cover_letter_role_match
from app.role_match.models import RoleMatchAnalysis


def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_modern_history_includes_full_analysis_and_compatibility_payload() -> None:
    db = db_session()
    db.add(
        Profile(
            id=1,
            label="Default",
            color="#6366f1",
            icon="💼",
            name="Candidate",
            email="candidate@example.com",
        )
    )
    summary = {
        "headline": "Your profile is a strong match",
        "description": "Strong evidence.",
        "strengths": [
            {
                "title": "Python backend capability",
                "explanation": "Supported by work evidence.",
            }
        ],
        "concerns": [],
        "next_step": "Use the Python example.",
    }
    analysis = RoleMatchAnalysis(
        profile_id=1,
        created_at=datetime.now(UTC),
        analysis_date=date(2026, 8, 6),
        state="success",
        job_description="Python role",
        job_description_hash=hashlib.sha256(b"Python role").hexdigest(),
        safe_profile_snapshot="{}",
        safe_profile_hash=hashlib.sha256(b"{}").hexdigest(),
        rules_version="role-match-v1",
        prompt_version="role-match-extraction-v1",
        model_provider="openai",
        model_name="model",
        normalized_payload=json.dumps({"clusters": [], "summary": summary}),
        scoring_payload=json.dumps(
            {
                "score": {"category_assessments": []},
                "confidence": None,
                "eligibility": {"status": "likely_eligible", "reasons": []},
                "assessments": [],
            }
        ),
        raw_score=80.0,
        display_score=80,
        score_band="strong_evidence_match",
        confidence_score=0.8,
        confidence_band="high",
        eligibility_status="likely_eligible",
        show_authoritative_score=True,
        excluded_items="[]",
    )
    db.add(analysis)
    db.flush()
    entry = GeneratedCoverLetter(
        company_name="Example",
        job_description="Python role",
        cover_letter_text="Hello",
        profile_id=1,
        role_match_analysis_id=analysis.id,
    )
    db.add(entry)
    db.flush()

    payload = enrich_cover_letter_role_match(db, entry)

    assert payload["role_match_analysis"]["id"] == analysis.id
    assert payload["role_match_analysis"]["requirements"] == []
    assert payload["fit_analysis"]["role_match_analysis_id"] == analysis.id
    assert payload["fit_analysis"]["role_match_analysis"]["score"] == 80
    assert payload["fit_analysis"]["pros"] == ["Python backend capability"]
