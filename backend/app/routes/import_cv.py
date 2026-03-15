import json
import os

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app.schemas import ProfileData
from app.services.llm import APIKeyNotConfiguredError, LLMCallError, call_llm
from app.services.parser import extract_text, validate_extracted_text

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_EXTENSIONS = {"pdf", "docx"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

EXTRACT_SYSTEM_PROMPT = """You are a CV parser. Extract all information from the provided CV text and return it as a JSON object matching the schema below. Return only valid JSON with no markdown wrapping or explanation.

Schema: {"name": "string", "email": "string", "phone": "string or null", "location": "string or null", "linkedin": "string or null", "github": "string or null", "portfolio": "string or null", "summary": "string or null", "work_experience": [{"company": "string", "role": "string", "start_date": "string", "end_date": "string or null", "bullets": ["string"]}], "education": [{"institution": "string", "degree": "string", "field": "string", "start_date": "string", "end_date": "string or null"}], "skills": ["string"], "projects": [{"name": "string", "description": "string", "tech_stack": ["string"], "link": "string or null"}], "certifications": [{"name": "string", "issuer": "string", "date": "string"}]}"""


@router.post("/import/cv", response_model=ProfileData)
async def import_cv(
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
):
    # Check API key early
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

    # Extract text — file takes precedence over text
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
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "detail": "Could not extract text from file.",
                    "code": "FILE_PARSE_FAILED",
                },
            ) from e
    elif text:
        raw_text = text.strip()
    else:
        raise HTTPException(
            status_code=422,
            detail={"detail": "Provide a file or text.", "code": "FILE_PARSE_FAILED"},
        )

    try:
        validate_extracted_text(raw_text)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"detail": str(e), "code": "FILE_PARSE_FAILED"},
        ) from e

    # Call LLM to extract profile fields
    try:
        llm_output = call_llm(raw_text, system=EXTRACT_SYSTEM_PROMPT)
    except APIKeyNotConfiguredError as e:
        raise HTTPException(
            status_code=400, detail={"detail": str(e), "code": "API_KEY_NOT_CONFIGURED"}
        ) from e
    except LLMCallError as e:
        raise HTTPException(
            status_code=502, detail={"detail": str(e), "code": "LLM_CALL_FAILED"}
        ) from e

    # Strip markdown wrappers and validate JSON output
    cleaned = (
        llm_output.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    try:
        parsed = json.loads(cleaned)
        return ProfileData(**parsed)
    except (json.JSONDecodeError, ValidationError):
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "Could not parse CV into profile fields. Try editing manually.",
                "code": "LLM_OUTPUT_INVALID",
            },
        )
