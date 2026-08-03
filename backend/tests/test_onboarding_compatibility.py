from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    AppSetting,
    Application,
    Base,
    GeneratedCV,
    GeneratedCoverLetter,
    Profile,
    ProviderCredential,
)
from app.readiness.onboarding import (
    ONBOARDING_INSTALLATION_KEY,
    ONBOARDING_VERSION_KEY,
    get_or_initialize_onboarding_state,
    infer_installation_state,
    mark_onboarding_completed,
    mark_onboarding_skipped,
)
from app.services.settings import get_setting


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def empty_profile() -> Profile:
    return Profile(
        label="Default",
        color="#6366f1",
        icon="💼",
        name="",
        email="",
        work_experience="[]",
        education="[]",
        skills="[]",
        projects="[]",
        certifications="[]",
    )


def test_auto_created_empty_default_profile_is_still_fresh() -> None:
    db = make_session()
    try:
        db.add(empty_profile())
        db.commit()
        assert infer_installation_state(db) == "fresh"
        state = get_or_initialize_onboarding_state(db)
        assert state.seen is False
        assert state.should_redirect is True
        assert get_setting(db, ONBOARDING_VERSION_KEY) is None
    finally:
        db.close()


def test_fresh_classification_is_persisted_before_setup_data_changes() -> None:
    db = make_session()
    try:
        profile = empty_profile()
        db.add(profile)
        db.commit()

        first = get_or_initialize_onboarding_state(db)
        assert first.seen is False
        assert first.should_redirect is True
        assert get_setting(db, ONBOARDING_INSTALLATION_KEY) == "fresh"

        profile.name = "Wihlarko"
        profile.email = "w@example.com"
        profile.skills = '["Python"]'
        profile.work_experience = '[{"company":"Example","role":"Engineer"}]'
        db.add(AppSetting(key="llm_provider", value="ollama/llama3.2"))
        db.commit()

        second = get_or_initialize_onboarding_state(db)
        assert second.seen is False
        assert second.should_redirect is True
        assert get_setting(db, ONBOARDING_VERSION_KEY) is None
    finally:
        db.close()


def test_meaningful_profile_marks_installation_existing() -> None:
    db = make_session()
    try:
        profile = empty_profile()
        profile.name = "Wihlarko"
        db.add(profile)
        db.commit()
        assert infer_installation_state(db) == "existing"
    finally:
        db.close()


def test_generated_cv_marks_installation_existing() -> None:
    db = make_session()
    try:
        db.add(GeneratedCV(profile_snapshot="{}", enhanced=0))
        db.commit()
        assert infer_installation_state(db) == "existing"
    finally:
        db.close()


def test_generated_cover_letter_marks_installation_existing() -> None:
    db = make_session()
    try:
        db.add(
            GeneratedCoverLetter(
                job_description="Job",
                cover_letter_text="Letter",
                tone="professional",
            )
        )
        db.commit()
        assert infer_installation_state(db) == "existing"
    finally:
        db.close()


def test_application_marks_installation_existing() -> None:
    db = make_session()
    try:
        db.add(Application(company_name="Example", role_title="Engineer"))
        db.commit()
        assert infer_installation_state(db) == "existing"
    finally:
        db.close()


def test_saved_model_marks_installation_existing() -> None:
    db = make_session()
    try:
        db.add(AppSetting(key="selected_model_gemini", value="gemini/gemini-2.5-flash"))
        db.commit()
        assert infer_installation_state(db) == "existing"
    finally:
        db.close()


def test_provider_credential_marks_installation_existing() -> None:
    db = make_session()
    try:
        db.add(
            ProviderCredential(
                provider_id="gemini",
                label="Legacy",
                encrypted_secret="ciphertext",
                masked_secret="****1234",
                fingerprint="f" * 64,
                version=1,
                is_active=True,
                is_enabled=True,
                priority=1,
                health_status="healthy",
            )
        )
        db.commit()
        assert infer_installation_state(db) == "existing"
    finally:
        db.close()


def test_existing_installation_is_initialized_once_without_redirect() -> None:
    db = make_session()
    try:
        profile = empty_profile()
        profile.email = "w@example.com"
        db.add(profile)
        db.commit()

        first = get_or_initialize_onboarding_state(db)
        second = get_or_initialize_onboarding_state(db)

        assert first.seen is True
        assert first.skipped is False
        assert first.should_redirect is False
        assert second == first
        assert get_setting(db, ONBOARDING_INSTALLATION_KEY) == "existing"
        assert get_setting(db, ONBOARDING_VERSION_KEY) == "1"
    finally:
        db.close()


def test_skip_and_complete_are_global_and_idempotent() -> None:
    db = make_session()
    try:
        mark_onboarding_skipped(db)
        skipped = get_or_initialize_onboarding_state(db)
        assert skipped.seen is True
        assert skipped.skipped is True
        assert skipped.should_redirect is False

        mark_onboarding_completed(db)
        completed = get_or_initialize_onboarding_state(db)
        assert completed.seen is True
        assert completed.skipped is False
        assert completed.should_redirect is False
    finally:
        db.close()
