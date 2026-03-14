import json
import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
from app.schemas import ProfileData, ProfileResponse, StatusResponse
from app.utils import profile_to_schema

router = APIRouter()


@router.get("/profile", response_model=ProfileResponse)
def get_profile(db: Session = Depends(get_db)):
    profile = db.query(Profile).filter_by(id=1).first()
    if not profile:
        return ProfileResponse(profile=None)
    return ProfileResponse(profile=profile_to_schema(profile))


@router.post("/profile", response_model=ProfileData)
def save_profile(data: ProfileData, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter_by(id=1).first()
    fields = data.model_dump(exclude={"updated_at"})
    json_fields = {"work_experience", "education", "skills", "projects", "certifications"}

    if not profile:
        profile = Profile(id=1)
        db.add(profile)

    for key, value in fields.items():
        if key in json_fields:
            setattr(
                profile,
                key,
                json.dumps(
                    [v.model_dump() if hasattr(v, "model_dump") else v for v in value]
                ),
            )
        else:
            setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile_to_schema(profile)


@router.get("/status", response_model=StatusResponse)
def get_status():
    api_key = os.getenv("LLM_API_KEY", "").strip()
    provider = os.getenv("LLM_PROVIDER", "").strip()
    configured = bool(api_key and provider)
    return StatusResponse(
        api_key_configured=configured,
        provider=provider if configured else None,
    )
