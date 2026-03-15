import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
from app.schemas import OnboardingStatusResponse, StatusResponse

router = APIRouter()


@router.get("/onboarding", response_model=OnboardingStatusResponse)
def get_onboarding_status(db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.name != None, Profile.name != "").first()
    is_onboarded = profile is not None
    return OnboardingStatusResponse(is_onboarded=is_onboarded)


@router.get("/status", response_model=StatusResponse)
def get_status():
    api_key = os.getenv("LLM_API_KEY", "").strip()
    provider = os.getenv("LLM_PROVIDER", "").strip()
    configured = bool(api_key and provider)
    return StatusResponse(
        api_key_configured=configured,
        provider=provider if configured else None,
    )
