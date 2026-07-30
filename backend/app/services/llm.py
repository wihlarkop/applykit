"""LLM service: synchronous and streaming calls with usage logging."""

import json
import logging
import re
import time
from collections.abc import AsyncGenerator, Callable
from typing import Any, TypeVar

import litellm
from pydantic import BaseModel, ValidationError

from app.exceptions import RateLimitError
from app.exceptions.llm import APIKeyNotConfiguredError, LLMCallError, LLMOutputError
from app.public_errors import LLM_PROVIDER_ERROR_MESSAGE
from app.services.usage_logging import log_usage_background

logger = logging.getLogger(__name__)
StructuredModel = TypeVar("StructuredModel", bound=BaseModel)

# Operation types for LLM usage tracking
OPERATION_CV_GENERATION = "cv_generation"
OPERATION_COVER_LETTER = "cover_letter"
OPERATION_FIT_ANALYSIS = "fit_analysis"
OPERATION_JOB_PARSING = "job_parsing"
OPERATION_SUMMARY_GENERATION = "summary_generation"
OPERATION_BULLETS_GENERATION = "bullets_generation"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prepare_messages(prompt: str, system: str | None = None) -> list[dict]:
    """Build the messages list from a user prompt and optional system prompt."""
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return messages


def _extract_retry_delay(error_str: str) -> float:
    match = re.search(
        r"retry[_\s]delay[\":\s]+(\d+(?:\.\d+)?)", error_str, re.IGNORECASE
    )
    if match:
        return float(match.group(1))
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", error_str, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return 60.0


def _handle_rate_limit(error_str: str, original: Exception) -> None:
    """Raise RateLimitError if the error looks like a 429."""
    if "RateLimitError" in error_str or "429" in error_str:
        retry_after = _extract_retry_delay(error_str)
        raise RateLimitError(
            f"Rate limit exceeded. Please retry in {retry_after:.0f}s if available.",
            retry_after=retry_after,
        ) from original


def _compute_cost(response, provider: str) -> float | None:
    """Try to extract or compute cost from a LiteLLM response."""
    cost = getattr(response, "cost", None)
    if cost is None:
        usage = getattr(response, "usage", None)
        if usage is not None:
            try:
                cost = litellm.completion_cost(
                    completion_response=response, model=provider
                )
            except Exception:
                pass
    return cost


def clean_llm_json(raw: str) -> str:
    """Strip one optional markdown fence from raw LLM JSON output."""
    cleaned = raw.strip()
    if cleaned.startswith("```json") and cleaned.endswith("```"):
        return cleaned[len("```json") : -len("```")].strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        return cleaned[len("```") : -len("```")].strip()
    return cleaned


