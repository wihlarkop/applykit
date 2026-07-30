from app.schemas import FitAnalysisResponse
from app.services.llm import (
    OPERATION_FIT_ANALYSIS,
    call_llm,
    parse_structured_output,
)
from app.services.prompts import FIT_SYSTEM_PROMPT


def analyze_fit(
    profile_json: str,
    job_description: str,
    provider: str,
    api_key: str,
    profile_id: int | None = None,
) -> FitAnalysisResponse:
    user_prompt = (
        f"Profile:\n{profile_json}\n\n"
        f"Job Description:\n{job_description}\n\n"
        "Analyze fit and return JSON."
    )
    raw = call_llm(
        user_prompt,
        system=FIT_SYSTEM_PROMPT,
        provider=provider,
        api_key=api_key,
        timeout=30,
        operation=OPERATION_FIT_ANALYSIS,
        profile_id=profile_id,
    )
    return parse_structured_output(raw, FitAnalysisResponse)
