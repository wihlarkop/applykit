from app.exceptions.base import AppError, ErrorCode


class ValidationAppError(AppError):
    code = ErrorCode.VALIDATION_ERROR
    status_code = 422
    default_message = "Validation error."


class InvalidRequestError(AppError):
    code = ErrorCode.INVALID_REQUEST
    status_code = 400
    default_message = "Invalid request."


class ScrapeValueError(AppError):
    code = ErrorCode.SCRAPE_VALUE_ERROR
    status_code = 422
    default_message = "The job posting input is invalid."


class FileTooLargeError(AppError):
    code = ErrorCode.FILE_TOO_LARGE
    status_code = 413
    default_message = "File is too large."

    def __init__(self, max_size_mb: int) -> None:
        super().__init__(
            f"File too large. Maximum size is {max_size_mb}MB.",
            details={"max_size_mb": max_size_mb},
        )


class UnsupportedFileTypeError(AppError):
    code = ErrorCode.FILE_TYPE_UNSUPPORTED
    status_code = 422
    default_message = "Unsupported file type. Use PDF, DOCX, or plain text."


class FileParseError(AppError):
    code = ErrorCode.FILE_PARSE_FAILED
    status_code = 422
    default_message = "Could not extract text from file."
