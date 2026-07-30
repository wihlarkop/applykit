from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
from app.schemas import OnboardingStatusResponse, StatusResponse
from app.services.settings import get_llm_config, is_llm_configured

router = APIRouter()


@router.get("/onboarding", response_model=OnboardingStatusResponse)
def get_onboarding_status(db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.name.is_not(None), Profile.name != "").first()
    return OnboardingStatusResponse(is_onboarded=profile is not None)


@router.get("/status", response_model=StatusResponse)
def get_status(db: Session = Depends(get_db)):
    model, api_key = get_llm_config(db)
    configured = is_llm_configured(model, api_key)
    return StatusResponse(
        api_key_configured=configured,
        provider=model if configured else None,
    )
