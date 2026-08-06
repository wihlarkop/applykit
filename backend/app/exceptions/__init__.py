from app.exceptions.base import AppError, ErrorBody, ErrorCode, ErrorEnvelope
from app.exceptions.infrastructure import (
    InternalApplicationError,
    PDFRenderFailedError,
    RateLimitError,
    ScrapeFailedError,
)
from app.exceptions.llm import (
    APIKeyNotConfiguredError,
    CVImportOutputError,
    LLMCallError,
    LLMOutputError,
)
from app.exceptions.request import (
    FileParseError,
    FileTooLargeError,
    InvalidRequestError,
    ScrapeValueError,
    UnsupportedFileTypeError,
    ValidationAppError,
)
from app.exceptions.resource import (
    ApplicationNotFoundError,
    HistoryEntryNotFoundError,
    ProfileNotFoundError,
    ProviderNotFoundError,
)
from app.exceptions.role_match import (
    RoleMatchAnalysisNotFoundError,
    RoleMatchProfileRequiredError,
)
from app.exceptions.stream import stream_error_event

__all__ = [
    "AppError",
    "ErrorCode",
    "ErrorBody",
    "ErrorEnvelope",
    "ProfileNotFoundError",
    "ApplicationNotFoundError",
    "HistoryEntryNotFoundError",
    "ProviderNotFoundError",
    "RoleMatchAnalysisNotFoundError",
    "RoleMatchProfileRequiredError",
    "ValidationAppError",
    "InvalidRequestError",
    "ScrapeValueError",
    "FileTooLargeError",
    "UnsupportedFileTypeError",
    "FileParseError",
    "InternalApplicationError",
    "RateLimitError",
    "ScrapeFailedError",
    "PDFRenderFailedError",
    "APIKeyNotConfiguredError",
    "LLMCallError",
    "LLMOutputError",
    "CVImportOutputError",
    "stream_error_event",
]
