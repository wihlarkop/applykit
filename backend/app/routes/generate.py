import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GeneratedCoverLetter, GeneratedCV, Profile
from app.schemas import (
    ATSEnhancement,
    CoverLetterRequest,
    CoverLetterResponse,
    GenerateCvRequest,
    GenerateCvResponse,
    PdfRequest,
    ProfileData,
)
from app.services.llm import APIKeyNotConfiguredError, LLMCallError, call_llm
from app.services.pdf import PDFRenderError, html_to_pdf
from app.services.settings import get_llm_config
from app.utils import profile_to_schema

logger = logging.getLogger(__name__)

router = APIRouter()

ATS_SYSTEM_PROMPT = """\
You are a senior technical recruiter and CV optimization specialist. Your job is to rewrite a candidate's CV content so it passes ATS (Applicant Tracking System) filters and impresses human reviewers.

INSTRUCTIONS:
1. Rewrite the "summary" as a concise 2-3 sentence professional summary. Lead with years of experience + domain. Weave in 3-5 keywords from the job description naturally. Never use first person ("I").
2. Rewrite each work_experience entry's "bullets" array:
   - Start every bullet with a strong past-tense action verb (Led, Built, Designed, Reduced, Automated, Delivered, Migrated, Scaled...)
   - Include a measurable outcome where possible (%, $, time saved, users impacted). If no metric exists, quantify scope (team size, system scale, user count).
   - Mirror keywords and phrases from the target job description when the candidate genuinely has that experience. Do NOT fabricate skills or experience.
   - Keep each bullet to 1-2 lines. Aim for 3-5 bullets per role.
3. Preserve all factual information: company names, roles, dates, education, skills. Never invent or remove entries.
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
- Return plain text only. No markdown formatting."""


def _get_profile_or_404(db: Session, profile_id: int) -> Profile:
    profile = db.query(Profile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Profile not found.", "code": "PROFILE_NOT_FOUND"},
        )
    return profile


def _format_profile_for_llm(p: ProfileData) -> str:
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
        except Exception as exc:
            logger.warning(
                "ATS enhancement failed, falling back to original profile: %s", exc
            )

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
    profile = _get_profile_or_404(db, req.profile_id)
    profile_data = profile_to_schema(profile)

    provider, api_key = get_llm_config(db)
    prompt = _build_cover_letter_prompt(profile_data, req)

    try:
        text = call_llm(
            prompt,
            system=COVER_LETTER_SYSTEM_PROMPT,
            provider=provider,
            api_key=api_key,
        )
    except APIKeyNotConfiguredError as e:
        raise HTTPException(
            status_code=400,
            detail={"detail": str(e), "code": "API_KEY_NOT_CONFIGURED"},
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
