"""LLM service: synchronous and streaming calls with usage logging."""

import json
import logging
import time
from collections.abc import AsyncGenerator, Callable
from typing import Any, TypeVar

import litellm
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.exceptions import RateLimitError
from app.exceptions.llm import APIKeyNotConfiguredError, LLMCallError, LLMOutputError
from app.llm.catalog import provider_from_model, provider_requires_api_key
from app.models import ProviderCredential
from app.public_errors import LLM_PROVIDER_ERROR_MESSAGE
from app.services.credential_crypto import CredentialCipher
from app.services.provider_credential_rotation import (
    CredentialAttemptError,
    CredentialFailureKind,
    CredentialRotationPlan,
    CredentialStrategy,
    NoEligibleCredentialError,
    classify_provider_exception,
    execute_with_credential_rotation,
)
from app.services.settings import get_provider_base_url, is_llm_configured
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


def _compute_cost(response, provider: str) -> float | None:
    """Try to extract or compute cost from a LiteLLM response."""
    cost = getattr(response, "cost", None)
    if cost is None:
        usage = getattr(response, "usage", None)
        if usage is not None:
            try:
                cost = litellm.completion_cost(
                    completion_response=response,
                    model=provider,
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


def _open_rotation_session(
    provider: str,
    provided_db: Session | None,
) -> tuple[Session | None, bool]:
    provider_id = provider_from_model(provider)
    if not provider_id or not provider_requires_api_key(provider_id):
        return None, False

    db = provided_db or SessionLocal()
    owns_session = provided_db is None
    try:
        has_credentials = (
            db.query(ProviderCredential)
            .filter_by(provider_id=provider_id)
            .first()
            is not None
        )
    except OperationalError:
        if owns_session:
            db.close()
        logger.warning(
            "Credential vault table is unavailable; using the resolved active key."
        )
        return None, False

    if not has_credentials:
        if owns_session:
            db.close()
        return None, False
    return db, owns_session


def _resolve_api_base(
    provider: str,
    api_base: str | None,
    provided_db: Session | None,
) -> str | None:
    if api_base:
        return api_base

    provider_id = provider_from_model(provider)
    if provider_id != "ollama":
        return None

    db = provided_db or SessionLocal()
    owns_session = provided_db is None
    try:
        return get_provider_base_url(db, provider_id)
    finally:
        if owns_session:
            db.close()


def _completion_request(
    provider: str,
    messages: list[dict],
    timeout: int,
    api_key: str,
    api_base: str | None = None,
):
    request_kwargs: dict[str, Any] = {
        "model": provider,
        "messages": messages,
        "timeout": timeout,
    }
    if api_key:
        request_kwargs["api_key"] = api_key
    if api_base:
        request_kwargs["api_base"] = api_base
    return litellm.completion(**request_kwargs)


def _rotation_completion_attempt(
    provider: str,
    messages: list[dict],
    timeout: int,
    api_key: str,
    api_base: str | None = None,
):
    try:
        return _completion_request(provider, messages, timeout, api_key, api_base)
    except (APIKeyNotConfiguredError, LLMCallError, RateLimitError):
        raise
    except Exception as exc:
        raise classify_provider_exception(exc) from exc


def _log_failure(
    *,
    operation: str | None,
    provider: str,
    started_at: float,
    profile_id: int | None,
    message: str,
) -> None:
    if not operation:
        return
    log_usage_background(
        operation=operation,
        model_identifier=provider,
        latency_ms=int((time.time() - started_at) * 1000),
        profile_id=profile_id,
        success=False,
        error_message=message,
    )


def _raise_public_rotation_error(
    error: CredentialAttemptError,
    *,
    operation: str | None,
    provider: str,
    started_at: float,
    profile_id: int | None,
) -> None:
    original = error.original or error
    logger.warning(
        "LLM provider attempt failed model=%s error_type=%s",
        provider,
        type(original).__name__,
    )

    if error.kind is CredentialFailureKind.RATE_LIMIT:
        retry_after = max(float(error.retry_after or 60), 1.0)
        public_error = RateLimitError(
            f"Rate limit exceeded. Please retry in {retry_after:.0f}s if available.",
            retry_after=retry_after,
        )
        _log_failure(
            operation=operation,
            provider=provider,
            started_at=started_at,
            profile_id=profile_id,
            message=public_error.message,
        )
        raise public_error from original

    _log_failure(
        operation=operation,
        provider=provider,
        started_at=started_at,
        profile_id=profile_id,
        message=LLM_PROVIDER_ERROR_MESSAGE,
    )
    raise LLMCallError(LLM_PROVIDER_ERROR_MESSAGE) from original


def _record_completion_usage(
    response,
    *,
    operation: str | None,
    provider: str,
    profile_id: int | None,
) -> None:
    if not operation:
        return
    usage = getattr(response, "usage", None)
    prompt_tokens = usage.prompt_tokens if usage else None
    completion_tokens = usage.completion_tokens if usage else None
    total_tokens = usage.total_tokens if usage else None
    cost = _compute_cost(response, provider)
    latency_ms = getattr(response, "_response_ms", None)
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
    credential_db: Session | None = None,
    credential_cipher: CredentialCipher | None = None,
    api_base: str | None = None,
) -> str:
    if not is_llm_configured(provider, api_key):
        raise APIKeyNotConfiguredError(
            "LLM not configured. Set provider and API key in Settings."
        )

    messages = _prepare_messages(prompt, system)
    started_at = time.time()
    rotation_db, owns_rotation_db = _open_rotation_session(provider, credential_db)
    provider_id = provider_from_model(provider)
    resolved_api_base = _resolve_api_base(provider, api_base, credential_db)

    try:
        if rotation_db is not None and provider_id:
            response = execute_with_credential_rotation(
                rotation_db,
                provider_id,
                lambda selected_key, _credential_id: _rotation_completion_attempt(
                    provider,
                    messages,
                    timeout,
                    selected_key,
                    resolved_api_base,
                ),
                cipher=credential_cipher,
            )
        else:
            response = _completion_request(
                provider,
                messages,
                timeout,
                api_key,
                resolved_api_base,
            )

        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise LLMCallError("LLM returned an empty response.")

        _record_completion_usage(
            response,
            operation=operation,
            provider=provider,
            profile_id=profile_id,
        )
        return content

    except (APIKeyNotConfiguredError, LLMCallError, RateLimitError):
        raise
    except NoEligibleCredentialError as exc:
        raise APIKeyNotConfiguredError(
            "No enabled provider credential is currently available."
        ) from exc
    except CredentialAttemptError as exc:
        _raise_public_rotation_error(
            exc,
            operation=operation,
            provider=provider,
            started_at=started_at,
            profile_id=profile_id,
        )
    except Exception as exc:
        _raise_public_rotation_error(
            classify_provider_exception(exc),
            operation=operation,
            provider=provider,
            started_at=started_at,
            profile_id=profile_id,
        )
    finally:
        if owns_rotation_db and rotation_db is not None:
            rotation_db.close()


