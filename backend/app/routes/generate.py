import asyncio
import json
import logging
from collections.abc import AsyncIterable

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_profile_or_404, require_llm_config
from app.exceptions import RateLimitError
from app.models import GeneratedCoverLetter, GeneratedCV
from app.schemas import (
    ATSEnhancement,
    CoverLetterPdfRequest,
    CoverLetterRequest,
    CvPdfRequest,
    GenerateBulletsRequest,
    GenerateCvRequest,
    GenerateCvResponse,
    GenerateSummaryRequest,
    ProfileData,
)
from app.services.llm import (
    OPERATION_BULLETS_GENERATION,
    OPERATION_COVER_LETTER,
    OPERATION_CV_GENERATION,
    OPERATION_SUMMARY_GENERATION,
    call_llm,
    clean_llm_json,
    stream_llm,
)
from app.services.prompts import (
    ATS_SYSTEM_PROMPT,
    BULLETS_IMPROVE_PROMPT,
    BULLETS_REORGANIZE_PROMPT,
    COVER_LETTER_SYSTEM_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
    TONE_PROMPTS,
)
from app.services.settings import get_llm_config as _get_llm_config_raw
from app.utils import format_profile_for_llm, profile_to_schema
from integration.pdf import PDFRenderError, html_to_pdf
from integration.template import render_cover_letter_template, render_cv_template

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------


def _render_cv_pdf(profile_data: dict) -> Response:
    try:
        html = render_cv_template(profile_data)
        pdf_bytes = html_to_pdf(html)
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


def _render_cover_letter_pdf(letter_data: dict) -> Response:
    try:
        html = render_cover_letter_template(letter_data)
        pdf_bytes = html_to_pdf(html)
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


def _handle_stream_error(e: Exception) -> ServerSentEvent:
    if isinstance(e, RateLimitError):
        return ServerSentEvent(data=str(e), event="rate_limit")
    return ServerSentEvent(data=str(e), event="error")


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def _build_cover_letter_prompt(p: ProfileData, req: CoverLetterRequest) -> str:
    """Build a structured user prompt for cover letter generation."""
    parts = [format_profile_for_llm(p)]
    parts.append(f"\n---\nJOB DESCRIPTION:\n{req.job_description}")
    if req.company_name:
        parts.append(f"\nCOMPANY NAME: {req.company_name}")
    if req.extra_context and req.extra_context.strip():
        parts.append(
            f"\nSPECIAL INSTRUCTIONS FROM CANDIDATE:\n{req.extra_context.strip()}"
        )
    if req.fit_context and req.fit_context.strip():
        parts.append(
            f"\nAdditional context from the candidate: {req.fit_context.strip()}.\n"
            "Use this to guide emphasis — do not fabricate experience, but frame existing "
            "experience to address these points where honest."
        )
    tone_modifier = TONE_PROMPTS.get(
        req.tone or "professional", TONE_PROMPTS["professional"]
    )
    parts.append(f"\nTONE INSTRUCTION: {tone_modifier}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/generate/cv", response_model=GenerateCvResponse)
