import json

from app.schemas import ParseJobDescriptionResponse
from app.services.llm import call_llm, clean_llm_json, OPERATION_JOB_PARSING
from app.services.prompts import PARSE_JD_SYSTEM_PROMPT, PARSE_JD_USER_TEMPLATE


def parse_job_description(
    text: str, provider: str, api_key: str
) -> ParseJobDescriptionResponse:
    user_prompt = PARSE_JD_USER_TEMPLATE.format(text=text[:4000])
    raw = call_llm(
        user_prompt,
        system=PARSE_JD_SYSTEM_PROMPT,
        provider=provider,
        api_key=api_key,
        timeout=20,
        operation=OPERATION_JOB_PARSING,
        profile_id=None,
    )
    cleaned = clean_llm_json(raw)
    data = json.loads(cleaned)
    return ParseJobDescriptionResponse(**data)
