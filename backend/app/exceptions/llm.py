"""LLM-specific exceptions — integrated with the global exception handler."""

from fastapi import status

from app.exceptions.base import BaseCustomException


class APIKeyNotConfiguredError(BaseCustomException):
    """Raised when LLM API key is not configured."""

    def __init__(
        self, message: str = "LLM not configured. Set provider and API key in Settings."
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="API_KEY_NOT_CONFIGURED",
        )


class LLMCallError(BaseCustomException):
    """Raised when an LLM call fails."""

    def __init__(self, message: str = "LLM call failed."):
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="LLM_CALL_FAILED",
        )