def generate_cv(req: GenerateCvRequest, db: Session = Depends(get_db)):
    # NOTE: This endpoint intentionally does NOT use require_llm_config because
    # enhancement is optional — when LLM is unconfigured it returns the raw profile.
    profile = get_profile_or_404(req.profile_id, db)
    profile_data = profile_to_schema(profile)

    enhanced = False
    result_profile = profile_data
    provider, api_key = _get_llm_config_raw(db)

    if req.enhance and provider and api_key:
        try:
            user_prompt = format_profile_for_llm(profile_data)
            if req.job_description:
                user_prompt += (
                    f"\n\n---\nTARGET JOB DESCRIPTION:\n{req.job_description}"
                )
            if req.extra_context and req.extra_context.strip():
                user_prompt += f"\n\nADDITIONAL CONTEXT FROM CANDIDATE: {req.extra_context.strip()}"
            user_prompt += f"\n\n---\nORIGINAL DATA (use this schema for your JSON output):\n{profile_data.model_dump_json()}"
            llm_output = call_llm(
                user_prompt,
                system=ATS_SYSTEM_PROMPT,
                provider=provider,
                api_key=api_key,
                operation=OPERATION_CV_GENERATION,
                profile_id=req.profile_id,
            )
            cleaned = clean_llm_json(llm_output)
            ats = ATSEnhancement(**json.loads(cleaned))
            result_profile = profile_data.model_copy(
                update={
                    "summary": ats.summary,
                    "work_experience": ats.work_experience,
                }
            )
            enhanced = True
        except RateLimitError:
            raise
        except Exception as exc:
            logger.warning(
                "ATS enhancement failed, falling back to original profile: %s", exc
            )

    entry = GeneratedCV(
        enhanced=int(enhanced),
        profile_snapshot=result_profile.model_dump_json(),
        profile_id=req.profile_id,
        application_id=req.application_id,
    )
    db.add(entry)
    db.commit()

    return GenerateCvResponse(enhanced=enhanced, profile=result_profile)


@router.post("/generate/cv/stream", response_class=EventSourceResponse)
async def generate_cv_stream(req: GenerateCvRequest, db: Session = Depends(get_db)):
    """SSE endpoint: emits 'profile' (original) then 'done' (enhanced + saved id)."""
    profile = get_profile_or_404(req.profile_id, db)
    profile_data = profile_to_schema(profile)

    yield ServerSentEvent(data=profile_data.model_dump_json(), event="profile")

    enhanced = False
    result_profile = profile_data
    provider, api_key = _get_llm_config_raw(db)

    if req.enhance and provider and api_key:
        try:
            user_prompt = format_profile_for_llm(profile_data)
            if req.job_description:
                user_prompt += f"\n\n---\nTARGET JOB DESCRIPTION:\n{req.job_description}"
            if req.extra_context and req.extra_context.strip():
                user_prompt += f"\n\nADDITIONAL CONTEXT FROM CANDIDATE: {req.extra_context.strip()}"
            user_prompt += f"\n\n---\nORIGINAL DATA (use this schema for your JSON output):\n{profile_data.model_dump_json()}"

            llm_output = await asyncio.to_thread(
                call_llm,
                user_prompt,
                system=ATS_SYSTEM_PROMPT,
                provider=provider,
                api_key=api_key,
                operation=OPERATION_CV_GENERATION,
                profile_id=req.profile_id,
            )
            cleaned = clean_llm_json(llm_output)
            ats = ATSEnhancement(**json.loads(cleaned))
            result_profile = profile_data.model_copy(
                update={"summary": ats.summary, "work_experience": ats.work_experience}
            )
            enhanced = True
        except RateLimitError as e:
            yield ServerSentEvent(data=str(e), event="rate_limit")
            return
        except Exception as exc:
            logger.warning("ATS enhancement failed, falling back to original profile: %s", exc)

    entry = GeneratedCV(
        enhanced=int(enhanced),
        profile_snapshot=result_profile.model_dump_json(),
        profile_id=req.profile_id,
        application_id=req.application_id,
    )
    db.add(entry)
    db.commit()

    done_payload = json.dumps({
        "enhanced": enhanced,
        "profile": result_profile.model_dump(mode="json"),
        "id": entry.id,
    })
    yield ServerSentEvent(data=done_payload, event="done")


@router.post("/generate/cv/pdf")
def generate_cv_pdf(req: CvPdfRequest):
    return _render_cv_pdf(req.profile.model_dump())


