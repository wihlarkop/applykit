import json
import logging
from collections.abc import AsyncIterable

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import RateLimitError
from app.models import GeneratedCoverLetter, GeneratedCV, Profile
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
    call_llm,
    stream_llm,
)
from app.services.settings import get_llm_config
from app.utils import format_profile_for_llm, profile_to_schema
from integration.pdf import PDFRenderError, html_to_pdf
from integration.template import render_cover_letter_template, render_cv_template

logger = logging.getLogger(__name__)

router = APIRouter()

TONE_PROMPTS = {
    "professional": "Write in a formal, polished tone.",
    "enthusiastic": "Write in an energetic, passionate tone that conveys genuine excitement.",
    "concise": "Write concisely — aim for under 200 words. No filler.",
    "creative": "Write in a distinctive, memorable style that stands out.",
}

ATS_SYSTEM_PROMPT = """\
You are a senior technical recruiter and CV optimization specialist. Your job is to rewrite a candidate's CV content so it passes ATS (Applicant Tracking System) filters and impresses human reviewers.

INSTRUCTIONS:
1. Rewrite the "summary" as a concise 2-3 sentence professional summary. Lead with years of experience + domain. Weave in 3-5 keywords from the job description naturally. Never use first person ("I").
2. Rewrite each work_experience entry's "bullets" array:
   - Start every bullet with a strong past-tense action verb (Led, Built, Designed, Reduced, Automated, Delivered, Migrated, Scaled...)
   - Include a measurable outcome where possible (%, $, time saved, users impacted). If no metric exists, quantify scope (team size, system scale, user count).
   - Mirror keywords and phrases from the target job description when the candidate genuinely has that experience. Do NOT fabricate skills or experience.
   - Keep each bullet to 1-2 lines. Aim for 3-5 bullets per role.
3. Preserve all factual information: company names, roles, dates, education, skills, projects, certifications. Never invent, fabricate, or add any data that was not present in the original profile.
4. If no job description is provided, optimize generically for the candidate's apparent field.

OUTPUT FORMAT:
Return ONLY valid JSON with exactly two keys:
- "summary": string
- "work_experience": array of objects, each with: company (string), role (string), start_date (string), end_date (string or null), bullets (array of strings)

No markdown, no explanation, no wrapping — just the raw JSON object."""

COVER_LETTER_SYSTEM_PROMPT = """\
You are a professional cover letter writer. You write letters that are specific, human, and persuasive — never generic or formulaic.

STRUCTURE (3 paragraphs, 250-350 words total):

Paragraph 1 — Hook (2-3 sentences):
Open with genuine enthusiasm for the specific role and company. Mention the company by name and something concrete about what they do or why the candidate is drawn to them. State the role being applied for.

Paragraph 2 — Evidence (5-8 sentences):
This is the core. Connect 2-3 specific achievements from the candidate's experience directly to the job requirements. Use the STAR pattern briefly: what was the situation, what did the candidate do, what was the measurable result. Mirror the job description's language naturally. This paragraph should make it obvious the candidate has done work that is directly relevant.

Paragraph 3 — Close (2-3 sentences):
Express forward-looking enthusiasm. Mention one specific way the candidate could contribute. End with a confident, professional call to action.

RULES:
- Tone: confident and warm, never desperate or arrogant. Write like a competent professional, not a salesperson.
- Be specific. Replace every generic phrase ("I am a passionate professional...") with a concrete detail from the candidate's actual experience.
- Never fabricate achievements, skills, or experience not present in the profile.
- Never include a subject line, date, address header, or "Dear Hiring Manager" — start directly with the opening paragraph.
- Never include a sign-off like "Sincerely" or the candidate's name at the end.
- Use the candidate's name naturally within the letter only if it fits.
- If extra context / emphasis instructions are provided, incorporate them.
- Return plain text only. No markdown formatting.
- Use only standard ASCII punctuation. Do not use en-dashes (–), em-dashes (—), curly/smart quotes (' ' " "), or ellipsis (…). Use a plain hyphen (-) where a dash is needed and straight quotes (') otherwise."""


def _get_profile_or_404(db: Session, profile_id: int) -> Profile:
    profile = db.query(Profile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Profile not found.", "code": "PROFILE_NOT_FOUND"},
        )
    return profile


def _render_pdf(html: str, filename: str) -> Response:
    try:
        pdf_bytes = html_to_pdf(html)
    except PDFRenderError as e:
        raise HTTPException(
            status_code=502,
            detail={"detail": str(e), "code": "PDF_RENDER_FAILED"},
        ) from e
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


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


_format_profile_for_llm = format_profile_for_llm


def _build_cover_letter_prompt(p: ProfileData, req: CoverLetterRequest) -> str:
    """Build a structured user prompt for cover letter generation."""
    parts = [_format_profile_for_llm(p)]
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


@router.post("/generate/cv", response_model=GenerateCvResponse)
def generate_cv(req: GenerateCvRequest, db: Session = Depends(get_db)):
    profile = _get_profile_or_404(db, req.profile_id)
    profile_data = profile_to_schema(profile)

    enhanced = False
    result_profile = profile_data
    provider, api_key = get_llm_config(db)

    if req.enhance and provider and api_key:
        try:
            user_prompt = _format_profile_for_llm(profile_data)
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
            )
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


@router.post("/generate/cv/pdf")
def generate_cv_pdf(req: CvPdfRequest):
    return _render_cv_pdf(req.profile.model_dump())


