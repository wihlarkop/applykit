from app.exceptions.base import AppError, ErrorCode


class ValidationAppError(AppError):
    code = ErrorCode.VALIDATION_ERROR
    status_code = 422
    default_message = "Validation error."


class ValidationError(ValidationAppError):
    """Compatibility wrapper for the previous public exception API."""

    def __init__(
        self,
        message: str | list[str],
        field: str | None = None,
    ) -> None:
        public_message = message if isinstance(message, str) else "; ".join(message)
        details = {"field": field} if field else {}
        super().__init__(public_message, details=details)