@router.post("/generate/cover-letter", response_class=EventSourceResponse)
async def generate_cover_letter(
    req: CoverLetterRequest,
    db: Session = Depends(get_db),
    llm: tuple[str, str] = Depends(require_llm_config),
) -> AsyncIterable[ServerSentEvent]:
    profile = get_profile_or_404(req.profile_id, db)
    profile_data = profile_to_schema(profile)
    provider, api_key = llm

    prompt = _build_cover_letter_prompt(profile_data, req)

    accumulated = []
    try:
        async for chunk in stream_llm(
            prompt,
            system=COVER_LETTER_SYSTEM_PROMPT,
            provider=provider,
            api_key=api_key,
            operation=OPERATION_COVER_LETTER,
            profile_id=req.profile_id,
        ):
            accumulated.append(chunk)
            yield ServerSentEvent(data=str(chunk), event="token")
    except Exception as e:
        yield _handle_stream_error(e)
        return

    yield ServerSentEvent(data="[DONE]", event="done")

    full_text = "".join(accumulated)
    entry = GeneratedCoverLetter(
        company_name=req.company_name,
        role_title=req.role_title,
        location=req.location,
        salary=req.salary,
        job_description=req.job_description,
        extra_context=req.extra_context or None,
        cover_letter_text=full_text,
        profile_id=req.profile_id,
        job_url=req.job_url,
        tone=req.tone or "professional",
        match_score=req.match_score,
        fit_analysis=req.fit_analysis_json,
        application_id=req.application_id,
    )
    db.add(entry)
    db.commit()


@router.post("/generate/summary", response_class=EventSourceResponse)
async def generate_summary(
    req: GenerateSummaryRequest,
    db: Session = Depends(get_db),
    llm: tuple[str, str] = Depends(require_llm_config),
) -> AsyncIterable[ServerSentEvent]:
    profile = get_profile_or_404(req.profile_id, db)
    profile_data = profile_to_schema(profile)
    provider, api_key = llm

    tone_modifier = TONE_PROMPTS.get(req.tone, TONE_PROMPTS["professional"])
    user_prompt = format_profile_for_llm(profile_data)
    if req.extra_context and req.extra_context.strip():
        user_prompt += (
            f"\n\nADDITIONAL CONTEXT FROM CANDIDATE: {req.extra_context.strip()}"
        )
    user_prompt += f"\n\nTONE INSTRUCTION: {tone_modifier}"

    try:
        async for chunk in stream_llm(
            user_prompt,
            system=SUMMARY_SYSTEM_PROMPT,
            provider=provider,
            api_key=api_key,
            operation=OPERATION_SUMMARY_GENERATION,
            profile_id=req.profile_id,
        ):
            yield ServerSentEvent(data=str(chunk), event="token")
    except Exception as e:
        yield _handle_stream_error(e)
        return
    yield ServerSentEvent(data="[DONE]", event="done")


@router.post("/generate/bullets", response_class=EventSourceResponse)
async def generate_bullets(
    req: GenerateBulletsRequest,
    db: Session = Depends(get_db),
    llm: tuple[str, str] = Depends(require_llm_config),
) -> AsyncIterable[ServerSentEvent]:
    get_profile_or_404(req.profile_id, db)
    provider, api_key = llm

    system = (
        BULLETS_IMPROVE_PROMPT if req.mode == "improve" else BULLETS_REORGANIZE_PROMPT
    )

    clean_bullets = [b for b in req.bullets if b.strip()]
    bullets_text = "\n".join(f"- {b}" for b in clean_bullets)

    user_prompt = (
        f"Role: {req.role} at {req.company}\n"
        f"Input bullet count: {len(clean_bullets)}\n\n"
        f"Current bullets:\n{bullets_text}"
    )

    if req.extra_context and req.extra_context.strip():
        user_prompt += (
            f"\n\nADDITIONAL CONTEXT FROM CANDIDATE: {req.extra_context.strip()}"
        )

    try:
        async for chunk in stream_llm(
            user_prompt,
            system=system,
            provider=provider,
            api_key=api_key,
            operation=OPERATION_BULLETS_GENERATION,
            profile_id=req.profile_id,
        ):
            yield ServerSentEvent(data=str(chunk), event="token")
    except Exception as e:
        yield _handle_stream_error(e)
        return

    yield ServerSentEvent(data="[DONE]", event="done")


@router.post("/generate/cover-letter/pdf")
def generate_cover_letter_pdf(req: CoverLetterPdfRequest):
    return _render_cover_letter_pdf(req.model_dump())
