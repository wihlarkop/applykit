import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import not_found_404
from app.models import Application, GeneratedCoverLetter, GeneratedCV, Profile
from app.schemas import (
    BulkDeleteRequest,
    GeneratedCoverLetterEntry,
    GeneratedCoverLetterListResponse,
    GeneratedCVEntry,
    GeneratedCVListResponse,
    UpdateStatusRequest,
)

router = APIRouter()


def _extract_company(entry: GeneratedCoverLetter) -> str:
    """Extract company name from stored field or job_description."""
    if entry.company_name:
        return entry.company_name
    first_line = re.sub(
        r"^(title|job title|position|role)\s*:\s*",
        "",
        (entry.job_description or "").split("\n")[0].strip(),
        flags=re.IGNORECASE,
    )
    at_match = re.search(r"\bat\s+([^,(\n]+)", first_line, re.IGNORECASE)
    if at_match:
        return at_match.group(1).strip()[:30]
    dash_match = re.search(r"\s[-–]\s*([A-Za-z]\S+)", first_line)
    if dash_match:
        return dash_match.group(1)[:30]
    return first_line[:30] or "Unknown Company"


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
        "application_status": getattr(entry, "application_status", None),
        "profile_id": entry.profile_id,
        "profile_label": p.label if p else None,
        "profile_color": p.color if p else None,
        "profile_icon": p.icon if p else None,
    }


def _enrich_cl(entry: GeneratedCoverLetter, profiles: dict) -> dict:
    import json as _json

    p = profiles.get(entry.profile_id) if entry.profile_id else None
    fit = None
    raw_fit = getattr(entry, "fit_analysis", None)
    if raw_fit:
        try:
            fit = _json.loads(raw_fit)
        except Exception:
            fit = None
    return {
        "id": entry.id,
        "created_at": entry.created_at,
        "company_name": entry.company_name,
        "job_description": entry.job_description,
        "extra_context": entry.extra_context,
        "cover_letter_text": entry.cover_letter_text,
        "tone": getattr(entry, "tone", "professional"),
        "job_url": getattr(entry, "job_url", None),
        "match_score": getattr(entry, "match_score", None),
        "fit_analysis": fit,
        "application_status": getattr(entry, "application_status", None),
        "application_id": getattr(entry, "application_id", None),
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
    sort: str = Query(default="date_desc"),
    limit: int = Query(default=20),
    offset: int = Query(default=0),
):
    q = db.query(GeneratedCV)
    if profile_id is not None:
        q = q.filter(GeneratedCV.profile_id == profile_id)
    if sort == "date_asc":
        q = q.order_by(GeneratedCV.created_at.asc())
    else:
        q = q.order_by(GeneratedCV.created_at.desc())
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    pm = _profile_map(items, db)
    return GeneratedCVListResponse(
        items=[_enrich_cv(e, pm) for e in items], total=total
    )


@router.get("/history/cv/{entry_id}", response_model=GeneratedCVEntry)
def get_cv_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCV).filter_by(id=entry_id).first()
    if not entry:
        raise not_found_404("CV entry")
    return _enrich_cv(entry, _profile_map([entry], db))


@router.delete("/history/cv/{entry_id}", status_code=204)
def delete_cv_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCV).filter_by(id=entry_id).first()
    if not entry:
        raise not_found_404("CV entry")
    db.delete(entry)
    db.commit()


@router.patch("/history/cv/{entry_id}/status", response_model=GeneratedCVEntry)
def update_cv_status(
    entry_id: int, body: UpdateStatusRequest, db: Session = Depends(get_db)
):
    entry = db.query(GeneratedCV).filter_by(id=entry_id).first()
    if not entry:
        raise not_found_404("CV entry")
    entry.application_status = body.status
    db.commit()
    return _enrich_cv(entry, _profile_map([entry], db))


# --- Cover letter history ---


@router.get("/history/cover-letter", response_model=GeneratedCoverLetterListResponse)
def list_cover_letter_history(
    db: Session = Depends(get_db),
    profile_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    match_min: int | None = Query(default=None),
    match_max: int | None = Query(default=None),
    status: str | None = Query(default=None),
    sort: str = Query(default="date_desc"),
    limit: int = Query(default=20),
    offset: int = Query(default=0),
):
    q = db.query(GeneratedCoverLetter)
    if profile_id is not None:
        q = q.filter(GeneratedCoverLetter.profile_id == profile_id)
    if search:
        term = f"%{search}%"
        q = q.filter(
            GeneratedCoverLetter.company_name.ilike(term)
            | GeneratedCoverLetter.job_description.ilike(term)
        )
    if match_min is not None:
        q = q.filter(GeneratedCoverLetter.match_score >= match_min)
    if match_max is not None:
        q = q.filter(GeneratedCoverLetter.match_score <= match_max)
    if status:
        q = q.filter(GeneratedCoverLetter.application_status == status)
    if sort == "date_asc":
        q = q.order_by(GeneratedCoverLetter.created_at.asc())
    elif sort == "match_desc":
        q = q.order_by(GeneratedCoverLetter.match_score.desc().nullslast())
    elif sort == "company_asc":
        q = q.order_by(GeneratedCoverLetter.company_name.asc().nullslast())
    else:
        q = q.order_by(GeneratedCoverLetter.created_at.desc())
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    pm = _profile_map(items, db)
    return GeneratedCoverLetterListResponse(
        items=[_enrich_cl(e, pm) for e in items], total=total
    )


@router.get(
    "/history/cover-letter/{entry_id}", response_model=GeneratedCoverLetterEntry
)
def get_cover_letter_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCoverLetter).filter_by(id=entry_id).first()
    if not entry:
        raise not_found_404("Cover letter")
    return _enrich_cl(entry, _profile_map([entry], db))


@router.delete("/history/cover-letter/{entry_id}", status_code=204)
def delete_cover_letter_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCoverLetter).filter_by(id=entry_id).first()
    if not entry:
        raise not_found_404("Cover letter")
    db.delete(entry)
    db.commit()


@router.patch(
    "/history/cover-letter/{entry_id}/status", response_model=GeneratedCoverLetterEntry
)
def update_cover_letter_status(
    entry_id: int, body: UpdateStatusRequest, db: Session = Depends(get_db)
):
    entry = db.query(GeneratedCoverLetter).filter_by(id=entry_id).first()
    if not entry:
        raise not_found_404("Cover letter")
    entry.application_status = body.status
    if body.status:
        if entry.application_id:
            # Sync status to the linked Application
            linked = db.query(Application).filter_by(id=entry.application_id).first()
            if linked:
                linked.status = body.status
        else:
            # Auto-create an Application record and link it
            app = Application(
                company_name=_extract_company(entry),
                status=body.status,
                job_url=entry.job_url,
                profile_id=entry.profile_id,
                applied_date=date.today(),
            )
            db.add(app)
            db.flush()
            entry.application_id = app.id
    # Note: clearing to "—" does not unlink the Application — manage it from Tracker
    db.commit()
    return _enrich_cl(entry, _profile_map([entry], db))


@router.delete("/history/cover-letter")
def bulk_delete_cover_letters(body: BulkDeleteRequest, db: Session = Depends(get_db)):
    deleted = (
        db.query(GeneratedCoverLetter)
        .filter(GeneratedCoverLetter.id.in_(body.ids))
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"deleted": deleted}


@router.delete("/history/cv")
def bulk_delete_cvs(body: BulkDeleteRequest, db: Session = Depends(get_db)):
    deleted = (
        db.query(GeneratedCV)
        .filter(GeneratedCV.id.in_(body.ids))
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"deleted": deleted}
