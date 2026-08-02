from __future__ import annotations

from copy import deepcopy
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field


class ErrorCode(StrEnum):
    """Stable machine-readable error codes exposed by the API."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    ROUTE_NOT_FOUND = "ROUTE_NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"

    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
    APPLICATION_NOT_FOUND = "APPLICATION_NOT_FOUND"
    HISTORY_ENTRY_NOT_FOUND = "HISTORY_ENTRY_NOT_FOUND"
    PROVIDER_NOT_FOUND = "PROVIDER_NOT_FOUND"

    INVALID_REQUEST = "INVALID_REQUEST"
    SCRAPE_VALUE_ERROR = "SCRAPE_VALUE_ERROR"
    SCRAPE_FAILED = "SCRAPE_FAILED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_TYPE_UNSUPPORTED = "FILE_TYPE_UNSUPPORTED"
    FILE_PARSE_FAILED = "FILE_PARSE_FAILED"
    PDF_RENDER_FAILED = "PDF_RENDER_FAILED"

    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    API_KEY_NOT_CONFIGURED = "API_KEY_NOT_CONFIGURED"
    LLM_CALL_FAILED = "LLM_CALL_FAILED"
    LLM_OUTPUT_INVALID = "LLM_OUTPUT_INVALID"

    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_INVALID = "AUTH_INVALID"
    AUTH_FORBIDDEN = "AUTH_FORBIDDEN"
    AUTH_LOCKED = "AUTH_LOCKED"
    AUTH_SETUP_REQUIRED = "AUTH_SETUP_REQUIRED"
    AUTH_ALREADY_CONFIGURED = "AUTH_ALREADY_CONFIGURED"
    AUTH_DISABLED = "AUTH_DISABLED"


class ErrorBody(BaseModel):
    """Public error fields returned to API clients."""

    model_config = ConfigDict(frozen=True)

    code: ErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    """Top-level public error response."""

    model_config = ConfigDict(frozen=True)

    error: ErrorBody


class AppError(Exception):
    """Base type for expected application failures."""

    code: ClassVar[ErrorCode]
    status_code: ClassVar[int]
    default_message: ClassVar[str]

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        if type(self) is AppError:
            raise TypeError("AppError cannot be instantiated directly")

        error_type = type(self)
        code = getattr(error_type, "code", None)
        status_code = getattr(error_type, "status_code", None)
        default_message = getattr(error_type, "default_message", None)

        if not isinstance(code, ErrorCode):
            raise TypeError(f"{error_type.__name__}.code must be an ErrorCode")
        if not isinstance(status_code, int) or not 400 <= status_code <= 599:
            raise TypeError(
                f"{error_type.__name__}.status_code must be an integer from 400 to 599"
            )
        if not isinstance(default_message, str) or not default_message.strip():
            raise TypeError(
                f"{error_type.__name__}.default_message must be a non-empty string"
            )
        if message is not None and (not isinstance(message, str) or not message.strip()):
            raise TypeError("AppError message must be a non-empty string")
        if details is not None and not isinstance(details, dict):
            raise TypeError("AppError details must be a dictionary")
        if headers is not None and not isinstance(headers, dict):
            raise TypeError("AppError headers must be a dictionary")

        self.message = message or default_message
        self.error_code = code.value
        self.details = deepcopy(details) if details is not None else {}
        self.headers = dict(headers) if headers is not None else {}
        super().__init__(self.message)

    def to_envelope(self) -> ErrorEnvelope:
        return ErrorEnvelope(
            error=ErrorBody(
                code=self.code,
                message=self.message,
                details=deepcopy(self.details),
            )
        )
