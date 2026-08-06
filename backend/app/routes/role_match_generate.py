from __future__ import annotations

from collections.abc import AsyncIterable

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_profile_or_404, require_llm_config
from app.exceptions import stream_error_event
from app.models import GeneratedCoverLetter
from app.role_match.integration import build_cover_letter_role_match_context
from app.role_match.product_schemas import RoleMatchCoverLetterRequest
from app.routes.generate import _build_cover_letter_prompt
from app.services.llm import OPERATION_COVER_LETTER, stream_llm
from app.services.prompts import COVER_LETTER_SYSTEM_PROMPT
from app.utils import profile_to_schema

router = APIRouter()


@router.post(
    "/generate/cover-letter/role-match",
    response_class=EventSourceResponse,
)
async def generate_role_match_cover_letter(
    req: RoleMatchCoverLetterRequest,
    db: Session = Depends(get_db),
    llm: tuple[str, str] = Depends(require_llm_config),
) -> AsyncIterable[ServerSentEvent]:
    profile = get_profile_or_404(req.profile_id, db)
    profile_data = profile_to_schema(profile)
    provider, api_key = llm

    role_match = build_cover_letter_role_match_context(
        db,
        analysis_id=req.role_match_analysis_id,
        profile_id=req.profile_id,
        job_description=req.job_description,
    )
    effective_request = req.model_copy(
        update={
            "fit_context": role_match.fit_context,
            "match_score": None,
            "fit_analysis_json": None,
        }
    )
    prompt = _build_cover_letter_prompt(profile_data, effective_request)

    accumulated: list[str] = []
    try:
        async for chunk in stream_llm(
            prompt,
            system=COVER_LETTER_SYSTEM_PROMPT,
            provider=provider,
            api_key=api_key,
            operation=OPERATION_COVER_LETTER,
            profile_id=req.profile_id,
        ):
            accumulated.append(str(chunk))
            yield ServerSentEvent(data=str(chunk), event="token")
    except Exception as exc:
        yield stream_error_event(exc)
        return

    entry = GeneratedCoverLetter(
        company_name=req.company_name,
        role_title=req.role_title,
        location=req.location,
        salary=req.salary,
        job_description=req.job_description,
        extra_context=req.extra_context or None,
        cover_letter_text="".join(accumulated),
        profile_id=req.profile_id,
        job_url=req.job_url,
        tone=req.tone or "professional",
        match_score=None,
        fit_analysis=None,
        application_id=req.application_id,
        role_match_analysis_id=role_match.analysis_id,
    )
    db.add(entry)
    db.commit()

    yield ServerSentEvent(data="[DONE]", event="done")
