import json

from app.schemas import ParseJobDescriptionResponse
from app.services.llm import call_llm

PARSE_SYSTEM_PROMPT = """\
You are an expert at extracting structured information from job descriptions.
Given a job description text, extract the following fields:
- company_name: The company hiring (look for company name in title, header, or throughout text)
- role_title: The job title/position (look for "title", "position", "role" or in the first line/heading)
- location: The job location (look for location hints like "location", "city", "remote", "hybrid", "onsite", or place names)
- salary: Salary/range if mentioned (look for "salary", "compensation", "$", "USD", numbers with "k" or "000")

Return ONLY valid JSON with exactly these keys:
company_name, role_title, location, salary
All values should be strings or null if not found.
If salary is a range like "$100k - $150k", keep it as is.
If location says "Remote" or "Work from home", use that as the value.
No markdown, no explanation — just the raw JSON object."""

PARSE_USER_PROMPT = """\
Extract structured information from this job description:

{text}

Return JSON with company_name, role_title, location, salary fields."""


def parse_job_description(
    text: str, provider: str, api_key: str
) -> ParseJobDescriptionResponse:
    user_prompt = PARSE_USER_PROMPT.format(text=text[:4000])
    raw = call_llm(
        user_prompt,
        system=PARSE_SYSTEM_PROMPT,
        provider=provider,
        api_key=api_key,
        timeout=20,
    )
    cleaned = (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    data = json.loads(cleaned)
    return ParseJobDescriptionResponse(**data)
