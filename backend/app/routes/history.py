from fastapi import APIRouter, Depends, HTTPException, Query
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


def _profile_map(entries: list, db: Session) -> dict:
    """Batch-load profiles for a list of history entries to avoid N+1 queries."""
    ids = {e.profile_id for e in entries if e.profile_id}
    if not ids:
        return {}
    return {p.id: p for p in db.query(Profile).filter(Profile.id.in_(ids)).all()}


def _enrich_cv(entry: GeneratedCV, profiles: dict) -> dict:
    p = profiles.get(entry.profile_id) if entry.profile_id else None
    return {
        "id": entry.id,
        "created_at": entry.created_at,
        "enhanced": bool(entry.enhanced),
        "profile_snapshot": entry.profile_snapshot,
        "profile_id": entry.profile_id,
        "profile_label": p.label if p else None,
        "profile_color": p.color if p else None,
        "profile_icon": p.icon if p else None,
    }


def _enrich_cl(entry: GeneratedCoverLetter, profiles: dict) -> dict:
    p = profiles.get(entry.profile_id) if entry.profile_id else None
    return {
        "id": entry.id,
        "created_at": entry.created_at,
        "company_name": entry.company_name,
        "job_description": entry.job_description,
        "extra_context": entry.extra_context,
        "cover_letter_text": entry.cover_letter_text,
        "profile_id": entry.profile_id,
        "profile_label": p.label if p else None,
        "profile_color": p.color if p else None,
        "profile_icon": p.icon if p else None,
    }


# --- CV history ---

@router.get("/history/cv", response_model=GeneratedCVListResponse)
def list_cv_history(
    db: Session = Depends(get_db),
    profile_id: int | None = Query(default=None),
):
    q = db.query(GeneratedCV).order_by(GeneratedCV.created_at.desc())
    if profile_id is not None:
        q = q.filter(GeneratedCV.profile_id == profile_id)
    items = q.all()
    pm = _profile_map(items, db)
    return GeneratedCVListResponse(items=[_enrich_cv(e, pm) for e in items])


@router.get("/history/cv/{entry_id}", response_model=GeneratedCVEntry)
def get_cv_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCV).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    return _enrich_cv(entry, _profile_map([entry], db))


@router.delete("/history/cv/{entry_id}", status_code=204)
def delete_cv_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCV).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    db.delete(entry)
    db.commit()


# --- Cover letter history ---

@router.get("/history/cover-letter", response_model=GeneratedCoverLetterListResponse)
def list_cover_letter_history(
    db: Session = Depends(get_db),
    profile_id: int | None = Query(default=None),
):
    q = db.query(GeneratedCoverLetter).order_by(GeneratedCoverLetter.created_at.desc())
    if profile_id is not None:
        q = q.filter(GeneratedCoverLetter.profile_id == profile_id)
    items = q.all()
    pm = _profile_map(items, db)
    return GeneratedCoverLetterListResponse(items=[_enrich_cl(e, pm) for e in items])


@router.get("/history/cover-letter/{entry_id}", response_model=GeneratedCoverLetterEntry)
def get_cover_letter_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCoverLetter).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    return _enrich_cl(entry, _profile_map([entry], db))


@router.delete("/history/cover-letter/{entry_id}", status_code=204)
def delete_cover_letter_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCoverLetter).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    db.delete(entry)
    db.commit()
