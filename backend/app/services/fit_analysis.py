import json

from app.schemas import FitAnalysisResponse
from app.services.llm import call_llm

FIT_SYSTEM_PROMPT = """\
You are a career coach analyzing a candidate's fit for a job.
Return ONLY valid JSON with exactly these keys:
match_score (integer 0-100),
pros (array of strings — profile strengths matching the role),
cons (array of strings — gaps or weaknesses),
missing_keywords (array of strings — keywords in JD not present in profile),
red_flags (array of strings — hard blockers like years required; empty array if none),
suggested_emphasis (string — one paragraph advising what to emphasize in the cover letter),
interview_questions (array of 3 strings — likely questions based on gaps).
No markdown, no explanation — just the raw JSON object."""


def analyze_fit(
    profile_json: str,
    job_description: str,
    provider: str,
    api_key: str,
) -> FitAnalysisResponse:
    user_prompt = (
        f"Profile:\n{profile_json}\n\n"
        f"Job Description:\n{job_description}\n\n"
        "Analyze fit and return JSON."
    )
    raw = call_llm(user_prompt, system=FIT_SYSTEM_PROMPT, provider=provider, api_key=api_key, timeout=30)
    cleaned = (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    data = json.loads(cleaned)
    return FitAnalysisResponse(**data)