@router.post("/generate/cover-letter", response_class=EventSourceResponse)
async def generate_cover_letter(
    req: CoverLetterRequest, db: Session = Depends(get_db)
) -> AsyncIterable[ServerSentEvent]:
    profile = _get_profile_or_404(db, req.profile_id)
    profile_data = profile_to_schema(profile)
    provider, api_key = get_llm_config(db)

    if not provider or not api_key:
        raise HTTPException(
            status_code=400,
            detail={"detail": "LLM not configured.", "code": "API_KEY_NOT_CONFIGURED"},
        )

    prompt = _build_cover_letter_prompt(profile_data, req)

    accumulated = []
    try:
        async for chunk in stream_llm(
            prompt,
            system=COVER_LETTER_SYSTEM_PROMPT,
            provider=provider,
            api_key=api_key,
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


SUMMARY_SYSTEM_PROMPT = """\
You are a professional resume writer specializing in crafting compelling professional summaries.

Write a 2-4 sentence professional summary for the candidate based on their profile.

RULES:
- Lead with years of experience + core domain/role if apparent from the data.
- Weave in 2-3 key skills or technologies that define the candidate.
- Convey what value the candidate brings to an employer.
- Never use first person ("I", "my", "me") — write in third person or impersonal style.
- Never fabricate details not present in the profile.
- Return plain text only. No markdown, no labels, no preamble.
- Use only standard ASCII punctuation. No en-dashes, em-dashes, smart quotes, or ellipsis."""


@router.post("/generate/summary", response_class=EventSourceResponse)
async def generate_summary(
    req: GenerateSummaryRequest, db: Session = Depends(get_db)
) -> AsyncIterable[ServerSentEvent]:
    profile = _get_profile_or_404(db, req.profile_id)
    profile_data = profile_to_schema(profile)
    provider, api_key = get_llm_config(db)

    if not provider or not api_key:
        raise HTTPException(
            status_code=400,
            detail={"detail": "LLM not configured.", "code": "API_KEY_NOT_CONFIGURED"},
        )

    tone_modifier = TONE_PROMPTS.get(req.tone, TONE_PROMPTS["professional"])
    user_prompt = _format_profile_for_llm(profile_data)
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
        ):
            yield ServerSentEvent(data=str(chunk), event="token")
    except Exception as e:
        yield _handle_stream_error(e)
        return
    yield ServerSentEvent(data="[DONE]", event="done")


BULLETS_IMPROVE_PROMPT = """\
You are a professional resume writer. Rewrite the given work experience bullet points to be stronger.

RULES:
- Output EXACTLY the same number of bullets as the input — one rewritten bullet for each input bullet. Do not merge, split, or drop any bullets.
- Start every bullet with a strong past-tense action verb (Led, Built, Designed, Reduced, Automated, Delivered, Migrated, Scaled, Launched, Optimized...).
- Include a measurable outcome where one can reasonably be inferred (%, time saved, users impacted, team size, revenue). If no metric is present in the original, quantify the scope instead.
- Do NOT fabricate specific numbers that were not implied — use qualifiers like "significantly", "across a team of X" only when that scale is evident.
- Keep each bullet to 1-2 concise lines. If an input bullet is a long paragraph, condense it to the core achievement.
- Preserve all factual content — company, role, and achievements must remain accurate.
- Use only standard ASCII punctuation. No en-dashes, em-dashes, smart quotes, or ellipsis.

OUTPUT FORMAT:
Return ONLY the bullet points, one per line, each starting with "- ". No preamble, no explanation."""

BULLETS_REORGANIZE_PROMPT = """\
You are a professional resume strategist. Reorganize the given work experience bullet points by impact — most impressive and results-driven first.

RULES:
- Output EXACTLY the same number of bullets as the input — every input bullet must appear in the output. Do not merge, drop, or add any bullets.
- Reorder bullets from highest impact to lowest (quantified results > scope/scale > general contributions).
- Lightly clean up wording: fix grammar, ensure each bullet starts with a strong action verb. Keep each bullet to 1-2 concise lines — condense any paragraph-length bullet to its core achievement.
- Do NOT change the substance of any bullet — preserve all facts and figures.
- Ensure every bullet starts with "- ".
- Use only standard ASCII punctuation. No en-dashes, em-dashes, smart quotes, or ellipsis.

OUTPUT FORMAT:
Return ONLY the reordered bullet points, one per line, each starting with "- ". No preamble, no explanation."""


@router.post("/generate/bullets", response_class=EventSourceResponse)
async def generate_bullets(
    req: GenerateBulletsRequest, db: Session = Depends(get_db)
) -> AsyncIterable[ServerSentEvent]:

    _get_profile_or_404(db, req.profile_id)
    provider, api_key = get_llm_config(db)

    if not provider or not api_key:
        raise HTTPException(
            status_code=400,
            detail={"detail": "LLM not configured.", "code": "API_KEY_NOT_CONFIGURED"},
        )

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
            user_prompt, system=system, provider=provider, api_key=api_key
        ):
            yield ServerSentEvent(data=str(chunk), event="token")
    except Exception as e:
        yield _handle_stream_error(e)
        return

    yield ServerSentEvent(data="[DONE]", event="done")


@router.post("/generate/cover-letter/pdf")
def generate_cover_letter_pdf(req: CoverLetterPdfRequest):
    return _render_cover_letter_pdf(req.model_dump())
