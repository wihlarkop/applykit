import json

from app.models import Profile
from app.schemas import ProfileData


def _safe_json(value: str | None, fallback: list) -> list:
    try:
        return json.loads(value or "[]")
    except (json.JSONDecodeError, TypeError):
        return fallback


def profile_to_schema(p: Profile) -> ProfileData:
    return ProfileData(
        id=p.id,
        label=p.label,
        color=p.color,
        icon=p.icon,
        name=p.name,
        email=p.email,
        phone=p.phone,
        location=p.location,
        linkedin=p.linkedin,
        github=p.github,
        portfolio=p.portfolio,
        summary=p.summary,
        work_experience=_safe_json(p.work_experience, []),
        education=_safe_json(p.education, []),
        skills=_safe_json(p.skills, []),
        projects=_safe_json(p.projects, []),
        certifications=_safe_json(p.certifications, []),
        updated_at=p.updated_at,
    )
