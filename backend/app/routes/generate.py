import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GeneratedCV, GeneratedCoverLetter, Profile
from app.schemas import (
    ATSEnhancement,
    CoverLetterRequest,
    CoverLetterResponse,
    GenerateCvRequest,
    GenerateCvResponse,
    PdfRequest,
)
from app.services.llm import APIKeyNotConfiguredError, LLMCallError, call_llm
from app.services.pdf import PDFRenderError, html_to_pdf
from app.utils import profile_to_schema

router = APIRouter()

ATS_SYSTEM_PROMPT = """You are an expert CV writer specializing in ATS optimization. Given this candidate's profile, rewrite the work_experience bullet points and summary to be action-oriented, metric-driven, and ATS-friendly. If a target job description is provided, tailor the language to match its keywords and requirements. Return only valid JSON with two keys: "summary" (string) and "work_experience" (array, same schema as input — each item has company, role, start_date, end_date, bullets)."""

COVER_LETTER_SYSTEM_PROMPT = """You are an expert career coach. Write a professional, tailored cover letter based on the candidate's profile and the provided job description. Be specific to the role and company. Tone: confident, direct. Return plain text only — no subject line, no date, no header."""


def _check_api_key():
    if (
        not os.getenv("LLM_API_KEY", "").strip()
        or not os.getenv("LLM_PROVIDER", "").strip()
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "LLM_API_KEY not configured. See README.",
                "code": "API_KEY_NOT_CONFIGURED",
            },
        )


def _get_profile_or_404(db: Session, profile_id: int) -> Profile:
    profile = db.query(Profile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": "Profile not found.",
                "code": "PROFILE_NOT_FOUND",
            },
        )
    return profile


@router.post("/generate/cv", response_model=GenerateCvResponse)
def generate_cv(req: GenerateCvRequest, db: Session = Depends(get_db)):
    _check_api_key()
    profile = _get_profile_or_404(db, req.profile_id)
    profile_data = profile_to_schema(profile)

    enhanced = False
    result_profile = profile_data

    if req.enhance:
        try:
            user_prompt = profile_data.model_dump_json()
            if req.job_description:
                user_prompt += f"\n\nTarget job description: {req.job_description}"
            llm_output = call_llm(user_prompt, system=ATS_SYSTEM_PROMPT)
            cleaned = (
                llm_output.strip()
                .removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )
            ats = ATSEnhancement(**json.loads(cleaned))
            result_profile = profile_data.model_copy(
                update={
                    "summary": ats.summary,
                    "work_experience": ats.work_experience,
                }
            )
            enhanced = True
        except Exception as exc:
            logger.warning("ATS enhancement failed, falling back to original profile: %s", exc)

    entry = GeneratedCV(
        enhanced=int(enhanced),
        profile_snapshot=result_profile.model_dump_json(),
        profile_id=req.profile_id,
    )
    db.add(entry)
    db.commit()

    return GenerateCvResponse(enhanced=enhanced, profile=result_profile)


@router.post("/generate/cv/pdf")
def generate_cv_pdf(req: PdfRequest):
    try:
        pdf_bytes = html_to_pdf(req.html)
    except PDFRenderError as e:
        raise HTTPException(
            status_code=502,
            detail={"detail": str(e), "code": "PDF_RENDER_FAILED"},
        ) from e
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=cv.pdf"},
    )


@router.post("/generate/cover-letter", response_model=CoverLetterResponse)
def generate_cover_letter(req: CoverLetterRequest, db: Session = Depends(get_db)):
    _check_api_key()
    profile = _get_profile_or_404(db, req.profile_id)
    profile_data = profile_to_schema(profile)

    prompt = f"""Candidate profile: {profile_data.model_dump_json()}
Job description: {req.job_description}
Additional context: {req.extra_context or "None"}"""

    try:
        text = call_llm(prompt, system=COVER_LETTER_SYSTEM_PROMPT)
    except APIKeyNotConfiguredError as e:
        raise HTTPException(
            status_code=400, detail={"detail": str(e), "code": "API_KEY_NOT_CONFIGURED"}
        ) from e
    except LLMCallError as e:
        raise HTTPException(
            status_code=502, detail={"detail": str(e), "code": "LLM_CALL_FAILED"}
        ) from e

    entry = GeneratedCoverLetter(
        company_name=req.company_name,
        job_description=req.job_description,
        extra_context=req.extra_context or None,
        cover_letter_text=text,
        profile_id=req.profile_id,
    )
    db.add(entry)
    db.commit()

    return CoverLetterResponse(cover_letter_text=text)


@router.post("/generate/cover-letter/pdf")
def generate_cover_letter_pdf(req: PdfRequest):
    try:
        pdf_bytes = html_to_pdf(req.html)
    except PDFRenderError as e:
        raise HTTPException(
            status_code=502,
            detail={"detail": str(e), "code": "PDF_RENDER_FAILED"},
        ) from e
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=cover-letter.pdf"},
    )
