from __future__ import annotations

from pydantic import BaseModel, ConfigDict, ValidationError

from app.role_match.constants import EXTRACTION_ATTEMPTS
from app.role_match.domain import AnalysisState, AtomicRequirement
from app.role_match.prompts import REQUIREMENT_EXTRACTION_SYSTEM_PROMPT
from app.role_match.structured import parse_json_model
from app.services.prompts import format_untrusted_input


class RequirementExtractionPayload(BaseModel):
    requirements: list[AtomicRequirement]


class ExtractionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: AnalysisState
    requirements: list[AtomicRequirement] = []
    raw_outputs: list[str] = []
    failure_code: str | None = None


def _call_llm(**kwargs) -> str:
    from app.services.llm import call_llm

    return call_llm(**kwargs)


def extract_atomic_requirements(
    job_description: str,
    provider: str,
    api_key: str,
    *,
    profile_id: int | None = None,
) -> ExtractionResult:
    raw_outputs: list[str] = []
    user_prompt = "\n".join(
        [
            format_untrusted_input("job_description", job_description),
            "Extract atomic requirements and return JSON with a requirements array.",
        ]
    )
    for _ in range(EXTRACTION_ATTEMPTS):
        raw = _call_llm(
            user_prompt=user_prompt,
            system=REQUIREMENT_EXTRACTION_SYSTEM_PROMPT,
            provider=provider,
            api_key=api_key,
            timeout=45,
            operation="role_match_extraction",
            profile_id=profile_id,
        )
        raw_outputs.append(raw)
        try:
            payload = parse_json_model(raw, RequirementExtractionPayload)
            if not payload.requirements:
                raise ValueError("No requirements extracted")
            return ExtractionResult(
                state=AnalysisState.EXTRACTED,
                requirements=payload.requirements,
                raw_outputs=raw_outputs,
            )
        except (ValidationError, ValueError, TypeError):
            continue
        except Exception:
            continue
    return ExtractionResult(
        state=AnalysisState.NEEDS_REVIEW,
        raw_outputs=raw_outputs,
        failure_code="invalid_requirement_extraction",
    )
