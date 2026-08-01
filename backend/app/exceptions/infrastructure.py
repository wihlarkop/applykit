from app.exceptions.base import AppError, ErrorCode
from app.public_errors import UNEXPECTED_ERROR_MESSAGE


class InternalApplicationError(AppError):
    code = ErrorCode.INTERNAL_SERVER_ERROR
    status_code = 500
    default_message = UNEXPECTED_ERROR_MESSAGE


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


class ScrapeFailedError(AppError):
    code = ErrorCode.SCRAPE_FAILED
    status_code = 422
    default_message = (
        "Could not extract job posting. Please paste the text manually."
    )


class PDFRenderFailedError(AppError):
    code = ErrorCode.PDF_RENDER_FAILED
    status_code = 502
    default_message = "Could not generate the PDF. Please try again."
