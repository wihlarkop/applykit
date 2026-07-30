from app.schemas import ParseJobDescriptionResponse
from app.services.llm import (
    OPERATION_JOB_PARSING,
    call_llm,
    parse_structured_output,
)
from app.services.prompts import (
    PARSE_JD_SYSTEM_PROMPT,
    PARSE_JD_USER_TEMPLATE,
    format_untrusted_input,
)


def parse_job_description(
    text: str, provider: str, api_key: str
) -> ParseJobDescriptionResponse:
    user_prompt = PARSE_JD_USER_TEMPLATE.format(
        job_description=format_untrusted_input("job_description", text[:4000])
    )
    raw = call_llm(
        user_prompt,
        system=PARSE_JD_SYSTEM_PROMPT,
        provider=provider,
        api_key=api_key,
        timeout=20,
        operation=OPERATION_JOB_PARSING,
        profile_id=None,
    )
    return parse_structured_output(raw, ParseJobDescriptionResponse)
