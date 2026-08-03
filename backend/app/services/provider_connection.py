import logging

import litellm

from app.public_errors import PROVIDER_CONNECTION_ERROR_MESSAGE
from app.readiness.schemas import ConnectionFailureCategory
from app.schemas import TestConnectionResponse
from app.security.secrets import safe_exception_type

logger = logging.getLogger(__name__)


def classify_connection_failure(exc: Exception) -> ConnectionFailureCategory:
    """Classify provider failures without reading or persisting exception text."""
    error_type = type(exc).__name__.lower()
    status_code = getattr(exc, "status_code", None)
    if status_code is None:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)

    if status_code in {401, 403} or any(
        token in error_type
        for token in ("authentication", "permission", "unauthorized")
    ):
        return ConnectionFailureCategory.AUTHENTICATION_FAILED
    if status_code == 429 or "ratelimit" in error_type or "rate_limit" in error_type:
        return ConnectionFailureCategory.RATE_LIMITED
    if status_code == 404 or any(
        token in error_type for token in ("notfound", "not_found", "modelnotfound")
    ):
        return ConnectionFailureCategory.MODEL_UNAVAILABLE
    if status_code in {408, 502, 503, 504} or any(
        token in error_type
        for token in ("connection", "timeout", "unavailable", "network")
    ):
        return ConnectionFailureCategory.ENDPOINT_UNREACHABLE
    return ConnectionFailureCategory.UNKNOWN_FAILURE


def public_message_for_failure(
    category: ConnectionFailureCategory,
    *,
    fallback: str = PROVIDER_CONNECTION_ERROR_MESSAGE,
) -> str:
    return {
        ConnectionFailureCategory.AUTHENTICATION_FAILED: (
            "Authentication failed. Check the active credential."
        ),
        ConnectionFailureCategory.ENDPOINT_UNREACHABLE: (
            "The provider endpoint could not be reached."
        ),
        ConnectionFailureCategory.MODEL_UNAVAILABLE: (
            "The selected model is unavailable."
        ),
        ConnectionFailureCategory.RATE_LIMITED: (
            "The provider rate limit was reached. Try again later."
        ),
        ConnectionFailureCategory.UNKNOWN_FAILURE: fallback,
    }[category]


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
        return TestConnectionResponse(
            ok=False,
            message="Provider returned an empty response.",
            failure_category=ConnectionFailureCategory.UNKNOWN_FAILURE.value,
        )
    except Exception as exc:
        category = classify_connection_failure(exc)
        logger.warning(
            "LLM connection test failed model=%s error_type=%s category=%s",
            model_id,
            safe_exception_type(exc),
            category.value,
        )
        return TestConnectionResponse(
            ok=False,
            message=public_message_for_failure(category, fallback=failure_message),
            failure_category=category.value,
        )
