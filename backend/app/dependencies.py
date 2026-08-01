"""Shared FastAPI dependencies to reduce boilerplate across routes."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import APIKeyNotConfiguredError, ProfileNotFoundError
from app.models import Profile
from app.services.settings import get_llm_config, is_llm_configured


def get_profile_or_404(profile_id: int, db: Session = Depends(get_db)) -> Profile:
    """Fetch a Profile by ID or raise a typed 404 error."""
    profile = db.query(Profile).filter_by(id=profile_id).first()
    if not profile:
        raise ProfileNotFoundError(profile_id)
    return profile


def require_llm_config(db: Session = Depends(get_db)) -> tuple[str, str]:
    """Return (model_string, api_key) or raise when LLM is not configured."""
    model, api_key = get_llm_config(db)
    if not is_llm_configured(model, api_key):
        raise APIKeyNotConfiguredError(
            "LLM not configured. Select a model and add an API key when required."
        )
    return model, api_key
