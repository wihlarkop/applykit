import logging

from fastapi.sse import ServerSentEvent

from app.exceptions.base import AppError
from app.exceptions.infrastructure import InternalApplicationError, RateLimitError
from app.security.secrets import safe_exception_type, safe_traceback_locations

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
            "Unhandled streaming exception error_type=%s locations=%s",
            safe_exception_type(exc),
            safe_traceback_locations(exc),
        )
        public_error = InternalApplicationError()
        event = "error"

    return ServerSentEvent(
        data=public_error.to_envelope().model_dump(mode="json"),
        event=event,
    )
