import json

from app.models import Profile
from app.schemas import ProfileData


def _safe_json(value: str | None, fallback: list) -> list:
    try:
        return json.loads(value or "[]")
    except (json.JSONDecodeError, TypeError):
        return fallback


def _filter_empty_certs(certs: list) -> list:
    return [c for c in certs if c.get("name", "").strip()]


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
        certifications=_filter_empty_certs(_safe_json(p.certifications, [])),
        updated_at=p.updated_at,
    )


def format_profile_for_llm(p: ProfileData) -> str:
    """Format a ProfileData object as human-readable text for better LLM comprehension."""
    lines = [f"CANDIDATE: {p.name}"]
    if p.email:
        lines.append(f"Email: {p.email}")
    if p.location:
        lines.append(f"Location: {p.location}")
    if p.linkedin:
        lines.append(f"LinkedIn: {p.linkedin}")
    if p.github:
        lines.append(f"GitHub: {p.github}")
    if p.summary:
        lines.append(f"\nSUMMARY:\n{p.summary}")
    if p.skills:
        lines.append(f"\nSKILLS: {', '.join(p.skills)}")
    if p.work_experience:
        lines.append("\nWORK EXPERIENCE:")
        for w in p.work_experience:
            end = w.end_date or "Present"
            lines.append(f"\n  {w.role} at {w.company} ({w.start_date} – {end})")
            for b in w.bullets:
                lines.append(f"    - {b}")
    if p.education:
        lines.append("\nEDUCATION:")
        for e in p.education:
            end = e.end_date or "Present"
            lines.append(
                f"  {e.degree} in {e.field}, {e.institution} ({e.start_date} – {end})"
            )
    if p.projects:
        lines.append("\nPROJECTS:")
        for proj in p.projects:
            tech = f" [{', '.join(proj.tech_stack)}]" if proj.tech_stack else ""
            lines.append(f"  {proj.name}{tech}: {proj.description}")
    if p.certifications:
        lines.append("\nCERTIFICATIONS:")
        for c in p.certifications:
            lines.append(f"  {c.name} — {c.issuer} ({c.date})")
    return "\n".join(lines)
