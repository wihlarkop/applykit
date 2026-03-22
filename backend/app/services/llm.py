from typing import AsyncGenerator
import re
import threading
import time
from datetime import datetime, UTC

import litellm

from app.exceptions import RateLimitError
from app.exceptions.llm import APIKeyNotConfiguredError, LLMCallError
from sqlalchemy.orm import Session

from app.models import LlmUsageLog
from app.database import get_db_context

# Operation types for LLM usage tracking
OPERATION_CV_GENERATION = "cv_generation"
OPERATION_COVER_LETTER = "cover_letter"
OPERATION_FIT_ANALYSIS = "fit_analysis"
OPERATION_JOB_PARSING = "job_parsing"
OPERATION_SUMMARY_GENERATION = "summary_generation"
OPERATION_BULLETS_GENERATION = "bullets_generation"


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
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
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
        cost = getattr(response, "cost", None)
        latency_ms = getattr(response, "_response_ms", None)

        # DEBUG: Print all response attributes
        print(f"[DEBUG] litellm response type: {type(response)}")
        print(
            f"[DEBUG] response attributes: {[a for a in dir(response) if not a.startswith('_')]}"
        )
        print(f"[DEBUG] usage: {usage}")
        print(f"[DEBUG] cost: {cost}")
        print(f"[DEBUG] latency_ms: {latency_ms}")

        # Try calculating cost manually if not set
        if cost is None and usage is not None:
            try:
                cost = litellm.completion_cost(
                    completion_response=response, model=provider
                )
                print(f"[DEBUG] calculated cost: {cost}")
            except Exception as e:
                print(f"[DEBUG] cost calculation failed: {e}")

        if operation:
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
                    latency_ms or 0,
                    profile_id,
                    True,
                    None,
                ),
            ).start()

        return content
    except (APIKeyNotConfiguredError, LLMCallError, RateLimitError):
        raise
    except Exception as e:
        error_str = str(e)
        if operation:
            threading.Thread(
                target=_log_usage_thread,
                args=(
                    operation,
                    provider,
                    provider,
                    None,
                    None,
                    None,
                    None,
                    int((time.time() - start_time) * 1000),
                    profile_id,
                    False,
                    str(e),
                ),
            ).start()
        if "RateLimitError" in error_str or "429" in error_str:
            retry_after = _extract_retry_delay(error_str)
            raise RateLimitError(
                f"Rate limit exceeded. Please retry in {retry_after:.0f}s if available.",
                retry_after=retry_after,
            ) from e
            raise LLMCallError(error_str) from e


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
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        response = await litellm.acompletion(
            model=provider,
            messages=messages,
            api_key=api_key,
            stream=True,
            timeout=60,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

        if operation:
            try:
                final_usage = getattr(response, "usage", None)
                if final_usage:
                    threading.Thread(
                        target=_log_usage_thread,
                        args=(
                            operation,
                            provider,
                            provider,
                            final_usage.prompt_tokens if final_usage else None,
                            final_usage.completion_tokens if final_usage else None,
                            final_usage.total_tokens if final_usage else None,
                            getattr(response, "cost", None),
                            getattr(response, "_response_ms", 0) or 0,
                            profile_id,
                            True,
                            None,
                        ),
                    ).start()
            except Exception:
                pass
    except (APIKeyNotConfiguredError, LLMCallError, RateLimitError):
        raise
    except Exception as e:
        error_str = str(e)
        if "RateLimitError" in error_str or "429" in error_str:
            retry_after = _extract_retry_delay(error_str)
            raise RateLimitError(
                f"Rate limit exceeded. Please retry in {retry_after:.0f}s if available.",
                retry_after=retry_after,
            ) from e
        raise LLMCallError(error_str) from e
