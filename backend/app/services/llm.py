from typing import AsyncGenerator
import re

import litellm

from app.exceptions import RateLimitError
from app.exceptions.llm import APIKeyNotConfiguredError, LLMCallError


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
        response = litellm.completion(
            model=provider,
            messages=messages,
            api_key=api_key,
            timeout=timeout,
        )
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise LLMCallError("LLM returned an empty response.")
        return content
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


async def stream_llm(
    prompt: str,
    system: str | None = None,
    provider: str = "",
    api_key: str = "",
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