# ---------------------------------------------------------------------------
# Async streaming LLM call
# ---------------------------------------------------------------------------


async def _stream_request(
    provider: str,
    messages: list[dict],
    api_key: str,
    api_base: str | None = None,
):
    request_kwargs: dict[str, Any] = {
        "model": provider,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
        "timeout": 60,
    }
    if api_key:
        request_kwargs["api_key"] = api_key
    if api_base:
        request_kwargs["api_base"] = api_base
    return await litellm.acompletion(**request_kwargs)


def _record_stream_usage(
    *,
    operation: str | None,
    provider: str,
    profile_id: int | None,
    started_at: float,
    final_usage,
    final_chunk,
) -> None:
    if not operation:
        return
    latency_ms = int((time.time() - started_at) * 1000)
    if final_usage is not None:
        cost = _compute_cost(final_chunk, provider) if final_chunk is not None else None
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
        return
    log_usage_background(
        operation=operation,
        model_identifier=provider,
        latency_ms=latency_ms,
        profile_id=profile_id,
    )


async def stream_llm(
    prompt: str,
    system: str | None = None,
    provider: str = "",
    api_key: str = "",
    operation: str | None = None,
    profile_id: int | None = None,
    credential_db: Session | None = None,
    credential_cipher: CredentialCipher | None = None,
    api_base: str | None = None,
) -> AsyncGenerator[str, None]:
    if not is_llm_configured(provider, api_key):
        raise APIKeyNotConfiguredError(
            "LLM not configured. Set provider and API key in Settings."
        )

    messages = _prepare_messages(prompt, system)
    started_at = time.time()
    rotation_db, owns_rotation_db = _open_rotation_session(provider, credential_db)
    provider_id = provider_from_model(provider)
    resolved_api_base = _resolve_api_base(provider, api_base, credential_db)

    try:
        if rotation_db is None or not provider_id:
            try:
                response = await _stream_request(
                    provider,
                    messages,
                    api_key,
                    resolved_api_base,
                )
                final_usage = None
                final_chunk = None
                async for chunk in response:
                    final_chunk = chunk
                    usage = getattr(chunk, "usage", None)
                    if usage and getattr(usage, "total_tokens", None):
                        final_usage = usage
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        yield delta
                _record_stream_usage(
                    operation=operation,
                    provider=provider,
                    profile_id=profile_id,
                    started_at=started_at,
                    final_usage=final_usage,
                    final_chunk=final_chunk,
                )
                return
            except (APIKeyNotConfiguredError, LLMCallError, RateLimitError):
                raise
            except Exception as exc:
                _raise_public_rotation_error(
                    classify_provider_exception(exc),
                    operation=operation,
                    provider=provider,
                    started_at=started_at,
                    profile_id=profile_id,
                )

        plan = CredentialRotationPlan(
            rotation_db,
            provider_id,
            cipher=credential_cipher,
        )
        last_error: CredentialAttemptError | None = None

        for resolved in plan.attempts():
            emitted_content = False
            final_usage = None
            final_chunk = None
            try:
                response = await _stream_request(
                    provider,
                    messages,
                    resolved.secret,
                    resolved_api_base,
                )
                async for chunk in response:
                    final_chunk = chunk
                    usage = getattr(chunk, "usage", None)
                    if usage and getattr(usage, "total_tokens", None):
                        final_usage = usage
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        emitted_content = True
                        yield delta
            except (APIKeyNotConfiguredError, LLMCallError, RateLimitError):
                raise
            except Exception as exc:
                error = classify_provider_exception(exc)
                last_error = error
                plan.record_failure(resolved.credential_id, error)
                can_retry = (
                    not emitted_content
                    and error.kind is not CredentialFailureKind.NON_RETRYABLE
                    and plan.strategy is not CredentialStrategy.MANUAL
                )
                if can_retry:
                    continue
                _raise_public_rotation_error(
                    error,
                    operation=operation,
                    provider=provider,
                    started_at=started_at,
                    profile_id=profile_id,
                )

            plan.record_success(resolved.credential_id)
            _record_stream_usage(
                operation=operation,
                provider=provider,
                profile_id=profile_id,
                started_at=started_at,
                final_usage=final_usage,
                final_chunk=final_chunk,
            )
            return

        if last_error is not None:
            _raise_public_rotation_error(
                last_error,
                operation=operation,
                provider=provider,
                started_at=started_at,
                profile_id=profile_id,
            )
    except (APIKeyNotConfiguredError, LLMCallError, RateLimitError):
        raise
    except NoEligibleCredentialError as exc:
        raise APIKeyNotConfiguredError(
            "No enabled provider credential is currently available."
        ) from exc
    finally:
        if owns_rotation_db and rotation_db is not None:
            rotation_db.close()
