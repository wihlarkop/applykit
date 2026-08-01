import logging

import litellm

from app.schemas import TestConnectionResponse

logger = logging.getLogger(__name__)


def test_provider_connection(
    model_id: str,
    api_key: str | None = None,
) -> TestConnectionResponse:
    request_kwargs: dict[str, object] = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "timeout": 15,
        "max_tokens": 5,
    }
    if api_key:
        request_kwargs["api_key"] = api_key

    try:
        response = litellm.completion(**request_kwargs)
        content = response.choices[0].message.content if response.choices else ""
        if content:
            return TestConnectionResponse(ok=True, message="Connection successful.")
        return TestConnectionResponse(ok=False, message="LLM returned empty response.")
    except Exception as exc:
        logger.warning(
            "LLM connection test failed for model %s",
            model_id,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return TestConnectionResponse(
            ok=False,
            message="Provider connection failed.",
        )
