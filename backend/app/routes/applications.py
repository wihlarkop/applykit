from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import ApplicationNotFoundError
from app.models import Application, GeneratedCoverLetter, GeneratedCV
from app.role_match.integration import resolve_application_match_scores
from app.role_match.product_schemas import (
    RoleMatchApplicationEntry,
    RoleMatchApplicationListResponse,
)
from app.schemas import CreateApplicationRequest, UpdateApplicationRequest
from app.utils import batch_load_profiles

router = APIRouter()


def _get_application_or_404(db: Session, application_id: int) -> Application:
    application = db.query(Application).filter_by(id=application_id).first()
    if not application:
        raise ApplicationNotFoundError(application_id)
    return application


def _enrich_app(app: Application, profiles: dict) -> dict:
    """Build an application response from the ORM object and profile map."""
    profile = profiles.get(app.profile_id) if app.profile_id else None
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
        "profile_label": profile.label if profile else None,
        "profile_color": profile.color if profile else None,
        "profile_icon": profile.icon if profile else None,
        "match_score": None,
        "match_score_source": "none",
        "role_match_analysis_id": None,
        "linked_cover_letter_id": None,
        "linked_cv_id": None,
        "location": app.location,
        "salary": app.salary,
        "job_description": app.job_description,
    }


def _resolve_docs(
    app_ids: list[int],
    db: Session,
) -> tuple[dict[int, int], dict[int, int], dict]:
    """Resolve latest documents and the preferred score source per application."""
    if not app_ids:
        return {}, {}, {}

    cover_letters = (
        db.query(GeneratedCoverLetter)
        .filter(GeneratedCoverLetter.application_id.in_(app_ids))
        .order_by(
            GeneratedCoverLetter.created_at.desc(),
            GeneratedCoverLetter.id.desc(),
        )
        .all()
    )
    cvs = (
        db.query(GeneratedCV)
        .filter(GeneratedCV.application_id.in_(app_ids))
        .order_by(GeneratedCV.created_at.desc(), GeneratedCV.id.desc())
        .all()
    )

    cover_letter_ids: dict[int, int] = {}
    for cover_letter in cover_letters:
        application_id = cover_letter.application_id
        if application_id is not None and application_id not in cover_letter_ids:
            cover_letter_ids[application_id] = cover_letter.id

    cv_ids: dict[int, int] = {}
    for cv in cvs:
        application_id = cv.application_id
        if application_id is not None and application_id not in cv_ids:
            cv_ids[application_id] = cv.id

    matches = resolve_application_match_scores(db, app_ids)
    return cover_letter_ids, cv_ids, matches


def _build_app_entry(app: Application, db: Session) -> RoleMatchApplicationEntry:
    profiles = batch_load_profiles([app], db)
    entry = _enrich_app(app, profiles)
    cover_letter_ids, cv_ids, matches = _resolve_docs([app.id], db)
    entry["linked_cover_letter_id"] = cover_letter_ids.get(app.id)
    entry["linked_cv_id"] = cv_ids.get(app.id)
    match = matches.get(app.id)
    if match is not None:
        entry["match_score"] = match.score
        entry["match_score_source"] = match.source
        entry["role_match_analysis_id"] = match.analysis_id
    return RoleMatchApplicationEntry(**entry)


@router.post("/applications", response_model=RoleMatchApplicationEntry)
def create_application(body: CreateApplicationRequest, db: Session = Depends(get_db)):
    app = Application(
        company_name=body.company_name,
        role_title=body.role_title,
        status=body.status.value,
        job_url=body.job_url,
        notes=body.notes,
        applied_date=body.applied_date or date.today(),
        profile_id=body.profile_id,
        location=body.location,
        salary=body.salary,
        job_description=body.job_description,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return _build_app_entry(app, db)


@router.get("/applications", response_model=RoleMatchApplicationListResponse)
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
    query = db.query(Application)
    if profile_id is not None:
        query = query.filter(Application.profile_id == profile_id)
    if status:
        query = query.filter(Application.status == status)
    if search:
        term = f"%{search}%"
        query = query.filter(
            Application.company_name.ilike(term) | Application.role_title.ilike(term)
        )
    if date_from:
        query = query.filter(Application.applied_date >= date_from)
    if date_to:
        query = query.filter(Application.applied_date <= date_to)
    if sort == "date_asc":
        query = query.order_by(
            Application.applied_date.asc().nullslast(),
            Application.created_at.asc(),
        )
    else:
        query = query.order_by(
            Application.applied_date.desc().nullslast(),
            Application.created_at.desc(),
        )

    apps = query.all()
    profiles = batch_load_profiles(apps, db)
    app_ids = [app.id for app in apps]
    cover_letter_ids, cv_ids, matches = _resolve_docs(app_ids, db)

    items: list[RoleMatchApplicationEntry] = []
    for app in apps:
        entry = _enrich_app(app, profiles)
        entry["linked_cover_letter_id"] = cover_letter_ids.get(app.id)
        entry["linked_cv_id"] = cv_ids.get(app.id)
        match = matches.get(app.id)
        if match is not None:
            entry["match_score"] = match.score
            entry["match_score_source"] = match.source
            entry["role_match_analysis_id"] = match.analysis_id

        score = entry["match_score"]
        if match_min is not None and (score is None or score < match_min):
            continue
        if match_max is not None and (score is None or score > match_max):
            continue
        items.append(RoleMatchApplicationEntry(**entry))

    return RoleMatchApplicationListResponse(items=items, total=len(items))


@router.get("/applications/{app_id}", response_model=RoleMatchApplicationEntry)
def get_application(app_id: int, db: Session = Depends(get_db)):
    return _build_app_entry(_get_application_or_404(db, app_id), db)


@router.patch("/applications/{app_id}", response_model=RoleMatchApplicationEntry)
def update_application(
    app_id: int, body: UpdateApplicationRequest, db: Session = Depends(get_db)
):
    app = _get_application_or_404(db, app_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "status" and value is not None:
            value = value if isinstance(value, str) else value.value
        setattr(app, field, value)
    app.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(app)
    return _build_app_entry(app, db)


@router.delete("/applications/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    app = _get_application_or_404(db, app_id)
    db.query(GeneratedCoverLetter).filter_by(application_id=app_id).update(
        {"application_id": None}
    )
    db.query(GeneratedCV).filter_by(application_id=app_id).update(
        {"application_id": None}
    )
    db.delete(app)
    db.commit()
    return {"deleted": 1}
