import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
from app.schemas import (
    CreateProfileRequest,
    ProfileData,
    ProfileListItem,
    ProfileListResponse,
)
from app.utils import profile_to_schema

router = APIRouter()

JSON_FIELDS = {"work_experience", "education", "skills", "projects", "certifications"}


def _get_or_404(db: Session, profile_id: int) -> Profile:
    profile = db.query(Profile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Profile not found", "code": "NOT_FOUND"},
        )
    return profile


@router.get("/profiles", response_model=ProfileListResponse)
def list_profiles(db: Session = Depends(get_db)):
    items = db.query(Profile).order_by(Profile.id).all()
    return ProfileListResponse(items=items)


@router.post("/profiles", response_model=ProfileData, status_code=201)
def create_profile(req: CreateProfileRequest, db: Session = Depends(get_db)):
    if req.clone_from_id is not None:
        source = _get_or_404(db, req.clone_from_id)
        profile = Profile(
            label=req.label,
            color=req.color,
            icon=req.icon,
            name=source.name,
            email=source.email,
            phone=source.phone,
            location=source.location,
            linkedin=source.linkedin,
            github=source.github,
            portfolio=source.portfolio,
            summary=source.summary,
            work_experience=source.work_experience,
            education=source.education,
            skills=source.skills,
            projects=source.projects,
            certifications=source.certifications,
        )
    else:
        profile = Profile(
            label=req.label,
            color=req.color,
            icon=req.icon,
            name="",
            email="",
        )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile_to_schema(profile)


@router.get("/profiles/{profile_id}", response_model=ProfileData)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    return profile_to_schema(_get_or_404(db, profile_id))


@router.put("/profiles/{profile_id}", response_model=ProfileData)
def save_profile(profile_id: int, data: ProfileData, db: Session = Depends(get_db)):
    profile = _get_or_404(db, profile_id)
    fields = data.model_dump(exclude={"id", "updated_at"})

    for key, value in fields.items():
        if key in JSON_FIELDS:
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


@router.delete("/profiles/{profile_id}", status_code=204)
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = _get_or_404(db, profile_id)
    db.delete(profile)
    db.commit()
