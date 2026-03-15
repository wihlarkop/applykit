import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ProfileData
from app.services.llm import APIKeyNotConfiguredError, LLMCallError, call_llm
from app.services.parser import extract_text, validate_extracted_text
from app.services.settings import get_llm_config

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_EXTENSIONS = {"pdf", "docx"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

EXTRACT_SYSTEM_PROMPT = """\
You are a precise CV data extraction engine. Your task is to read raw CV/resume text and extract every piece of information into a structured JSON object.

EXTRACTION RULES:
1. Extract ALL information present — do not skip sections or summarize. If the CV mentions it, capture it.
2. For work_experience bullets: extract each accomplishment as a separate bullet string. Keep the candidate's original wording. If they wrote paragraphs instead of bullets, break them into individual achievement statements.
3. For dates: use the format as written (e.g., "Jan 2022", "2022", "March 2020"). If end_date is missing or says "Present"/"Current", set it to null.
4. For skills: extract individual skills as separate strings, not comma-separated groups. "Python, JavaScript, React" becomes ["Python", "JavaScript", "React"].
5. If a field is genuinely not present in the CV, use null (for optional strings) or [] (for arrays). Never fabricate data.
6. For projects: if tech_stack is mentioned alongside a project, extract it. If a link/URL is associated, capture it.
7. Phone numbers: preserve the original format including country codes.
8. LinkedIn/GitHub/portfolio: extract full URLs if present, or usernames/paths if that's all that's given.

OUTPUT FORMAT — return ONLY this JSON structure, no markdown, no explanation:
{
  "name": "string",
  "email": "string",
  "phone": "string or null",
  "location": "string or null",
  "linkedin": "string or null",
  "github": "string or null",
  "portfolio": "string or null",
  "summary": "string or null",
  "work_experience": [{"company": "string", "role": "string", "start_date": "string", "end_date": "string or null", "bullets": ["string"]}],
  "education": [{"institution": "string", "degree": "string", "field": "string", "start_date": "string", "end_date": "string or null"}],
  "skills": ["string"],
  "projects": [{"name": "string", "description": "string", "tech_stack": ["string"], "link": "string or null"}],
  "certifications": [{"name": "string", "issuer": "string", "date": "string"}]
}"""


@router.post("/import/cv", response_model=ProfileData)
async def import_cv(
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    db: Session = Depends(get_db),
):
    provider, api_key = get_llm_config(db)
    if not provider or not api_key:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "LLM not configured. Set provider and API key in Settings.",
                "code": "API_KEY_NOT_CONFIGURED",
            },
        )

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

    try:
        llm_output = call_llm(
            raw_text,
            system=EXTRACT_SYSTEM_PROMPT,
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
