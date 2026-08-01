from typing import Any

from app.exceptions.base import AppError, ErrorCode
from app.public_errors import UNEXPECTED_ERROR_MESSAGE


class InternalApplicationError(AppError):
    code = ErrorCode.INTERNAL_SERVER_ERROR
    status_code = 500
    default_message = UNEXPECTED_ERROR_MESSAGE


class InternalServerError(InternalApplicationError):
    """Compatibility wrapper for the previous public exception API."""

    default_message = "An internal server error occurred"

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)


class AIProcessingError(AppError):
    code = ErrorCode.AI_PROCESSING_ERROR
    status_code = 500
    default_message = "AI processing failed"

    def __init__(
        self,
        message: str | None = None,
        model: str | None = None,
    ) -> None:
        details = {"model": model} if model else {}
        super().__init__(message, details=details)


class RateLimitError(AppError):
    code = ErrorCode.RATE_LIMIT_EXCEEDED
    status_code = 429
    default_message = "Rate limit exceeded. Please retry later."

    def __init__(
        self,
        message: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        details = {"retry_after": retry_after} if retry_after is not None else {}
        headers = (
            {"Retry-After": str(retry_after)} if retry_after is not None else None
        )
        super().__init__(message, details=details, headers=headers)


class StorageError(AppError):
    code = ErrorCode.STORAGE_ERROR
    status_code = 500
    default_message = "Storage operation failed"

    def __init__(
        self,
        message: str | None = None,
        operation: str | None = None,
    ) -> None:
        details = {"operation": operation} if operation else {}
        super().__init__(message, details=details)
