from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, GeneratedCoverLetter, GeneratedCV, Profile
from app.schemas import (
    ApplicationEntry,
    ApplicationListResponse,
    ApplicationStatus,
    CreateApplicationRequest,
    UpdateApplicationRequest,
)

router = APIRouter()


def _enrich_app(app: Application, profiles: dict) -> dict:
    """Build ApplicationEntry dict from ORM object + profile map.
    match_score, linked_cover_letter_id, linked_cv_id are filled in
    by the caller after running _resolve_docs()."""
    p = profiles.get(app.profile_id) if app.profile_id else None
    return {
        "id": app.id,
        "company_name": app.company_name,
        "role_title": app.role_title,
        "status": app.status,
        "job_url": app.job_url,
        "notes": app.notes,
        "applied_date": app.applied_date,
        "created_at": app.created_at,
        "profile_id": app.profile_id,
        "profile_label": p.label if p else None,
        "profile_color": p.color if p else None,
        "profile_icon": p.icon if p else None,
        "match_score": None,  # filled in by _resolve_scores()
        "linked_cover_letter_id": None,  # filled in by _resolve_docs()
        "linked_cv_id": None,  # filled in by _resolve_docs()
    }


def _profile_map(apps: list[Application], db: Session) -> dict:
    ids = {a.profile_id for a in apps if a.profile_id}
    if not ids:
        return {}
    return {p.id: p for p in db.query(Profile).filter(Profile.id.in_(ids)).all()}


def _resolve_docs(app_ids: list[int], db: Session) -> tuple[dict, dict, dict]:
    """
    Returns three dicts keyed by application_id:
      - cl_id: most recent cover letter id per application
      - cv_id: most recent cv id per application
      - match_score: match_score from most recent cover letter with a score
    """
    if not app_ids:
        return {}, {}, {}

    cls = (
        db.query(GeneratedCoverLetter)
        .filter(GeneratedCoverLetter.application_id.in_(app_ids))
        .order_by(GeneratedCoverLetter.created_at.desc())
        .all()
    )
    cvs = (
        db.query(GeneratedCV)
        .filter(GeneratedCV.application_id.in_(app_ids))
        .order_by(GeneratedCV.created_at.desc())
        .all()
    )

    cl_id: dict = {}
    match_scores: dict = {}
    for cl in cls:
        aid = cl.application_id
        if aid not in cl_id:
            cl_id[aid] = cl.id
        score = getattr(cl, "match_score", None)
        if aid not in match_scores and score is not None:
            match_scores[aid] = score

    cv_id: dict = {}
    for cv in cvs:
        aid = cv.application_id
        if aid not in cv_id:
            cv_id[aid] = cv.id

    return cl_id, cv_id, match_scores


# --- Endpoints ---


@router.post("/applications", response_model=ApplicationEntry)
def create_application(
    body: CreateApplicationRequest, db: Session = Depends(get_db)
):
    app = Application(
        company_name=body.company_name,
        role_title=body.role_title,
        status=body.status.value,
        job_url=body.job_url,
        notes=body.notes,
        applied_date=body.applied_date or date.today(),
        profile_id=body.profile_id,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    pm = _profile_map([app], db)
    entry = _enrich_app(app, pm)
    cl_id, cv_id, scores = _resolve_docs([app.id], db)
    entry["linked_cover_letter_id"] = cl_id.get(app.id)
    entry["linked_cv_id"] = cv_id.get(app.id)
    entry["match_score"] = scores.get(app.id)
    return ApplicationEntry(**entry)


@router.get("/applications", response_model=ApplicationListResponse)
def list_applications(
    db: Session = Depends(get_db),
    profile_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    match_min: int | None = Query(default=None),
    match_max: int | None = Query(default=None),
    sort: str = Query(default="date_desc"),
):
    q = db.query(Application)
    if profile_id is not None:
        q = q.filter(Application.profile_id == profile_id)
    if status:
        q = q.filter(Application.status == status)
    if search:
        term = f"%{search}%"
        q = q.filter(
            Application.company_name.ilike(term) | Application.role_title.ilike(term)
        )
    if date_from:
        q = q.filter(Application.applied_date >= date_from)
    if date_to:
        q = q.filter(Application.applied_date <= date_to)
    if sort == "date_asc":
        q = q.order_by(Application.applied_date.asc().nullslast(), Application.created_at.asc())
    else:
        q = q.order_by(Application.applied_date.desc().nullslast(), Application.created_at.desc())

    apps = q.all()
    pm = _profile_map(apps, db)
    app_ids = [a.id for a in apps]
    cl_id, cv_id, scores = _resolve_docs(app_ids, db)

    items = []
    for a in apps:
        entry = _enrich_app(a, pm)
        entry["linked_cover_letter_id"] = cl_id.get(a.id)
        entry["linked_cv_id"] = cv_id.get(a.id)
        entry["match_score"] = scores.get(a.id)

        # Apply match_min / match_max filter (post-query since score is derived)
        score = entry["match_score"]
        if match_min is not None and (score is None or score < match_min):
            continue
        if match_max is not None and (score is None or score > match_max):
            continue

        items.append(ApplicationEntry(**entry))

    return ApplicationListResponse(items=items, total=len(items))


@router.get("/applications/{app_id}", response_model=ApplicationEntry)
def get_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    pm = _profile_map([app], db)
    entry = _enrich_app(app, pm)
    cl_id, cv_id, scores = _resolve_docs([app.id], db)
    entry["linked_cover_letter_id"] = cl_id.get(app.id)
    entry["linked_cv_id"] = cv_id.get(app.id)
    entry["match_score"] = scores.get(app.id)
    return ApplicationEntry(**entry)


@router.patch("/applications/{app_id}", response_model=ApplicationEntry)
def update_application(
    app_id: int, body: UpdateApplicationRequest, db: Session = Depends(get_db)
):
    app = db.query(Application).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "status" and value is not None:
            value = value if isinstance(value, str) else value.value
        setattr(app, field, value)
    app.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(app)
    pm = _profile_map([app], db)
    entry = _enrich_app(app, pm)
    cl_id, cv_id, scores = _resolve_docs([app.id], db)
    entry["linked_cover_letter_id"] = cl_id.get(app.id)
    entry["linked_cv_id"] = cv_id.get(app.id)
    entry["match_score"] = scores.get(app.id)
    return ApplicationEntry(**entry)


@router.delete("/applications/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    # Nullify FKs on linked documents before deleting
    db.query(GeneratedCoverLetter).filter_by(application_id=app_id).update(
        {"application_id": None}
    )
    db.query(GeneratedCV).filter_by(application_id=app_id).update(
        {"application_id": None}
    )
    db.delete(app)
    db.commit()
    return {"deleted": 1}
