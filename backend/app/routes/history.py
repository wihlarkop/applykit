from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GeneratedCV, GeneratedCoverLetter, Profile
from app.schemas import (
    GeneratedCoverLetterEntry,
    GeneratedCoverLetterListResponse,
    GeneratedCVEntry,
    GeneratedCVListResponse,
)

router = APIRouter()


def _enrich_cv(entry: GeneratedCV, db: Session) -> dict:
    d = {
        "id": entry.id,
        "created_at": entry.created_at,
        "enhanced": bool(entry.enhanced),
        "profile_snapshot": entry.profile_snapshot,
        "profile_id": entry.profile_id,
        "profile_label": None,
        "profile_color": None,
        "profile_icon": None,
    }
    if entry.profile_id:
        p = db.query(Profile).filter_by(id=entry.profile_id).first()
        if p:
            d["profile_label"] = p.label
            d["profile_color"] = p.color
            d["profile_icon"] = p.icon
    return d


def _enrich_cl(entry: GeneratedCoverLetter, db: Session) -> dict:
    d = {
        "id": entry.id,
        "created_at": entry.created_at,
        "company_name": entry.company_name,
        "job_description": entry.job_description,
        "extra_context": entry.extra_context,
        "cover_letter_text": entry.cover_letter_text,
        "profile_id": entry.profile_id,
        "profile_label": None,
        "profile_color": None,
        "profile_icon": None,
    }
    if entry.profile_id:
        p = db.query(Profile).filter_by(id=entry.profile_id).first()
        if p:
            d["profile_label"] = p.label
            d["profile_color"] = p.color
            d["profile_icon"] = p.icon
    return d


# --- CV history ---

@router.get("/history/cv", response_model=GeneratedCVListResponse)
def list_cv_history(db: Session = Depends(get_db)):
    items = db.query(GeneratedCV).order_by(GeneratedCV.created_at.desc()).all()
    return GeneratedCVListResponse(items=[_enrich_cv(e, db) for e in items])


@router.get("/history/cv/{entry_id}", response_model=GeneratedCVEntry)
def get_cv_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCV).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    return _enrich_cv(entry, db)


@router.delete("/history/cv/{entry_id}", status_code=204)
def delete_cv_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCV).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    db.delete(entry)
    db.commit()


# --- Cover letter history ---

@router.get("/history/cover-letter", response_model=GeneratedCoverLetterListResponse)
def list_cover_letter_history(db: Session = Depends(get_db)):
    items = db.query(GeneratedCoverLetter).order_by(GeneratedCoverLetter.created_at.desc()).all()
    return GeneratedCoverLetterListResponse(items=[_enrich_cl(e, db) for e in items])


@router.get("/history/cover-letter/{entry_id}", response_model=GeneratedCoverLetterEntry)
def get_cover_letter_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCoverLetter).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    return _enrich_cl(entry, db)


@router.delete("/history/cover-letter/{entry_id}", status_code=204)
def delete_cover_letter_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCoverLetter).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    db.delete(entry)
    db.commit()
