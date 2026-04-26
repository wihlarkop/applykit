from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
from app.schemas import OnboardingStatusResponse, StatusResponse
from app.services.settings import get_llm_config

router = APIRouter()


@router.get("/onboarding", response_model=OnboardingStatusResponse)
def get_onboarding_status(db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.name.is_not(None), Profile.name != "").first()
    return OnboardingStatusResponse(is_onboarded=profile is not None)


@router.get("/status", response_model=StatusResponse)
def get_status(db: Session = Depends(get_db)):
    provider, api_key = get_llm_config(db)
    configured = bool(api_key and provider)
    return StatusResponse(
        api_key_configured=configured,
        provider=provider if configured else None,
    )
