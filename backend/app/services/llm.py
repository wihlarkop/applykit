import litellm


class APIKeyNotConfiguredError(Exception):
    pass


class LLMCallError(Exception):
    pass


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
    except (APIKeyNotConfiguredError, LLMCallError):
        raise
    except Exception as e:
        raise LLMCallError(str(e)) from e
