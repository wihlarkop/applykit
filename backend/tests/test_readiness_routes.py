from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.exceptions import ProfileNotFoundError
from app.models import AppSetting, Base, Profile
from app.readiness.ai import record_active_connection_result, resolve_active_ai_configuration
from app.readiness.schemas import ReadinessProfileRequest
from app.routes.readiness import (
    complete_onboarding,
    dismiss_readiness_checklist,
    get_readiness,
    skip_onboarding,
)
from app.routes.profile import get_onboarding_status, get_status
from app.services.settings import set_provider_api_key


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def add_profile(db, *, ready=False, profile_id=1):
    profile = Profile(
        id=profile_id,
        label="Default",
        color="#6366f1",
        icon="💼",
        name="Wihlarko" if ready else "",
        email="w@example.com" if ready else "",
        work_experience=(
            '[{"company":"Example","role":"Engineer"}]' if ready else "[]"
        ),
        education="[]",
        skills='["Python"]' if ready else "[]",
        projects="[]",
        certifications="[]",
    )
    db.add(profile)
    db.commit()
    return profile


def configure_gemini(db):
    db.add(AppSetting(key="llm_provider", value="gemini/gemini-2.5-flash"))
    db.commit()
    set_provider_api_key(db, "gemini", "gemini-test-secret")


def mark_ai_ready(db):
    active = resolve_active_ai_configuration(db)
    assert active is not None
    record_active_connection_result(
        db,
        tested_config=active,
        ok=True,
        public_message="Connection verified.",
    )


def test_fresh_readiness_payload_matches_active_profile() -> None:
    db = make_session()
    try:
        add_profile(db)
        response = get_readiness(1, db)
        assert response.onboarding.seen is False
        assert response.onboarding.should_redirect is True
        assert response.profile.profile_id == 1
        assert response.profile.ready is False
        assert response.ai.status == "not_configured"
        assert response.applykit_ready is False
        assert response.checklist_visible is True
        assert len(response.checklist_fingerprint) == 64
    finally:
        db.close()


def test_existing_installation_does_not_redirect_and_requires_retest() -> None:
    db = make_session()
    try:
        add_profile(db, ready=True)
        configure_gemini(db)
        response = get_readiness(1, db)
        assert response.onboarding.seen is True
        assert response.onboarding.should_redirect is False
        assert response.ai.status == "retest_required"
    finally:
        db.close()


def test_missing_profile_uses_existing_404_contract() -> None:
    db = make_session()
    try:
        try:
            get_readiness(999, db)
        except ProfileNotFoundError as exc:
            assert exc.status_code == 404
        else:
            raise AssertionError("missing profile should raise ProfileNotFoundError")
    finally:
        db.close()


def test_skip_marks_seen_without_blocking_readiness() -> None:
    db = make_session()
    try:
        add_profile(db)
        response = skip_onboarding(ReadinessProfileRequest(profile_id=1), db)
        assert response.onboarding.seen is True
        assert response.onboarding.skipped is True
        assert response.onboarding.should_redirect is False
        assert response.applykit_ready is False
    finally:
        db.close()


def test_complete_only_marks_seen_when_both_checks_are_ready() -> None:
    db = make_session()
    try:
        add_profile(db, ready=True)
        configure_gemini(db)

        before = complete_onboarding(ReadinessProfileRequest(profile_id=1), db)
        assert before.onboarding.seen is True  # existing-install compatibility inference
        assert before.applykit_ready is False

        mark_ai_ready(db)
        completed = complete_onboarding(ReadinessProfileRequest(profile_id=1), db)
        assert completed.applykit_ready is True
        assert completed.onboarding.seen is True
        assert completed.onboarding.skipped is False
    finally:
        db.close()


def test_dismissal_hides_only_the_same_fingerprint() -> None:
    db = make_session()
    try:
        add_profile(db)
        initial = get_readiness(1, db)
        dismissed = dismiss_readiness_checklist(
            ReadinessProfileRequest(profile_id=1), db
        )
        assert dismissed.checklist_visible is False
        assert dismissed.checklist_fingerprint == initial.checklist_fingerprint

        profile = db.query(Profile).filter_by(id=1).one()
        profile.name = "Wihlarko"
        db.commit()
        changed = get_readiness(1, db)
        assert changed.checklist_fingerprint != initial.checklist_fingerprint
        assert changed.checklist_visible is True
    finally:
        db.close()


def test_ai_fingerprint_change_reopens_dismissed_checklist() -> None:
    db = make_session()
    try:
        add_profile(db, ready=True)
        configure_gemini(db)
        mark_ai_ready(db)
        dismissed = dismiss_readiness_checklist(
            ReadinessProfileRequest(profile_id=1), db
        )
        assert dismissed.checklist_visible is False

        setting = db.query(AppSetting).filter_by(key="llm_provider").one()
        setting.value = "gemini/gemini-2.0-flash"
        db.commit()
        changed = get_readiness(1, db)
        assert changed.ai.status == "configuration_changed"
        assert changed.checklist_visible is True
    finally:
        db.close()


def test_legacy_status_routes_remain_compatible() -> None:
    db = make_session()
    try:
        add_profile(db, ready=True)
        configure_gemini(db)
        assert get_onboarding_status(db).is_onboarded is True
        status = get_status(db)
        assert status.api_key_configured is True
        assert status.provider == "gemini/gemini-2.5-flash"
    finally:
        db.close()
