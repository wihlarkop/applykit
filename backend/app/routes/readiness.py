from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_profile_or_404
from app.readiness.ai import evaluate_ai_readiness
from app.readiness.onboarding import (
    CHECKLIST_DISMISSED_KEY,
    get_or_initialize_onboarding_state,
    mark_onboarding_completed,
    mark_onboarding_skipped,
)
from app.readiness.profile import evaluate_profile
from app.readiness.schemas import ReadinessProfileRequest, ReadinessResponse
from app.services.settings import get_setting, set_setting

router = APIRouter()


def _checklist_fingerprint(profile, ai) -> str:
    payload = {
        "profile_id": profile.profile_id,
        "profile_ready": profile.ready,
        "profile_missing": profile.missing_requirements,
        "ai_ready": ai.ready,
        "ai_status": ai.status.value,
        "ai_configuration_fingerprint": ai.configuration_fingerprint,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_readiness_response(db: Session, profile_id: int) -> ReadinessResponse:
    profile_model = get_profile_or_404(profile_id, db)
    onboarding = get_or_initialize_onboarding_state(db)
    profile = evaluate_profile(profile_model)
    ai = evaluate_ai_readiness(db)
    applykit_ready = profile.ready and ai.ready
    fingerprint = _checklist_fingerprint(profile, ai)
    dismissed = get_setting(db, CHECKLIST_DISMISSED_KEY)
    return ReadinessResponse(
        onboarding=onboarding,
        profile=profile,
        ai=ai,
        applykit_ready=applykit_ready,
        checklist_visible=dismissed != fingerprint,
        checklist_fingerprint=fingerprint,
    )


@router.get("/readiness", response_model=ReadinessResponse)
def get_readiness(
    profile_id: int,
    db: Session = Depends(get_db),
) -> ReadinessResponse:
    return build_readiness_response(db, profile_id)


@router.post("/readiness/onboarding/skip", response_model=ReadinessResponse)
def skip_onboarding(
    req: ReadinessProfileRequest,
    db: Session = Depends(get_db),
) -> ReadinessResponse:
    get_profile_or_404(req.profile_id, db)
    mark_onboarding_skipped(db)
    return build_readiness_response(db, req.profile_id)


@router.post("/readiness/onboarding/complete", response_model=ReadinessResponse)
def complete_onboarding(
    req: ReadinessProfileRequest,
    db: Session = Depends(get_db),
) -> ReadinessResponse:
    current = build_readiness_response(db, req.profile_id)
    if current.applykit_ready:
        mark_onboarding_completed(db)
        return build_readiness_response(db, req.profile_id)
    return current


@router.post("/readiness/checklist/dismiss", response_model=ReadinessResponse)
def dismiss_readiness_checklist(
    req: ReadinessProfileRequest,
    db: Session = Depends(get_db),
) -> ReadinessResponse:
    current = build_readiness_response(db, req.profile_id)
    set_setting(db, CHECKLIST_DISMISSED_KEY, current.checklist_fingerprint)
    return build_readiness_response(db, req.profile_id)
