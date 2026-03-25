"""LLM service: synchronous and streaming calls with usage logging."""

import re
import threading
import time
from collections.abc import AsyncGenerator

import litellm

from app.database import get_db_context
from app.exceptions import RateLimitError
from app.exceptions.llm import APIKeyNotConfiguredError, LLMCallError
from app.models import LlmUsageLog

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
    """Strip common markdown fencing from raw LLM JSON output."""
    return (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )


# ---------------------------------------------------------------------------
# Usage logging (background)
# ---------------------------------------------------------------------------


def _log_usage_thread(
    operation: str,
    provider: str,
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
    cost: float | None,
    latency_ms: int,
    profile_id: int | None,
    success: bool,
    error_message: str | None,
) -> None:
    db_gen = get_db_context()
    db = next(db_gen)
    try:
        log = LlmUsageLog(
            operation=operation,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            latency_ms=latency_ms,
            profile_id=profile_id,
            success=success,
            error_message=error_message,
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _log_usage_background(
    operation: str,
    provider: str,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    cost: float | None = None,
    latency_ms: int = 0,
    profile_id: int | None = None,
    success: bool = True,
    error_message: str | None = None,
) -> None:
    """Fire-and-forget usage logging in a background thread."""
    threading.Thread(
        target=_log_usage_thread,
        args=(
            operation,
            provider,
            provider,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            cost,
            latency_ms,
            profile_id,
            success,
            error_message,
        ),
    ).start()


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
            _log_usage_background(
                operation=operation,
                provider=provider,
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
    except Exception as e:
        error_str = str(e)
        if operation:
            _log_usage_background(
                operation=operation,
                provider=provider,
                latency_ms=int((time.time() - start_time) * 1000),
                profile_id=profile_id,
                success=False,
                error_message=error_str,
            )
        _handle_rate_limit(error_str, e)
        raise LLMCallError(error_str) from e


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
            _log_usage_background(
                operation=operation,
                provider=provider,
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
            _log_usage_background(
                operation=operation,
                provider=provider,
                latency_ms=latency_ms,
                profile_id=profile_id,
            )

    except (APIKeyNotConfiguredError, LLMCallError, RateLimitError):
        raise
    except Exception as e:
        error_str = str(e)
        _handle_rate_limit(error_str, e)
        raise LLMCallError(error_str) from e
