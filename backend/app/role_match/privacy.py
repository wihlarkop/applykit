from __future__ import annotations

import re
from typing import Any

from app.role_match.domain import (
    SafeCertification,
    SafeEducation,
    SafeProfile,
    SafeProject,
    SafeWorkExperience,
)

_SENSITIVE_LINE_PATTERNS = [
    re.compile(r"\b(date of birth|dob|born|age|aged)\b", re.IGNORECASE),
    re.compile(r"\b(marital status|married|single|children)\b", re.IGNORECASE),
    re.compile(r"\b(gender|male|female|religion|race|ethnicity)\b", re.IGNORECASE),
]


def _safe_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _filter_summary(value: str | None) -> str | None:
    if not value:
        return None
    kept = [
        line.strip()
        for line in value.splitlines()
        if line.strip()
        and not any(pattern.search(line) for pattern in _SENSITIVE_LINE_PATTERNS)
    ]
    return "\n".join(kept) or None


def build_safe_profile(profile: Any, include_location: bool) -> SafeProfile:
    return SafeProfile(
        location=_safe_text(getattr(profile, "location", None)) if include_location else None,
        summary=_filter_summary(_safe_text(getattr(profile, "summary", None))),
        work_experience=[
            SafeWorkExperience(
                company=_safe_text(item.company) or "",
                role=_safe_text(item.role) or "",
                start_date=_safe_text(item.start_date),
                end_date=_safe_text(item.end_date),
                bullets=[str(b).strip() for b in item.bullets if str(b).strip()],
            )
            for item in getattr(profile, "work_experience", [])
        ],
        education=[
            SafeEducation(
                institution=_safe_text(item.institution) or "",
                degree=_safe_text(item.degree),
                field=_safe_text(item.field),
                start_date=_safe_text(item.start_date),
                end_date=_safe_text(item.end_date),
            )
            for item in getattr(profile, "education", [])
        ],
        skills=[str(skill).strip() for skill in getattr(profile, "skills", []) if str(skill).strip()],
        projects=[
            SafeProject(
                name=_safe_text(item.name) or "",
                description=_safe_text(item.description),
                tech_stack=[str(t).strip() for t in item.tech_stack if str(t).strip()],
            )
            for item in getattr(profile, "projects", [])
        ],
        certifications=[
            SafeCertification(
                name=_safe_text(item.name),
                issuer=_safe_text(item.issuer),
                date=_safe_text(item.date),
            )
            for item in getattr(profile, "certifications", [])
        ],
    )
