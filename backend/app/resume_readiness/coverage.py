from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.resume_readiness.domain import CoverageResult, EvidencePhrase
from app.resume_readiness.normalization import normalize_text


def _phrase(
    key: str,
    value: Any,
    *,
    weight: float,
    critical: bool = False,
    location: str | None = None,
) -> EvidencePhrase | None:
    text = str(value or "").strip()
    if len(normalize_text(text)) < 2:
        return None
    return EvidencePhrase(
        key=key,
        value=text,
        weight=weight,
        critical=critical,
        location=location,
    )


def _append(target: list[EvidencePhrase], candidate: EvidencePhrase | None) -> None:
    if candidate is not None:
        target.append(candidate)


def profile_evidence_phrases(snapshot: dict[str, Any]) -> list[EvidencePhrase]:
    phrases: list[EvidencePhrase] = []
    _append(phrases, _phrase("name", snapshot.get("name"), weight=3, critical=True))
    _append(phrases, _phrase("email", snapshot.get("email"), weight=3, critical=True))
    _append(phrases, _phrase("phone", snapshot.get("phone"), weight=2, critical=True))

    for index, experience in enumerate(snapshot.get("work_experience") or []):
        location = f"work_experience[{index}]"
        _append(
            phrases,
            _phrase(
                f"experience:{index}:role",
                experience.get("role"),
                weight=3,
                critical=True,
                location=location,
            ),
        )
        _append(
            phrases,
            _phrase(
                f"experience:{index}:company",
                experience.get("company"),
                weight=3,
                critical=True,
                location=location,
            ),
        )
        for bullet_index, bullet in enumerate(experience.get("bullets") or []):
            _append(
                phrases,
                _phrase(
                    f"experience:{index}:bullet:{bullet_index}",
                    bullet,
                    weight=2,
                    location=f"{location}.bullets[{bullet_index}]",
                ),
            )

    for index, education in enumerate(snapshot.get("education") or []):
        location = f"education[{index}]"
        for field in ("institution", "school", "degree", "field"):
            if field in education:
                _append(
                    phrases,
                    _phrase(
                        f"education:{index}:{field}",
                        education.get(field),
                        weight=2,
                        location=location,
                    ),
                )

    skills = snapshot.get("skills") or []
    for index, skill in enumerate(skills):
        value = skill.get("name") if isinstance(skill, dict) else skill
        _append(
            phrases,
            _phrase(
                f"skill:{index}",
                value,
                weight=1,
                location=f"skills[{index}]",
            ),
        )

    for field in ("linkedin", "github", "portfolio"):
        _append(phrases, _phrase(field, snapshot.get(field), weight=0.5))

    return phrases


def _contains_phrase(normalized_document: str, phrase: EvidencePhrase) -> bool:
    normalized_phrase = normalize_text(phrase.value)
    if not normalized_phrase:
        return False
    return normalized_phrase in normalized_document


def calculate_source_coverage(
    snapshot: dict[str, Any],
    extracted_text: str,
    *,
    phrases: Iterable[EvidencePhrase] | None = None,
) -> CoverageResult:
    evidence = list(phrases or profile_evidence_phrases(snapshot))
    normalized_document = normalize_text(extracted_text)
    matched = tuple(
        phrase for phrase in evidence if _contains_phrase(normalized_document, phrase)
    )
    missing = tuple(phrase for phrase in evidence if phrase not in matched)
    total_weight = sum(item.weight for item in evidence)
    matched_weight = sum(item.weight for item in matched)
    coverage = matched_weight / total_weight if total_weight else 1.0
    return CoverageResult(
        coverage=round(coverage, 4),
        matched=matched,
        missing=missing,
    )
