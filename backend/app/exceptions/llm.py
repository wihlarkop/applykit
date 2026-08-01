"""LLM-specific application errors."""

from app.exceptions.base import AppError, ErrorCode


class APIKeyNotConfiguredError(AppError):
    code = ErrorCode.API_KEY_NOT_CONFIGURED
    status_code = 400
    default_message = "LLM not configured. Set provider and API key in Settings."


class LLMCallError(AppError):
    code = ErrorCode.LLM_CALL_FAILED
    status_code = 502
    default_message = "LLM call failed."


class LLMOutputError(AppError):
    code = ErrorCode.LLM_OUTPUT_INVALID
    status_code = 502
    default_message = (
        "The AI provider returned an invalid structured response. Please try again."
    )


class CVImportOutputError(AppError):
    code = ErrorCode.LLM_OUTPUT_INVALID
    status_code = 422
    default_message = "Could not parse CV into profile fields. Try editing manually."
