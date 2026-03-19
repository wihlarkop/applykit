from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status


class BaseCustomException(HTTPException):
    """Base custom exception class with structured error information."""

    def __init__(
        self,
        message: str | list[str],
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}


class NotFoundError(BaseCustomException):
    """Exception for resource not found errors."""

    def __init__(self, resource: str, identifier: str | int) -> None:
        message = f"{resource} with identifier '{identifier}' not found"
        error_code = f"{resource.upper()}_NOT_FOUND"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=error_code,
        )


class ValidationError(BaseCustomException):
    """Exception for validation errors."""

    def __init__(
        self,
        message: str | list[str],
        field: str | None = None,
    ) -> None:
        details = {"field": field} if field else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class ConflictError(BaseCustomException):
    """Exception for resource conflict errors (e.g., duplicate ID)."""

    def __init__(
        self,
        resource: str,
        identifier: str | int,
        message: str | None = None,
    ) -> None:
        error_message = (
            message or f"{resource} with identifier '{identifier}' already exists"
        )
        error_code = f"{resource.upper()}_CONFLICT"
        super().__init__(
            message=error_message,
            status_code=status.HTTP_409_CONFLICT,
            error_code=error_code,
        )


class InternalServerError(BaseCustomException):
    """Exception for internal server errors."""

    def __init__(
        self,
        message: str = "An internal server error occurred",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            details=details,
        )


class AIProcessingError(BaseCustomException):
    """Exception for AI processing errors."""

    def __init__(
        self,
        message: str = "AI processing failed",
        model: str | None = None,
    ) -> None:
        details = {"model": model} if model else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="AI_PROCESSING_ERROR",
            details=details,
        )


class RateLimitError(BaseCustomException):
    """Exception for rate limit errors (HTTP 429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded. Please retry later.",
        retry_after: float | None = None,
    ) -> None:
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
        )


class StorageError(BaseCustomException):
    """Exception for storage/upload errors."""

    def __init__(
        self,
        message: str = "Storage operation failed",
        operation: str | None = None,
    ) -> None:
        details = {"operation": operation} if operation else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="STORAGE_ERROR",
            details=details,
        )


def error_response(
    message: str | list[str],
    status_code: int,
    error_code: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create standardized error response."""
    return {
        "success": False,
        "status_code": status_code,
        "error_code": error_code,
        "message": message,
        "details": details or {},
        "timestamp": datetime.now(UTC).isoformat(),
    }
