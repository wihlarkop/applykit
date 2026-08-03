from __future__ import annotations

import json
from typing import Any

from app.models import Profile
from app.readiness.schemas import ProfileReadiness, ProfileRequirement


def parse_list(value: str | None) -> list[Any]:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def evaluate_profile(profile: Profile) -> ProfileReadiness:
    work_experience = parse_list(profile.work_experience)
    education = parse_list(profile.education)
    skills = parse_list(profile.skills)
    projects = parse_list(profile.projects)
    certifications = parse_list(profile.certifications)

    has_name = bool((profile.name or "").strip())
    has_email = bool((profile.email or "").strip())
    has_history = bool(work_experience or education)
    has_skills = bool(skills)

    missing: list[ProfileRequirement] = []
    if not has_name:
        missing.append("name")
    if not has_email:
        missing.append("email")
    if not has_history:
        missing.append("experience_or_education")
    if not has_skills:
        missing.append("skills")

    completeness = 0
    if has_name:
        completeness += 15
    if has_email:
        completeness += 10
    if (profile.summary or "").strip():
        completeness += 10
    if work_experience:
        completeness += 30
    if education:
        completeness += 20
    if skills:
        completeness += 15

    recommendations: list[str] = []
    if not (profile.summary or "").strip():
        recommendations.append("Add a professional summary.")
    if not projects:
        recommendations.append("Add one or more relevant projects.")
    if not certifications:
        recommendations.append(
            "Add certifications if they strengthen this profile."
        )

    return ProfileReadiness(
        profile_id=int(profile.id or 0),
        ready=not missing,
        completeness=min(completeness, 100),
        missing_requirements=missing,
        recommendations=recommendations,
    )
