import os

import litellm


class APIKeyNotConfiguredError(Exception):
    pass


class LLMCallError(Exception):
    pass


def _get_config() -> tuple[str, str]:
    provider = os.getenv("LLM_PROVIDER", "").strip()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not provider or not api_key:
        raise APIKeyNotConfiguredError(
            "LLM_API_KEY not configured. See README for setup instructions."
        )
    return provider, api_key


def call_llm(prompt: str, system: str | None = None, timeout: int = 30) -> str:
    provider, api_key = _get_config()
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
        return response.choices[0].message.content
    except Exception as e:
        raise LLMCallError(str(e)) from e
