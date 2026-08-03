from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.readiness.onboarding import get_or_initialize_onboarding_state
from app.schemas import OnboardingStatusResponse, StatusResponse
from app.services.settings import get_llm_config, is_llm_configured

router = APIRouter()


@router.get("/onboarding", response_model=OnboardingStatusResponse)
def get_onboarding_status(db: Session = Depends(get_db)):
    # Legacy projection: "onboarded" now means the guided setup has been seen
    # (or an existing installation was detected), not merely that a name exists.
    state = get_or_initialize_onboarding_state(db)
    return OnboardingStatusResponse(is_onboarded=state.seen)


@router.get("/status", response_model=StatusResponse)
def get_status(db: Session = Depends(get_db)):
    model, api_key = get_llm_config(db)
    configured = is_llm_configured(model, api_key)
    return StatusResponse(
        api_key_configured=configured,
        provider=model if configured else None,
    )
