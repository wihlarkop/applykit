from __future__ import annotations

import re
import unicodedata

from app.role_match.domain import EvidenceCatalogItem, EvidenceSource, SafeProfile


def _duplicate_key(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(re.findall(r"[a-z0-9+#.-]+", normalized))


def _slug(text: str) -> str:
    value = _duplicate_key(text).replace(" ", "-")
    return value or "unnamed"


def build_evidence_catalog(profile: SafeProfile) -> list[EvidenceCatalogItem]:
    items: list[EvidenceCatalogItem] = []

    if profile.summary:
        items.append(
            EvidenceCatalogItem(
                evidence_id="summary:0",
                source=EvidenceSource.SKILLS_LIST,
                text=profile.summary,
                duplicate_key=_duplicate_key(profile.summary),
                metadata={"kind": "summary"},
            )
        )

    for work_index, work in enumerate(profile.work_experience):
        role_text = f"{work.role} at {work.company}".strip()
        if role_text:
            items.append(
                EvidenceCatalogItem(
                    evidence_id=f"work:{work_index}:role",
                    source=EvidenceSource.WORK_EXPERIENCE,
                    text=role_text,
                    start_date=work.start_date,
                    end_date=work.end_date,
                    duplicate_key=_duplicate_key(role_text),
                    metadata={"company": work.company, "role": work.role, "kind": "role"},
                )
            )
        for bullet_index, bullet in enumerate(work.bullets):
            items.append(
                EvidenceCatalogItem(
                    evidence_id=f"work:{work_index}:bullet:{bullet_index}",
                    source=EvidenceSource.WORK_EXPERIENCE,
                    text=bullet,
                    start_date=work.start_date,
                    end_date=work.end_date,
                    duplicate_key=_duplicate_key(bullet),
                    metadata={"company": work.company, "role": work.role, "kind": "bullet"},
                )
            )

    for project_index, project in enumerate(profile.projects):
        if project.description:
            items.append(
                EvidenceCatalogItem(
                    evidence_id=f"project:{project_index}:description",
                    source=EvidenceSource.PROJECT,
                    text=project.description,
                    duplicate_key=_duplicate_key(project.description),
                    metadata={"project": project.name, "kind": "description"},
                )
            )
        for tech_index, tech in enumerate(project.tech_stack):
            items.append(
                EvidenceCatalogItem(
                    evidence_id=f"project:{project_index}:tech:{tech_index}",
                    source=EvidenceSource.PROJECT,
                    text=tech,
                    duplicate_key=_duplicate_key(tech),
                    metadata={"project": project.name, "kind": "technology"},
                )
            )

    for education_index, education in enumerate(profile.education):
        parts = [education.degree, education.field, education.institution]
        text = " — ".join(part for part in parts if part)
        if text:
            items.append(
                EvidenceCatalogItem(
                    evidence_id=f"education:{education_index}",
                    source=EvidenceSource.CERTIFICATION_EDUCATION,
                    text=text,
                    start_date=education.start_date,
                    end_date=education.end_date,
                    duplicate_key=_duplicate_key(text),
                    metadata={"kind": "education"},
                )
            )

    for certification_index, certification in enumerate(profile.certifications):
        parts = [certification.name, certification.issuer]
        text = " — ".join(part for part in parts if part)
        if text:
            items.append(
                EvidenceCatalogItem(
                    evidence_id=f"certification:{certification_index}",
                    source=EvidenceSource.CERTIFICATION_EDUCATION,
                    text=text,
                    end_date=certification.date,
                    duplicate_key=_duplicate_key(text),
                    metadata={"kind": "certification"},
                )
            )

    used_skill_ids: dict[str, int] = {}
    for skill in profile.skills:
        base = _slug(skill)
        occurrence = used_skill_ids.get(base, 0)
        used_skill_ids[base] = occurrence + 1
        suffix = "" if occurrence == 0 else f"-{occurrence + 1}"
        items.append(
            EvidenceCatalogItem(
                evidence_id=f"skill:{base}{suffix}",
                source=EvidenceSource.SKILLS_LIST,
                text=skill,
                duplicate_key=_duplicate_key(skill),
                metadata={"kind": "skill"},
            )
        )

    return items
