from __future__ import annotations

from typing import Literal

from sqlalchemy.orm import Session

from app.models import (
    AppSetting,
    Application,
    GeneratedCV,
    GeneratedCoverLetter,
    Profile,
    ProviderCredential,
)
from app.readiness.profile import parse_list
from app.readiness.schemas import OnboardingState
from app.services.settings import get_setting, set_setting

ONBOARDING_VERSION = "1"
ONBOARDING_VERSION_KEY = "onboarding_version_seen"
ONBOARDING_SKIPPED_KEY = "onboarding_skipped"
CHECKLIST_DISMISSED_KEY = "readiness_checklist_dismissed_fingerprint"


def _truthy_setting(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _profile_is_meaningful(profile: Profile) -> bool:
    scalar_fields = (
        profile.name,
        profile.email,
        profile.phone,
        profile.location,
        profile.linkedin,
        profile.github,
        profile.portfolio,
        profile.summary,
    )
    if any(bool((value or "").strip()) for value in scalar_fields):
        return True
    return any(
        parse_list(value)
        for value in (
            profile.work_experience,
            profile.education,
            profile.skills,
            profile.projects,
            profile.certifications,
        )
    )


def infer_installation_state(db: Session) -> Literal["fresh", "existing"]:
    if any(_profile_is_meaningful(profile) for profile in db.query(Profile).all()):
        return "existing"
    if db.query(GeneratedCV.id).first() is not None:
        return "existing"
    if db.query(GeneratedCoverLetter.id).first() is not None:
        return "existing"
    if db.query(Application.id).first() is not None:
        return "existing"
    if db.query(ProviderCredential.id).first() is not None:
        return "existing"

    settings = db.query(AppSetting).all()
    for setting in settings:
        if not (setting.value or "").strip():
            continue
        if setting.key == "llm_provider" or setting.key.startswith("selected_model_"):
            return "existing"
    return "fresh"


def get_or_initialize_onboarding_state(db: Session) -> OnboardingState:
    seen = get_setting(db, ONBOARDING_VERSION_KEY) == ONBOARDING_VERSION
    skipped = _truthy_setting(get_setting(db, ONBOARDING_SKIPPED_KEY))
    if seen:
        return OnboardingState(
            version=int(ONBOARDING_VERSION),
            seen=True,
            skipped=skipped,
            should_redirect=False,
        )

    if infer_installation_state(db) == "existing":
        set_setting(db, ONBOARDING_VERSION_KEY, ONBOARDING_VERSION)
        set_setting(db, ONBOARDING_SKIPPED_KEY, "false")
        return OnboardingState(
            version=int(ONBOARDING_VERSION),
            seen=True,
            skipped=False,
            should_redirect=False,
        )

    return OnboardingState(
        version=int(ONBOARDING_VERSION),
        seen=False,
        skipped=False,
        should_redirect=True,
    )


def mark_onboarding_skipped(db: Session) -> None:
    set_setting(db, ONBOARDING_VERSION_KEY, ONBOARDING_VERSION)
    set_setting(db, ONBOARDING_SKIPPED_KEY, "true")


def mark_onboarding_completed(db: Session) -> None:
    set_setting(db, ONBOARDING_VERSION_KEY, ONBOARDING_VERSION)
    set_setting(db, ONBOARDING_SKIPPED_KEY, "false")
