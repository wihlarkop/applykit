import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_llm_config
from app.exceptions.llm import LLMOutputError
from app.schemas import ProfileData
from app.services.llm import call_llm, parse_structured_output
from app.services.parser import extract_text, validate_extracted_text
from app.services.prompts import CV_IMPORT_SYSTEM_PROMPT

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_EXTENSIONS = {"pdf", "docx"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def _clean_cv_payload(payload: dict[str, Any]) -> dict[str, Any]:
    certifications = payload.get("certifications")
    if isinstance(certifications, list):
        payload["certifications"] = [
            item
            for item in certifications
            if isinstance(item, dict) and (item.get("name") or "").strip()
        ]
    return payload


@router.post("/import/cv", response_model=ProfileData)
async def import_cv(
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    provider, api_key = require_llm_config(db)

    raw_text: str
    if file is not None:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail={
                    "detail": "File too large. Maximum size is 5MB.",
                    "code": "FILE_TOO_LARGE",
                },
            )
        ext = (file.filename or "").lower().rsplit(".", 1)[-1]
        mime = file.content_type or ""
        if ext not in ALLOWED_EXTENSIONS or mime not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=422,
                detail={
                    "detail": "Unsupported file type. Use PDF, DOCX, or plain text.",
                    "code": "FILE_TYPE_UNSUPPORTED",
                },
            )
        try:
            raw_text = extract_text(file_content=content, filename=file.filename)
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "detail": "Could not extract text from file.",
                    "code": "FILE_PARSE_FAILED",
                },
            ) from exc
    elif text:
        raw_text = text.strip()
    else:
        raise HTTPException(
            status_code=422,
            detail={"detail": "Provide a file or text.", "code": "FILE_PARSE_FAILED"},
        )

    try:
        validate_extracted_text(raw_text)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"detail": str(exc), "code": "FILE_PARSE_FAILED"},
        ) from exc

    # Truncate to avoid exceeding LLM context windows (CVs rarely need more than this)
    max_text_chars = 15_000
    if len(raw_text) > max_text_chars:
        raw_text = raw_text[:max_text_chars]

    llm_output = call_llm(
        raw_text,
        system=CV_IMPORT_SYSTEM_PROMPT,
        provider=provider,
        api_key=api_key,
        timeout=60,
    )

    try:
        return parse_structured_output(
            llm_output,
            ProfileData,
            preprocess=_clean_cv_payload,
        )
    except LLMOutputError:
        logger.warning("CV import returned invalid structured output")
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "Could not parse CV into profile fields. Try editing manually.",
                "code": "LLM_OUTPUT_INVALID",
            },
        ) from None
