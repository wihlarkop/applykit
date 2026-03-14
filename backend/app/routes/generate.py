import json
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GeneratedCV, GeneratedCoverLetter, Profile
from app.schemas import (
    ATSEnhancement,
    CoverLetterRequest,
    CoverLetterResponse,
    GenerateCvResponse,
    PdfRequest,
)
from app.services.llm import APIKeyNotConfiguredError, LLMCallError, call_llm
from app.services.pdf import PDFRenderError, html_to_pdf
from app.utils import profile_to_schema

router = APIRouter()

ATS_SYSTEM_PROMPT = """You are an expert CV writer specializing in ATS optimization. Given this candidate's profile, rewrite the work_experience bullet points and summary to be action-oriented, metric-driven, and ATS-friendly. Return only valid JSON with two keys: "summary" (string) and "work_experience" (array, same schema as input — each item has company, role, start_date, end_date, bullets)."""

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


def _get_profile_or_404(db: Session) -> Profile:
    profile = db.query(Profile).filter_by(id=1).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": "No profile found. Please complete your profile first.",
                "code": "PROFILE_NOT_FOUND",
            },
        )
    return profile


@router.post("/generate/cv", response_model=GenerateCvResponse)
def generate_cv(db: Session = Depends(get_db)):
    _check_api_key()
    profile = _get_profile_or_404(db)
    profile_data = profile_to_schema(profile)

    enhanced = False
    result_profile = profile_data

    try:
        llm_output = call_llm(profile_data.model_dump_json(), system=ATS_SYSTEM_PROMPT)
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
    except Exception:
        pass  # fallback to original profile on any error

    # Save to history
    entry = GeneratedCV(
        enhanced=int(enhanced),
        profile_snapshot=result_profile.model_dump_json(),
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
    profile = _get_profile_or_404(db)
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

    # Save to history
    entry = GeneratedCoverLetter(
        company_name=req.company_name,
        job_description=req.job_description,
        extra_context=req.extra_context or None,
        cover_letter_text=text,
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
