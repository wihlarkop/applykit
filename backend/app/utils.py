import json
from app.models import Profile
from app.schemas import ProfileData


def profile_to_schema(p: Profile) -> ProfileData:
    return ProfileData(
        name=p.name,
        email=p.email,
        phone=p.phone,
        location=p.location,
        linkedin=p.linkedin,
        github=p.github,
        portfolio=p.portfolio,
        summary=p.summary,
        work_experience=json.loads(p.work_experience or "[]"),
        education=json.loads(p.education or "[]"),
        skills=json.loads(p.skills or "[]"),
        projects=json.loads(p.projects or "[]"),
        certifications=json.loads(p.certifications or "[]"),
        updated_at=p.updated_at,
    )