def parse_structured_output(
    raw: str,
    schema: type[StructuredModel],
    *,
    preprocess: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> StructuredModel:
    """Parse one JSON object and validate it against a Pydantic schema."""
    try:
        data = json.loads(clean_llm_json(raw))
        if not isinstance(data, dict):
            raise TypeError("Structured output must be a JSON object")
        if preprocess is not None:
            data = preprocess(data)
        return schema.model_validate(data)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
        logger.warning(
            "Invalid structured LLM output schema=%s output_length=%d",
            schema.__name__,
            len(raw),
        )
        raise LLMOutputError() from None


# ---------------------------------------------------------------------------
# Synchronous LLM call
# ---------------------------------------------------------------------------


def call_llm(
    prompt: str,
    system: str | None = None,
    timeout: int = 30,
    provider: str = "",
    api_key: str = "",
    operation: str | None = None,
    profile_id: int | None = None,
) -> str:
    if not provider or not api_key:
        raise APIKeyNotConfiguredError(
            "LLM not configured. Set provider and API key in Settings."
        )

    messages = _prepare_messages(prompt, system)

    try:
        start_time = time.time()
        response = litellm.completion(
            model=provider,
            messages=messages,
            api_key=api_key,
            timeout=timeout,
        )
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise LLMCallError("LLM returned an empty response.")

        usage = getattr(response, "usage", None)
        prompt_tokens = usage.prompt_tokens if usage else None
        completion_tokens = usage.completion_tokens if usage else None
        total_tokens = usage.total_tokens if usage else None
        cost = _compute_cost(response, provider)
        latency_ms = getattr(response, "_response_ms", None)

        if operation:
            log_usage_background(
                operation=operation,
                model_identifier=provider,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=latency_ms or 0,
                profile_id=profile_id,
            )

        return content

    except (APIKeyNotConfiguredError, LLMCallError, RateLimitError):
        raise
    except Exception as exc:
        error_str = str(exc)
        logger.warning(
            "LLM request failed for model %s",
            provider,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        try:
            _handle_rate_limit(error_str, exc)
        except RateLimitError as rate_error:
            if operation:
                log_usage_background(
                    operation=operation,
                    model_identifier=provider,
                    latency_ms=int((time.time() - start_time) * 1000),
                    profile_id=profile_id,
                    success=False,
                    error_message=rate_error.message,
                )
            raise

        if operation:
            log_usage_background(
                operation=operation,
                model_identifier=provider,
                latency_ms=int((time.time() - start_time) * 1000),
                profile_id=profile_id,
                success=False,
                error_message=LLM_PROVIDER_ERROR_MESSAGE,
            )
        raise LLMCallError(LLM_PROVIDER_ERROR_MESSAGE) from exc


# ---------------------------------------------------------------------------
# Async streaming LLM call
# ---------------------------------------------------------------------------


async def stream_llm(
    prompt: str,
    system: str | None = None,
    provider: str = "",
    api_key: str = "",
    operation: str | None = None,
    profile_id: int | None = None,
) -> AsyncGenerator[str, None]:
    if not provider or not api_key:
        raise APIKeyNotConfiguredError(
            "LLM not configured. Set provider and API key in Settings."
        )

    messages = _prepare_messages(prompt, system)

    try:
        start_time = time.time()
        response = await litellm.acompletion(
            model=provider,
            messages=messages,
            api_key=api_key,
            stream=True,
            stream_options={"include_usage": True},
            timeout=60,
        )

        # Track final usage from the last chunk
        final_usage = None
        async for chunk in response:
            # The last chunk with include_usage=True has usage data but empty choices
            usage = getattr(chunk, "usage", None)
            if usage and getattr(usage, "total_tokens", None):
                final_usage = usage

            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

        # Log usage after streaming completes
        if operation and final_usage:
            cost = _compute_cost(chunk, provider)
            latency_ms = int((time.time() - start_time) * 1000)
            log_usage_background(
                operation=operation,
                model_identifier=provider,
                prompt_tokens=getattr(final_usage, "prompt_tokens", None),
                completion_tokens=getattr(final_usage, "completion_tokens", None),
                total_tokens=getattr(final_usage, "total_tokens", None),
                cost=cost,
                latency_ms=latency_ms,
                profile_id=profile_id,
            )
        elif operation:
            # No usage info returned, but still log the call
            latency_ms = int((time.time() - start_time) * 1000)
            log_usage_background(
                operation=operation,
                model_identifier=provider,
                latency_ms=latency_ms,
                profile_id=profile_id,
            )

    except (APIKeyNotConfiguredError, LLMCallError, RateLimitError):
        raise
    except Exception as exc:
        error_str = str(exc)
        logger.warning(
            "Streaming LLM request failed for model %s",
            provider,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        try:
            _handle_rate_limit(error_str, exc)
        except RateLimitError as rate_error:
            if operation:
                log_usage_background(
                    operation=operation,
                    model_identifier=provider,
                    latency_ms=int((time.time() - start_time) * 1000),
                    profile_id=profile_id,
                    success=False,
                    error_message=rate_error.message,
                )
            raise

        if operation:
            log_usage_background(
                operation=operation,
                model_identifier=provider,
                latency_ms=int((time.time() - start_time) * 1000),
                profile_id=profile_id,
                success=False,
                error_message=LLM_PROVIDER_ERROR_MESSAGE,
            )
        raise LLMCallError(LLM_PROVIDER_ERROR_MESSAGE) from exc
