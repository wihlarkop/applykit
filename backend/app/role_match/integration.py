from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.exceptions import InvalidRequestError, RoleMatchAnalysisNotFoundError
from app.models import GeneratedCoverLetter
from app.role_match.models import RoleMatchAnalysis


@dataclass(frozen=True)
class CoverLetterRoleMatchContext:
    analysis_id: int
    match_score: int | None
    fit_context: str | None


@dataclass(frozen=True)
class ResolvedApplicationMatch:
    score: int
    source: str
    analysis_id: int | None


def _loads(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def _job_description_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_authoritative(analysis: RoleMatchAnalysis | None) -> bool:
    return bool(
        analysis
        and analysis.state == "success"
        and analysis.show_authoritative_score
        and analysis.display_score is not None
    )


def _summary_to_fit_context(summary: dict[str, Any] | None) -> str | None:
    if not summary:
        return None
    lines: list[str] = []
    headline = summary.get("headline")
    description = summary.get("description")
    if headline:
        lines.append(str(headline))
    if description:
        lines.append(str(description))

    strengths = summary.get("strengths") or []
    if strengths:
        lines.append("Strongest supported evidence:")
        for item in strengths[:3]:
            title = item.get("title") if isinstance(item, dict) else None
            explanation = item.get("explanation") if isinstance(item, dict) else None
            if title:
                lines.append(f"- {title}: {explanation or 'Supported by profile evidence.'}")

    concerns = summary.get("concerns") or []
    if concerns:
        lines.append("Areas that should not be overstated:")
        for item in concerns[:3]:
            title = item.get("title") if isinstance(item, dict) else None
            explanation = item.get("explanation") if isinstance(item, dict) else None
            if title:
                lines.append(f"- {title}: {explanation or 'Evidence is limited.'}")

    next_step = summary.get("next_step")
    if next_step:
        lines.append(f"Recommended emphasis: {next_step}")
    return "\n".join(lines) or None


def build_cover_letter_role_match_context(
    db: Session,
    *,
    analysis_id: int,
    profile_id: int,
    job_description: str,
) -> CoverLetterRoleMatchContext:
    analysis = db.query(RoleMatchAnalysis).filter_by(id=analysis_id).first()
    if analysis is None:
        raise RoleMatchAnalysisNotFoundError(analysis_id)
    if analysis.profile_id != profile_id:
        raise InvalidRequestError(
            "Role match analysis must use the same profile as the cover letter"
        )
    if analysis.job_description_hash != _job_description_hash(job_description):
        raise InvalidRequestError(
            "Role match analysis does not match this job description"
        )

    if not _is_authoritative(analysis):
        return CoverLetterRoleMatchContext(
            analysis_id=analysis.id,
            match_score=None,
            fit_context=None,
        )

    normalized = _loads(analysis.normalized_payload, {})
    return CoverLetterRoleMatchContext(
        analysis_id=analysis.id,
        match_score=analysis.display_score,
        fit_context=_summary_to_fit_context(normalized.get("summary")),
    )


def _legacy_compatible_fit_analysis(
    analysis_payload: dict[str, Any],
) -> dict[str, Any]:
    summary = analysis_payload.get("summary") or {}
    strengths = summary.get("strengths") or []
    concerns = summary.get("concerns") or []
    requirements = analysis_payload.get("requirements") or []
    missing = [
        item.get("canonical_text")
        for item in requirements
        if item.get("match_level") in {"no_evidence", "unknown"}
        and item.get("canonical_text")
    ]
    eligibility = analysis_payload.get("eligibility")
    red_flags = (
        [f"Eligibility status: {str(eligibility).replace('_', ' ')}"]
        if eligibility in {"likely_ineligible", "ineligible"}
        else []
    )
    return {
        "match_score": analysis_payload.get("score") or 0,
        "pros": [item.get("title") for item in strengths if item.get("title")],
        "cons": [item.get("title") for item in concerns if item.get("title")],
        "missing_keywords": missing,
        "red_flags": red_flags,
        "suggested_emphasis": summary.get("next_step")
        or "Review the evidence details before tailoring this application.",
        "interview_questions": [],
        "role_match_analysis_id": analysis_payload["id"],
        "role_match_analysis": analysis_payload,
    }


def enrich_cover_letter_role_match(
    db: Session,
    entry: GeneratedCoverLetter,
) -> dict[str, Any]:
    analysis = None
    analysis_id = getattr(entry, "role_match_analysis_id", None)
    if analysis_id is not None:
        analysis = db.query(RoleMatchAnalysis).filter_by(id=analysis_id).first()

    if _is_authoritative(analysis):
        score = analysis.display_score
        source = "role_evidence_match"
    elif entry.match_score is not None:
        score = entry.match_score
        source = "legacy_llm_score"
    else:
        score = None
        source = "none"

    analysis_payload = None
    compatibility_payload = None
    if analysis is not None:
        from app.role_match.repository import serialize_analysis

        analysis_payload = serialize_analysis(db, analysis).model_dump(mode="json")
        compatibility_payload = _legacy_compatible_fit_analysis(analysis_payload)

    return {
        "match_score": score,
        "match_score_source": source,
        "role_match_analysis_id": analysis.id if analysis is not None else None,
        "role_match_analysis": analysis_payload,
        "fit_analysis": compatibility_payload,
    }


def resolve_application_match_scores(
    db: Session,
    application_ids: list[int],
) -> dict[int, ResolvedApplicationMatch]:
    if not application_ids:
        return {}

    resolved: dict[int, ResolvedApplicationMatch] = {}
    direct_analyses = (
        db.query(RoleMatchAnalysis)
        .filter(
            RoleMatchAnalysis.application_id.in_(application_ids),
            RoleMatchAnalysis.state == "success",
            RoleMatchAnalysis.show_authoritative_score.is_(True),
            RoleMatchAnalysis.display_score.is_not(None),
        )
        .order_by(RoleMatchAnalysis.created_at.desc(), RoleMatchAnalysis.id.desc())
        .all()
    )
    for analysis in direct_analyses:
        application_id = analysis.application_id
        if application_id is not None and application_id not in resolved:
            resolved[application_id] = ResolvedApplicationMatch(
                score=analysis.display_score,
                source="role_evidence_match",
                analysis_id=analysis.id,
            )

    cover_letters = (
        db.query(GeneratedCoverLetter)
        .filter(GeneratedCoverLetter.application_id.in_(application_ids))
        .order_by(
            GeneratedCoverLetter.created_at.desc(),
            GeneratedCoverLetter.id.desc(),
        )
        .all()
    )
    analysis_ids = {
        entry.role_match_analysis_id
        for entry in cover_letters
        if getattr(entry, "role_match_analysis_id", None) is not None
    }
    analyses = (
        db.query(RoleMatchAnalysis).filter(RoleMatchAnalysis.id.in_(analysis_ids)).all()
        if analysis_ids
        else []
    )
    analysis_map = {analysis.id: analysis for analysis in analyses}

    for entry in cover_letters:
        application_id = entry.application_id
        if application_id is None or application_id in resolved:
            continue
        analysis = analysis_map.get(getattr(entry, "role_match_analysis_id", None))
        if _is_authoritative(analysis):
            resolved[application_id] = ResolvedApplicationMatch(
                score=analysis.display_score,
                source="role_evidence_match",
                analysis_id=analysis.id,
            )

    for entry in cover_letters:
        application_id = entry.application_id
        if (
            application_id is None
            or application_id in resolved
            or entry.match_score is None
        ):
            continue
        resolved[application_id] = ResolvedApplicationMatch(
            score=entry.match_score,
            source="legacy_llm_score",
            analysis_id=None,
        )

    return resolved
