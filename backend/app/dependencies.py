"""Shared FastAPI dependencies to reduce boilerplate across routes."""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
from app.services.settings import get_llm_config


def get_profile_or_404(profile_id: int, db: Session = Depends(get_db)) -> Profile:
    """Fetch a Profile by ID or raise 404. Use as a FastAPI dependency."""
    profile = db.query(Profile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Profile not found.", "code": "PROFILE_NOT_FOUND"},
        )
    return profile


def require_llm_config(db: Session = Depends(get_db)) -> tuple[str, str]:
    """Return (model_string, api_key) or raise 400 if LLM is not configured."""
    provider, api_key = get_llm_config(db)
    if not provider or not api_key:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "LLM not configured. Set provider and API key in Settings.",
                "code": "API_KEY_NOT_CONFIGURED",
            },
        )
    return provider, api_key
