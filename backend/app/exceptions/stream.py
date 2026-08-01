import logging

from fastapi.sse import ServerSentEvent

from app.exceptions.base import AppError
from app.exceptions.infrastructure import InternalApplicationError, RateLimitError

logger = logging.getLogger(__name__)


def stream_error_event(exc: Exception) -> ServerSentEvent:
    """Convert a streaming exception into the public error envelope."""
    if isinstance(exc, RateLimitError):
        public_error: AppError = exc
        event = "rate_limit"
    elif isinstance(exc, AppError):
        public_error = exc
        event = "error"
    else:
        logger.error(
            "Unhandled streaming exception",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        public_error = InternalApplicationError()
        event = "error"

    return ServerSentEvent(
        data=public_error.to_envelope().model_dump_json(),
        event=event,
    )
