import logging

import litellm

from app.public_errors import PROVIDER_CONNECTION_ERROR_MESSAGE
from app.schemas import TestConnectionResponse
from app.security.secrets import safe_exception_type

logger = logging.getLogger(__name__)


def test_provider_connection(
    model_id: str,
    api_key: str | None = None,
    *,
    api_base: str | None = None,
    failure_message: str = PROVIDER_CONNECTION_ERROR_MESSAGE,
) -> TestConnectionResponse:
    request_kwargs: dict[str, object] = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "timeout": 15,
        "max_tokens": 5,
    }
    if api_key:
        request_kwargs["api_key"] = api_key
    if api_base:
        request_kwargs["api_base"] = api_base

    try:
        response = litellm.completion(**request_kwargs)
        content = response.choices[0].message.content if response.choices else ""
        if content:
            return TestConnectionResponse(ok=True, message="Connection successful.")
        return TestConnectionResponse(ok=False, message="LLM returned empty response.")
    except Exception as exc:
        logger.warning(
            "LLM connection test failed model=%s error_type=%s",
            model_id,
            safe_exception_type(exc),
        )
        return TestConnectionResponse(
            ok=False,
            message=failure_message,
        )
