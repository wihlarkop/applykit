from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GeneratedCV, GeneratedCoverLetter
from app.schemas import (
    GeneratedCoverLetterEntry,
    GeneratedCoverLetterListResponse,
    GeneratedCVEntry,
    GeneratedCVListResponse,
)

router = APIRouter()


# --- CV history ---

@router.get("/history/cv", response_model=GeneratedCVListResponse)
def list_cv_history(db: Session = Depends(get_db)):
    items = (
        db.query(GeneratedCV)
        .order_by(GeneratedCV.created_at.desc())
        .all()
    )
    return GeneratedCVListResponse(items=items)


@router.get("/history/cv/{entry_id}", response_model=GeneratedCVEntry)
def get_cv_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCV).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    return entry


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
    items = (
        db.query(GeneratedCoverLetter)
        .order_by(GeneratedCoverLetter.created_at.desc())
        .all()
    )
    return GeneratedCoverLetterListResponse(items=items)


@router.get("/history/cover-letter/{entry_id}", response_model=GeneratedCoverLetterEntry)
def get_cover_letter_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCoverLetter).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    return entry


@router.delete("/history/cover-letter/{entry_id}", status_code=204)
def delete_cover_letter_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCoverLetter).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    db.delete(entry)
    db.commit()
